import asyncio
import json
import logging
import time
from typing import Any

import httpx
from websocket import create_connection

import custom_components.sungrow.core.modbus_base as modbus_base
from custom_components.sungrow.core.modbus_base import (
    ModbusConnectionBase,
    RegisterType,
)

logger = logging.getLogger(__name__)


class HttpConnection(ModbusConnectionBase):
    def __init__(self, host: str, slave, port: int = 8082):
        _ = slave  # unused
        super().__init__(host, port, 0)  # FIXME: slave is not used. Remove from Base?

        self._httpx_client = httpx.AsyncClient()

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

        self._stats.connections += 1

        # Reset the httpx client, otherwise it will keep the connection open.
        # TODO: why not simply reuse the client?
        await self._httpx_client.aclose()

        # As we cannot reopen the httpx client, we need to create a new one.
        self._httpx_client = httpx.AsyncClient()
        await self._httpx_client.__aenter__()

        endpoint = f"ws://{self._host}:{self._port}/ws/home/overview"
        try:
            socket = create_connection(endpoint, timeout=2)
        except Exception as e:
            # FIXME: this is actually debug, but I want to see what it looks like
            logger.warning(e)
            return False

        logger.debug("Connection to websocket server established")

        socket.send(json.dumps({"lang": "en_us", "token": "", "service": "connect"}))
        response = json.loads(socket.recv())

        if response["result_msg"] == "success":
            self._token = response["result_data"]["token"]
            logger.info(f"Token Retrieved: {self._token}")
        else:
            raise modbus_base.CannotConnectError(
                f"Connection Failed {response['result_msg']}"
            )

        logger.debug("Requesting Device Information")
        socket.send(
            json.dumps(
                {
                    "lang": "en_us",
                    "token": self._token,
                    "service": "devicelist",
                    "type": "0",
                    "is_check_token": "0",
                }
            )
        )

        response = json.loads(socket.recv())
        logger.debug(response)
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

    async def disconnect(self):
        self._token = None
        self._inverter = None

        # Reset the httpx client, otherwise it will keep the connection open.
        await self._httpx_client.aclose()

    async def _handle_response(
        self,
        response: dict[str, Any],
        register_type: RegisterType,
        address_start: int,
    ) -> list[int]:
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
            self.disconnect()
            raise modbus_base.CannotConnectError(
                f"Token Expired: {response.get('result_msg')}"
            )
        elif result_code == 301:  # common read failed
            # For me this really happens on the same register every time.
            # So maybe it's not supported...
            raise modbus_base.UnsupportedRegisterQueriedError("Common Read Failed")
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
    ) -> list[int]:
        """Raises modbus.CannotConnectError on WiNet misbehavior."""

        if not self._token:
            connected = self.connect()
            if not connected:
                raise modbus_base.CannotConnectError("Connection failed")

        assert self._inverter

        param_types = {
            modbus_base.RegisterType.READ: 0,
            modbus_base.RegisterType.HOLD: 1,
        }

        await asyncio.sleep(0.3)  # Server simply disconnects if we query too fast.

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
        url = f"http://{self._host}/device/getParam?"
        for k, v in params.items():
            url += f"{k}={v}&"

        logger.debug(f"getting: {url}")
        try:
            r = await self._httpx_client.get(url)
        except Exception as e:
            raise modbus_base.CannotConnectError(f"Connection Failed: {e}") from None

        if r.status_code == 200:
            response = r.json()
            return await self._handle_response(response, register_type, address_start)
        else:
            raise modbus_base.CannotConnectError(
                f"Connection Failed: {r.status_code} {r.text}"
            )
