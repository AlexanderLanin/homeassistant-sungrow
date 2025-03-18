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


class BusyError(Err):
    """Inverter is busy, retry later."""

    ...


class TokenExpiredError(Err):
    """Token expired, fetch a new token first."""

    ...


class TooManyRetriesError(Err):
    """Too many retries, giving up."""

    ...


class InvalidResponseError(Err):
    """Invalid response from inverter."""

    def __init__(self):
        super().__init__("Invalid response from inverter")


class GenericError(Err):
    """Generic error."""

    def __init__(self):
        super().__init__("Generic error")


AnyError = (
    BusyError
    | TokenExpiredError
    | TooManyRetriesError
    | InvalidResponseError
    | GenericError
)


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

    async def _ws_query(self, query: dict[str, str | int]):
        # Potential services: connect, devicelist, state, statistics, runtime, real
        assert self._ws is not None

        try:
            await self._ws.send_json(query)
            response: dict = await self._ws.receive_json()
        except Exception as e:
            logger.error(f"Cannot send message to inverter: {e}")
            await self.disconnect()
            return GenericError()

        return _parse_ws_response(response)

    async def _get_new_token(self) -> Result[str, ErrorResponse]:
        response = await self._ws_query(
            {"lang": "en_us", "token": "", "service": "connect"}
        )
        if isinstance(response, Err):
            return response

        val = response.ok_value
        if isinstance(val, dict) and isinstance(val.get("token"), str):
            return Ok(str(val.get("token")))
        else:
            logger.error("Invalid response from inverter: %s", response)
            return Err(ErrorResponse.InvalidResponse)

    async def _get_connected_devices(
        self,
    ) -> Result[list[dict[str, str]], ErrorResponse]:
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
        return response.and_then(lambda x: Ok(x.get("list")))

    async def connect(self):
        """
        Establish permanent websocket connection to the WiNet dongle
        and retrieve a token.

        No (clasic) http connection is established!

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

    async def _query(
        self, url: str, params: dict[str, str | int]
    ) -> Result[dict[str, Any], ErrorResponse]:
        """Query the inverter via http GET."""

        try:
            async with await self._aio_client.get(url, params=params) as r:
                if r.status == 200:
                    return Ok(await r.json())
                else:
                    logger.error(
                        "Invalid response from inverter: %s %s", r.status, r.text
                    )
                    return Err(ErrorResponse.InvalidResponse)
        except ErrorResponse as e:
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

    class BusyError(ErrorResponse):
        pass

    class TokenExpiredError(ErrorResponse):
        pass

    async def _query_http_json(self, rr: RegisterRange) -> Result[dict, ErrorResponse]:
        _last_error = None
        for attempt in range(3):
            if attempt > 0:
                # Add 1 second delay before next attempt
                await asyncio.sleep(1)

            if not await self.connect():
                _last_error = modbus_connection_base.CannotConnectError()
                continue

            # (Re-)build query with current token
            url, params = self._build_http_request_for_register_query(rr)

            response = await self._query(url, params)
            if isinstance(response, Err):
                # connection failed
                _last_error = response.err_value
                continue

            parsed = _parse_sungrow_response(response.ok_value)
            if isinstance(parsed, Err):
                _last_error = parsed.err_value
                if isinstance(
                    parsed.err_value, ModbusConnection_Http.TokenExpiredError
                ):
                    logger.debug("Token expired, reconnecting")
                    await self.disconnect()
                elif isinstance(parsed.err_value, ModbusConnection_Http.BusyError):
                    logger.debug("Inverter busy, will retry after some delay")
                    await asyncio.sleep(5)
                continue
            return parsed

        # All retries exhausted
        # TODO: append last_error to error message?!
        return Err(ErrorResponse.TooManyRetries)

    async def _read_range(self, rr: RegisterRange) -> Result[list[int], ErrorResponse]:
        # Note: websocket does not allow access to all possible registers.
        # Not quite clear whether it's worth the effort to query some via websocket and
        # only the rest via http.

        json = await self._query_http_json(rr)
        if isinstance(json, Ok):
            return _parse_modbus_data(json.ok_value, rr.length)
        else:
            return json

    def __str__(self):
        return f"http({self._host}:{self._port}, slave: {self._slave or 'unknown'})"


def _parse_sungrow_response(response: dict[str, Any]) -> Result[dict, ErrorResponse]:
    logger.debug(f"Response: {response}")
    if response["result_code"] == 1:
        return Ok(response["result_data"])
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


def _parse_modbus_data(
    response_json: dict[str, str], expected_length: int
) -> Result[list[int], modbus_connection_base.ModbusError]:
    modbus_data = response_json["param_value"].split(" ")
    logger.debug(f"Got modbus data: {modbus_data}")

    # There is always an extra null at the end, remove it.
    modbus_data.pop()

    if len(modbus_data) != expected_length * 2:
        return Err(
            modbus_connection_base.ModbusError(
                "Invalid response from inverter: "
                f"{response_json} => {modbus_data}, "
                f"expected length {expected_length}"
            )
        )

    data: list[int] = []
    # Merge two consecutive bytes into 16 bit integers, same as pymodbus.
    # Maybe it would be better to use bytes everywhere...
    # but pymodbus was implemented first.
    for i in range(0, len(modbus_data), 2):
        data.append(int(modbus_data[i], 16) * 256 + int(modbus_data[i + 1], 16))  # noqa: PERF401
    return Ok(data)


def _parse_ws_response(
    response: dict[str, Any],
):
    if (
        isinstance(response, dict)
        and response.get("result_code") == 1
        and response.get("result_msg") == "success"
        and response.get("result_data")  # is not None
    ):
        return Ok(response["result_data"])
    else:
        logger.error(f"Invalid websocket response from inverter: {response}")
        return InvalidResponseError()
