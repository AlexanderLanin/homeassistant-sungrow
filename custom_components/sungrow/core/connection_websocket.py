"""
Websocket connection to WiNet dongles.
While they provide a modbus interface, it is rather limited.
"""
from SungrowModbusWebClient.SungrowModbusWebClient import (  # type: ignore
    SungrowModbusWebClient,
)


class Connection:
    def __init__(self, host: str, port: int = 8082):
        self._client = SungrowModbusWebClient(host, port)
        self._detached = False

    def detach(self):
        """Detach from context manager."""
        self._detached = True
        return self

    async def connect(self):
        self._client.connect()
