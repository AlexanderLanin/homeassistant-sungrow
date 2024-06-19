import logging
from dataclasses import dataclass

from .modbus_connection_http import ModbusConnection_Http
from .modbus_connection_pymodbus import ModbusConnection_Pymodbus

logger = logging.getLogger(__name__)


@dataclass
class ConnectionParams:
    host: str
    port: int | None
    connection: str | None


def all_possible_connection_params(params: ConnectionParams):
    if params.connection:
        return [params]

    if params.port == ModbusConnection_Http.default_port():
        params.connection = "http"
        return [params]

    elif params.port is not None:
        # Non http port can only mean modbus proxy
        params.connection = "modbus"
        return [params]

    else:
        return [
            ConnectionParams(connection="modbus", host=params.host, port=None),
            ConnectionParams(connection="http", host=params.host, port=None),
        ]


def get_connection_cls(
    connection: str,
) -> type[ModbusConnection_Http | ModbusConnection_Pymodbus]:
    return {
        "http": ModbusConnection_Http,
        "modbus": ModbusConnection_Pymodbus,
    }[connection]


async def connect(params: ConnectionParams):
    """Apply a clever heuristic to missing parameters and connect to the inverter."""

    all_possible_params = all_possible_connection_params(params)
    for p in all_possible_params:
        assert p.connection
        cls = get_connection_cls(p.connection)
        connection_obj = cls(p.host, p.port)

        if await connection_obj.connect():
            return connection_obj

    logger.debug("Failed to connect to inverter")
    return None
