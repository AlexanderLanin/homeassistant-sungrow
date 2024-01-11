import asyncio
import json
import logging
import sys
import time

import httpx
from websocket import create_connection

from . import modbus, signals

logger = logging.getLogger(__name__)


class Connection:
    def __init__(self, host: str, port: int = 8082):
        self._host = host
        self._port = port
        self._httpx_client = httpx.AsyncClient()

        self._token: str | None = None
        self._inverter: dict[str, str | int] | None = None

    async def __aenter__(self):
        await self._httpx_client.__aenter__()
        if not await self.connect():
            raise modbus.CannotConnectError(
                f"Connection to {self._host}:{self._port} failed"
            )
        return self

    async def __aexit__(self, *args, **kwargs):
        await self._httpx_client.__aexit__(*args, **kwargs)

    async def connect(self):
        """
        Retrieves the token from the WiNet dongle.
        No permanent connection is established!

        Returns true/false on success/failure.
        Raises modbus.CannotConnectError on WiNet misbehavior.
        """

        if self._token:
            return True

        endpoint = f"ws://{self._host}:{self._port}/ws/home/overview"
        try:
            socket = create_connection(endpoint, timeout=2)
        except Exception as e:
            print(e)
            return False

        logger.debug("Connection to websocket server established")

        socket.send(json.dumps({"lang": "en_us", "token": "", "service": "connect"}))
        response = json.loads(socket.recv())

        if response["result_msg"] == "success":
            self._token = response["result_data"]["token"]
            logger.info(f"Token Retrieved: {self._token}")
        else:
            raise modbus.CannotConnectError(
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
            raise modbus.CannotConnectError(
                f"Connection Failed {response['result_msg']}"
            )

        return True

    async def disconnect(self):
        self._token = None
        self._inverter = None

    async def read(self, signal_definitions: list[modbus.Signal]) -> modbus.MappedData:
        data: modbus.MappedData = {}

        # FIXME can we use the range approach?
        for signal in signal_definitions:
            # ToDo: can we run these in parallel or will the inverter fail?
            print(f"Reading {signal.name}...")
            try:
                v = await self.read_signal(signal)
            except modbus.CannotConnectError:
                print("Failed, retrying in 5 seconds...")
                await asyncio.sleep(5)
                v = await self.read_signal(signal)
            data.update(v)

            sys.stdout.flush()

        return data

    async def read_signal(self, signal: modbus.Signal) -> modbus.MappedData:
        """Raises modbus.CannotConnectError on WiNet misbehavior."""

        if not self._token:
            connected = self.connect()
            if not connected:
                raise modbus.CannotConnectError("Connection failed")

        assert self._inverter

        param_types = {
            modbus.RegisterType.READ: 0,
            modbus.RegisterType.HOLD: 1,
        }

        params = {
            "dev_id": self._inverter["dev_id"],
            "dev_type": self._inverter["dev_type"],
            "dev_code": self._inverter["dev_code"],
            "type": "3",  # todo: Why 3?
            "param_addr": signal.address,
            "param_num": signal.length,
            "param_type": param_types[signal.register_type],
            "token": self._token,
            "lang": "en_us",
            "time123456": time.time(),
        }
        url = f"http://{self._host}/device/getParam?"
        for k, v in params.items():
            url += f"{k}={v}&"

        logger.debug(f"getting: {url}")
        r = await self._httpx_client.get(url)
        if r.status_code == 200:
            response = r.json()
            logger.debug("Response: {response}")
            result_code = response.get("result_code", 0)
            if result_code == 1:
                modbus_data = response["result_data"]["param_value"].split(" ")
                modbus_data.pop()  # remove null on the end
                data: list[int] = []
                # Merge two consecutive bytes into 16 bit integers, same as modbus.
                # Maybe it would be better to use bytes everywhere...
                # but modbus was here first.
                for i in range(0, len(modbus_data), 2):
                    data.append(
                        int(modbus_data[i], 16) * 256 + int(modbus_data[i + 1], 16)
                    )
                return {signal.name: data}
            elif response.get("result_code", 0) == 106:  # token expired
                self.disconnect()
                raise modbus.CannotConnectError(
                    f"Token Expired: {response.get('result_msg')}"
                )
            else:
                raise modbus.CannotConnectError(
                    f"_Unknown response while trying to query {signal.name}: {response} "
                )
        else:
            raise modbus.CannotConnectError(
                f"_Connection Failed: {r.status_code} {r.text}"
            )
