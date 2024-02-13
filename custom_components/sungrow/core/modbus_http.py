import asyncio
import logging
import os
import time
from enum import StrEnum
from typing import Any, cast

import aiohttp

import custom_components.sungrow.core.modbus_base as modbus_base
from custom_components.sungrow.core.modbus_base import (
    ModbusConnectionBase,
    RegisterType,
)

logger = logging.getLogger(__name__)


class HttpConnection(ModbusConnectionBase):
    def __init__(self, host: str, slave: int, port: int = 8082):
        _ = slave  # unused
        super().__init__(host, port, 0)  # FIXME: slave is not used. Remove from Base?

        self._aio_client = aiohttp.ClientSession()
        self._ws: aiohttp.client.ClientWebSocketResponse | None = None

        self._token: str | None = None
        self._inverter: dict[str, str] | None = None

    async def _ws_query(self, query: dict[str, str | int]) -> dict[str, Any]:
        # Potential services: connect, devicelist, state, statistics, runtime, real
        assert self._ws is not None

        await self._ws.send_json(query)

        response: dict = await self._ws.receive_json()

        if (
            response.get("result_code") == "1"
            and response.get("result_msg") == "success"
            and response.get("result_data") is not None
        ):
            return cast(dict[str, Any], response["result_data"])
        else:
            raise modbus_base.ModbusError(f"Inverter responded with: {response}")

    async def _get_new_token(self) -> str:
        response = await self._ws_query(
            {"lang": "en_us", "token": "", "service": "connect"}
        )
        return cast(str, response["token"])

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
        return cast(list[dict[str, str]], response["list"])

    async def connect(self):
        """
        Retrieves the token from the WiNet dongle.
        No permanent connection is established!

        Returns true/false on success/failure.
        Raises modbus.CannotConnectError on WiNet misbehavior.
        """

        if self._token:
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

    async def _get_json(self, url: str, params: dict[str, str | int]) -> dict[str, Any]:
        try:
            async with await self._aio_client.get(url, params=params) as r:
                logger.debug(f"Got r response: {r}")
                if r.status == 200:
                    v = cast(dict, await r.json())
                    return v
                else:
                    raise modbus_base.ModbusError(
                        f"Invalid response from inverter: {r.status} {r.text}"
                    )
        except Exception as e:
            # e.g. response is not valid json
            raise modbus_base.ModbusError(f"Connection Failed: {e}") from e

    def _build_address_for_register_query(  # noqa: N802
        self,
        address_start: int,
        address_count: int,
        register_type: modbus_base.RegisterType,
    ) -> tuple[str, dict[str, str | int]]:
        assert self._inverter
        assert self._token

        param_types = {
            modbus_base.RegisterType.READ: 0,
            modbus_base.RegisterType.HOLD: 1,
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
            "param_addr": address_start,
            "param_num": address_count,
            "param_type": param_types[register_type],
            "token": self._token,
            "lang": "en_us",
            "time123456": int(time.time()),
        }
        return url, params

    class ErrorResponse(StrEnum):
        Busy = "retry"
        TokenExpired = "token_expired"

    def _parse_sungrow_response_old(
        self, response: dict[str, Any]
    ) -> dict[str, Any] | ErrorResponse:
        logger.debug(f"Response: {response}")
        if response["result_code"] == 1:
            return cast(dict, response["result_data"])
        elif response["result_code"] == 106:
            return HttpConnection.ErrorResponse.TokenExpired
        elif response["result_code"] == 301:
            # Wild guess what 301 means. It's not in the official documentation.
            # Seems to work out if we retry after a reasonable delay.
            return HttpConnection.ErrorResponse.Busy
        else:
            raise modbus_base.ModbusError(f"Unknown response from inverter: {response}")

    async def _query_http_json_old(
        self,
        address_start: int,
        address_count: int,
        register_type: modbus_base.RegisterType,
    ):
        if not await self.connect():
            raise modbus_base.CannotConnectError("Connection failed")

        url, params = self._build_address_for_register_query(
            address_start, address_count, register_type
        )
        parsed = self._parse_sungrow_response_old(await self._get_json(url, params))

        if isinstance(parsed, HttpConnection.ErrorResponse):
            if parsed == HttpConnection.ErrorResponse.TokenExpired:
                logger.debug("Token expired, reconnecting")
                await self.disconnect()
                # retry once
                parsed = self._parse_sungrow_response_old(
                    await self._get_json(url, params)
                )
            elif parsed == HttpConnection.ErrorResponse.Busy:
                # retry after a delay
                await asyncio.sleep(5)
                parsed = self._parse_sungrow_response_old(
                    await self._get_json(url, params)
                )
            else:
                raise modbus_base.ModbusError(f"Unknown error: {parsed}")

            if isinstance(parsed, HttpConnection.ErrorResponse):
                raise modbus_base.ModbusError(f"Persistent error: {parsed}")

        return parsed

    class BusyError(Exception):
        pass

    class TokenExpiredError(Exception):
        pass

    def _parse_sungrow_response(self, response: dict[str, Any]) -> dict[str, Any]:
        logger.debug(f"Response: {response}")
        if response["result_code"] == 1:
            return cast(dict, response["result_data"])
        elif response["result_code"] == 106:
            raise HttpConnection.TokenExpiredError()
        elif response["result_code"] == 301:
            # Wild guess what 301 means. It's not in the official documentation.
            # Seems to work out if we retry after a reasonable delay.
            raise HttpConnection.BusyError()
        else:
            raise modbus_base.ModbusError(f"Unknown response from inverter: {response}")

    async def _query_http_json(
        self,
        address_start: int,
        address_count: int,
        register_type: modbus_base.RegisterType,
    ):
        # Note: refactor into for _attempt in range(3).
        # But this is not done yet to make this lool exactly like the old code.

        if not await self.connect():
            raise modbus_base.CannotConnectError("Connection failed")

        url, params = self._build_address_for_register_query(
            address_start, address_count, register_type
        )
        try:
            parsed = self._parse_sungrow_response(await self._get_json(url, params))
        except HttpConnection.TokenExpiredError:
            logger.debug("Token expired, reconnecting")
            await self.disconnect()
            if not await self.connect():
                raise modbus_base.CannotConnectError(
                    "Cannot reconnect for new token"
                ) from None
            # Rebuild query with new token
            url, params = self._build_address_for_register_query(
                address_start, address_count, register_type
            )
            parsed = self._parse_sungrow_response(await self._get_json(url, params))
        except HttpConnection.BusyError:
            # retry after a delay
            await asyncio.sleep(5)
            parsed = self._parse_sungrow_response(await self._get_json(url, params))

        return parsed

    async def _read_range(
        self,
        register_type: RegisterType,
        address_start: int,
        address_count: int,
    ) -> list[int]:
        """Raises modbus.CannotConnectError on WiNet misbehavior."""

        # Note: websocket does not allow access to all possible registers.
        # Not quite clear whether it's worth the effort to query some via websocket and
        # only the rest via http.

        response_json = await self._query_http_json(
            address_start, address_count, register_type
        )

        logger.debug(f"Got data: {response_json}")

        return _parse_modbus_data(response_json, address_count)


def _parse_modbus_data(
    response_json: dict[str, Any], expected_length: int
) -> list[int]:
    modbus_data = response_json["param_value"].split(" ")
    logger.debug(f"Got modbus data: {modbus_data}")
    modbus_data.pop()  # remove null on the end

    if len(modbus_data) != expected_length * 2:
        raise modbus_base.ModbusError(
            "Invalid response from inverter: "
            f"{response_json} => {modbus_data}, "
            f"expected length {expected_length}"
        )

    data: list[int] = []
    # Merge two consecutive bytes into 16 bit integers, same as modbus.
    # Maybe it would be better to use bytes everywhere...
    # but modbus was here first.
    for i in range(0, len(modbus_data), 2):
        data.append(int(modbus_data[i], 16) * 256 + int(modbus_data[i + 1], 16))
    return data
