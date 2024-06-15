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


def _guess_connection_classes(connection: str | None, port: int | None):
    """Returns connection classes worth trying."""

    if connection == "http" or port == ModbusConnection_Http.default_port():
        return [ModbusConnection_Http]

    if connection == "modbus" or port == ModbusConnection_Pymodbus.default_port():
        return [ModbusConnection_Pymodbus]

    elif connection is None and port is None:
        # TODO: which one do we prefer?
        return [
            ModbusConnection_Pymodbus,
            ModbusConnection_Http,
        ]

    else:
        # Non standard port can only mean modbus proxy
        return [ModbusConnection_Pymodbus]


async def connect(ci: ConnectionParams):
    """Apply a clever heuristic to missing parameters and connect to the inverter."""

    connection_classes = _guess_connection_classes(ci.connection, ci.port)
    for cc in connection_classes:
        port = ci.port or cc.default_port()
        connection_obj = cc(ci.host, port)

        if await connection_obj.connect():
            return connection_obj

    logger.debug("Failed to connect to inverter")
    return None
