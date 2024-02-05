import asyncio
import logging
import time
from typing import Any

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
        self._inverter: dict[str, str | int] | None = None

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

            await self._ws.send_json(
                {"lang": "en_us", "token": "", "service": "connect"}
            )
            logger.debug("Reading Token...")
            response = await self._ws.receive_json(timeout=5)
            logger.debug(f"Response: {response}")

            if response["result_msg"] == "success":
                self._token = response["result_data"]["token"]
                logger.info(f"Token Retrieved: {self._token}")
            else:
                raise modbus_base.CannotConnectError(
                    f"Connection Failed {response['result_msg']}"
                )

            logger.debug("Requesting Device Information")
            await self._ws.send_json(
                {
                    "lang": "en_us",
                    "token": self._token,
                    "service": "devicelist",
                    "type": "0",
                    "is_check_token": "0",
                }
            )

            response = await self._ws.receive_json(timeout=5)
            logger.debug(f"Response 2: {response}")
            # pprint(response)

            if response["result_msg"] == "success":
                # The first device is always the inverter.
                # ToDo: can we do anything with the others?
                self._inverter = response["result_data"]["list"][0]
            else:
                raise modbus_base.CannotConnectError(
                    f"Connection Failed {response['result_msg']}"
                )

            return True
        except Exception as e:
            logger.debug(f"Connection failed: {e}")
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

    async def _parse_response(
        self,
        response: dict[str, Any],
        register_type: RegisterType,
        address_start: int,
    ) -> list[int] | str:
        logger.debug(f"Response: {response}")
        result_code = response.get("result_code", 0)
        if result_code == 1:
            modbus_data = response["result_data"]["param_value"].split(" ")
            modbus_data.pop()  # remove null on the end
            data: list[int] = []
            # Merge two consecutive bytes into 16 bit integers, same as modbus.
            # Maybe it would be better to use bytes everywhere...
            # but modbus was here first.
            for i in range(0, len(modbus_data), 2):
                data.append(int(modbus_data[i], 16) * 256 + int(modbus_data[i + 1], 16))
            return data
        elif result_code == 106:  # token expired
            self._token = None
            await self.disconnect()
            raise modbus_base.CannotConnectError(
                f"Token Expired: {response.get('result_msg')}"
            )
        elif result_code == 301:  # common read failed
            return "retry"
        else:
            raise modbus_base.ModbusError(
                "Unknown response while trying to query "
                f"{register_type} {address_start}: {response} "
            )

    async def _read_range(
        self,
        register_type: RegisterType,
        address_start: int,
        address_count: int,
        recursion: bool = False,
    ) -> list[int]:
        """Raises modbus.CannotConnectError on WiNet misbehavior."""

        if not self._token:
            connected = await self.connect()
            if not connected:
                raise modbus_base.CannotConnectError("Connection failed")

        assert self._inverter

        param_types = {
            modbus_base.RegisterType.READ: 0,
            modbus_base.RegisterType.HOLD: 1,
        }

        await asyncio.sleep(0.5)  # Server simply disconnects if we query too fast.

        url = f"http://{self._host}/device/getParam"
        params = {
            "dev_id": self._inverter["dev_id"],
            "dev_type": self._inverter["dev_type"],
            "dev_code": self._inverter["dev_code"],
            "type": "3",  # todo: Why 3?
            "param_addr": address_start,
            "param_num": address_count,
            "param_type": param_types[register_type],
            "token": self._token,
            "lang": "en_us",
            "time123456": time.time(),
        }
        logger.debug(f"getting: {url} / {params}")

        try:
            async with await self._aio_client.get(url, params=params) as r:
                if r.status == 200:
                    response = await r.json()
                    value = await self._parse_response(
                        response, register_type, address_start
                    )
                    if isinstance(value, str):
                        assert value == "retry"

                        if recursion:
                            raise modbus_base.ModbusError(
                                "Unknown problem while trying to query "
                                f"{register_type} {address_start}: {response} "
                            )
                        else:
                            logger.debug(
                                "Tried to read too much too fast! Waiting 10 seconds..."
                            )
                            await asyncio.sleep(10)

                            return await self._read_range(
                                register_type,
                                address_start,
                                address_count,
                                recursion=True,
                            )
                    else:
                        return value
                else:
                    raise modbus_base.CannotConnectError(
                        f"Connection Failed: {r.status} {r.text}"
                    )

        except Exception as e:
            # e.g. response is not valid json
            raise modbus_base.CannotConnectError(f"Connection Failed: {e}") from None
