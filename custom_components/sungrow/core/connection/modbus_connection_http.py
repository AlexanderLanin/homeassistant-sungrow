"""
WiNet HTTP connection for Sungrow inverters.

In detail this will query the inverter via websocket for the token and then
query the inverter via http for the actual data.

Data-queries via websocket are not yet implemented.
"""

import asyncio
import logging
import os
import time
from enum import StrEnum
from typing import Any, cast

import aiohttp
import modbus_connection_base
from result import Err, Ok, Result

from .modbus_types import RegisterRange

logger = logging.getLogger(__name__)


class ModbusConnection_Http(modbus_connection_base.ModbusConnection_Base):  # noqa: N801
    def __init__(self, host: str, port: int | None = None):
        super().__init__(host, port or self.default_port())

        self._aio_client = aiohttp.ClientSession()
        self._ws: aiohttp.client.ClientWebSocketResponse | None = None

        self._token: str | None = None
        self._inverter: dict[str, str] | None = None

    @property
    def is_http(self) -> bool:
        return True

    @staticmethod
    def default_port() -> int:
        return 8082

    @staticmethod
    def _parse_ws_response(
        response: dict[str, Any],
    ) -> Result[dict[str, Any], modbus_connection_base.ModbusError]:
        if (
            response.get("result_code") == 1
            and response.get("result_msg") == "success"
            and response.get("result_data") is not None
        ):
            return Ok(response["result_data"])
        else:
            return Err(
                modbus_connection_base.ModbusError(
                    f"Inverter responded with: {type(response)} {response}"
                )
            )

    async def _ws_query(self, query: dict[str, str | int]):
        # Potential services: connect, devicelist, state, statistics, runtime, real
        assert self._ws is not None

        await self._ws.send_json(query)

        response: dict = await self._ws.receive_json()

        return ModbusConnection_Http._parse_ws_response(response)

    async def _get_new_token(self) -> str:
        response = await self._ws_query(
            {"lang": "en_us", "token": "", "service": "connect"}
        )
        if isinstance(response, Ok):
            return cast(str, response.ok_value["token"])
        else:
            # TODO: return the error instead?
            raise response.unwrap_err()

    async def _get_connected_devices(self) -> list[dict[str, str]]:
        assert self._token is not None

        response = await self._ws_query(
            {
                "lang": "en_us",
                "token": self._token,
                "service": "devicelist",
                "type": "0",
                "is_check_token": "0",
            }
        )
        if isinstance(response, Ok):
            return cast(list[dict[str, str]], response.ok_value["list"])
        else:
            # TODO: return the error instead?
            raise response.unwrap_err()

    async def connect(self):
        """
        Retrieves the token from the WiNet dongle.
        No permanent connection is established!

        Returns true/false on success/failure.
        Raises modbus.CannotConnectError on WiNet misbehavior.
        """

        if self.connected:
            return True

        logger.debug("Connecting to %s:%s", self._host, self._port)
        self._stats.connections += 1

        endpoint = f"ws://{self._host}:{self._port}/ws/home/overview"
        try:
            # We'll manage lifetime via connect/disconnect ourselfes
            self._ws = await self._aio_client.ws_connect(endpoint).__aenter__()

            logger.debug("Connection to websocket server established")

            self._token = await self._get_new_token()

            # The first device is always the inverter.
            # ToDo: can we do anything with the others?
            self._inverter = (await self._get_connected_devices())[0]

            return True
        except aiohttp.ClientError:
            # Cannot connect
            await self.disconnect()
            return False
        except Exception as e:
            # Some other error
            logger.debug(f"Connection failed: {e}", exc_info=True)
            await self.disconnect()
            return False

    async def disconnect(self):
        logger.debug("Disconnecting from %s:%s", self._host, self._port)

        self._token = None
        self._inverter = None

        if self._ws:
            await self._ws.close()
            self._ws = None

        # Force completely new connections on next connect()
        await self._aio_client.close()

    @property
    def connected(self) -> bool:
        return self._token is not None

    async def _get_json(
        self, url: str, params: dict[str, str | int]
    ) -> Result[dict[str, Any], modbus_connection_base.ModbusError]:
        try:
            async with await self._aio_client.get(url, params=params) as r:
                logger.debug(f"Got r response: {r}")
                if r.status == 200:
                    return Ok(await r.json())
                else:
                    return Err(
                        modbus_connection_base.ModbusError(
                            f"Invalid response from inverter: {r.status} {r.text}"
                        )
                    )
        except Exception as e:
            # e.g. response is not valid json
            return Err(modbus_connection_base.ModbusError(f"Connection Failed: {e}"))

    def _build_http_request_for_register_query(
        self, rr: RegisterRange
    ) -> tuple[str, dict[str, str | int]]:
        assert self._inverter
        assert self._token

        param_types = {
            modbus_connection_base.RegisterType.READ: 0,
            modbus_connection_base.RegisterType.HOLD: 1,
        }

        # Usually port 80, but we cannot use a hardcoded port in tests.
        # In tests we'll simply reuse the port of the websocket server.
        if "PYTEST_CURRENT_TEST" in os.environ:
            logger.warning("Running in test mode, using websocket port for http")
            port = self._port
        else:
            port = 80

        url = f"http://{self._host}:{port}/device/getParam"
        params: dict[str, str | int] = {
            "dev_id": self._inverter["dev_id"],
            "dev_type": self._inverter["dev_type"],
            "dev_code": self._inverter["dev_code"],
            "type": "3",  # todo: Why 3?
            "param_addr": rr.start,
            "param_num": rr.length,
            "param_type": param_types[rr.register_type],
            "token": self._token,
            "lang": "en_us",
            "time123456": int(time.time()),
        }
        return url, params

    class ErrorResponse(StrEnum):
        Busy = "retry"
        TokenExpired = "token_expired"

    class BusyError(Exception):
        pass

    class TokenExpiredError(Exception):
        pass

    def _parse_sungrow_response(self, response: dict[str, Any]):
        logger.debug(f"Response: {response}")
        if response["result_code"] == 1:
            return cast(dict, response["result_data"])
        elif response["result_code"] == 106:
            return Err(ModbusConnection_Http.TokenExpiredError())
        elif response["result_code"] == 301:
            # Wild guess what 301 means. It's not in the official documentation.
            # Seems to work out if we retry after a reasonable delay.
            return Err(ModbusConnection_Http.BusyError())
        else:
            return Err(
                modbus_connection_base.ModbusError(
                    f"Unknown response from inverter: {response}"
                )
            )

    async def _query_http_json(self, rr: RegisterRange):
        for _attempt in range(3):
            if not await self.connect():
                return Err(modbus_connection_base.CannotConnectError())

            # (Re-)build query with current token
            url, params = self._build_http_request_for_register_query(rr)

            response = await self._get_json(url, params)
            if isinstance(response, Err):
                # connection failed
                

            parsed = self._parse_sungrow_response(response.ok_value)
            if isinstance(parsed, Err):
                if isinstance(
                    parsed.err_value, ModbusConnection_Http.TokenExpiredError
                ):
                    logger.debug("Token expired, reconnecting")
                    await self.disconnect()
                    if not await self.connect():
                        return Err(
                            modbus_connection_base.CannotConnectError(
                                "Cannot reconnect for new token"
                            )
                        )
                    # Rebuild query with new token
                    url, params = self._build_http_request_for_register_query(rr)
                    parsed = self._parse_sungrow_response(
                        await self._get_json(url, params)
                    )

            try:
                parsed = self._parse_sungrow_response(response)
            except ModbusConnection_Http.TokenExpiredError:
                logger.debug("Token expired, reconnecting")
                await self.disconnect()
                if not await self.connect():
                    raise modbus_connection_base.CannotConnectError(
                        "Cannot reconnect for new token"
                    ) from None
                # Rebuild query with new token

            except ModbusConnection_Http.BusyError:
                # retry after a delay
                await asyncio.sleep(5)
                parsed = self._parse_sungrow_response(await self._get_json(url, params))

            return parsed
        return Err(modbus_connection_base.ModbusError("Too many retries"))

    async def _read_range(self, r: RegisterRange) -> Result[list[int], Exception]:
        # Note: websocket does not allow access to all possible registers.
        # Not quite clear whether it's worth the effort to query some via websocket and
        # only the rest via http.

        try:
            response_json = await self._query_http_json(r)

            logger.debug(f"Got data: {response_json}")

            data = _parse_modbus_data(response_json, r.length)
            return Ok(data)
        except Exception as e:
            return Err(e)

    def __str__(self):
        return f"http({self._host}:{self._port}, slave: {self._slave or 'unknown'})"


def _parse_modbus_data(
    response_json: dict[str, Any], expected_length: int
) -> list[int]:
    modbus_data = response_json["param_value"].split(" ")
    logger.debug(f"Got modbus data: {modbus_data}")
    modbus_data.pop()  # remove null on the end

    if len(modbus_data) != expected_length * 2:
        raise modbus_connection_base.ModbusError(
            "Invalid response from inverter: "
            f"{response_json} => {modbus_data}, "
            f"expected length {expected_length}"
        )

    data: list[int] = []
    # Merge two consecutive bytes into 16 bit integers, same as pymodbus.
    # Maybe it would be better to use bytes everywhere...
    # but pymodbus was implemented first.
    for i in range(0, len(modbus_data), 2):
        data.append(int(modbus_data[i], 16) * 256 + int(modbus_data[i + 1], 16))  # noqa: PERF401
    return data
