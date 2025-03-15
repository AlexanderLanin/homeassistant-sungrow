import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import overload

from .modbus_connection_http import ModbusConnection_Http
from .modbus_connection_pymodbus import ModbusConnection_Pymodbus

logger = logging.getLogger(__name__)


class ConnectionMode(StrEnum):
    HTTP_WEBSOCKET = "http"
    MODBUS = "modbus"
    ANY = "any"


@dataclass
class ConnectionParams:
    host: str
    port: int | None
    mode: ConnectionMode = ConnectionMode.ANY


def _get_all_connection_variants(params: ConnectionParams):
    # If mode is already set, return the params as is
    if params.mode != ConnectionMode.ANY:
        return [params]

    # If port looks like a http port, assume http connection
    if params.port == ModbusConnection_Http.default_port():
        return [
            ConnectionParams(
                host=params.host, port=params.port, mode=ConnectionMode.HTTP_WEBSOCKET
            )
        ]

    elif params.port is not None:
        # Non http port can only mean modbus proxy
        return [
            ConnectionParams(
                host=params.host, port=params.port, mode=ConnectionMode.MODBUS
            )
        ]

    else:
        # Undefined port and undefined mode... that's bad.
        # Let's try standard modbus port and standard http port.
        return [
            ConnectionParams(
                host=params.host,
                port=ModbusConnection_Pymodbus.default_port(),
                mode=ConnectionMode.MODBUS,
            ),
            ConnectionParams(
                host=params.host,
                port=ModbusConnection_Http.default_port(),
                mode=ConnectionMode.HTTP_WEBSOCKET,
            ),
        ]


def _get_connection_cls(
    connection: ConnectionMode,
) -> type[ModbusConnection_Http | ModbusConnection_Pymodbus]:
    return {
        ConnectionMode.HTTP_WEBSOCKET: ModbusConnection_Http,
        ConnectionMode.MODBUS: ModbusConnection_Pymodbus,
    }[connection]


@overload
async def connect(
    host: ConnectionParams,
) -> ModbusConnection_Http | ModbusConnection_Pymodbus | None: ...


@overload
async def connect(
    host: str, port: int | None, mode: ConnectionMode = ConnectionMode.ANY
) -> ModbusConnection_Http | ModbusConnection_Pymodbus | None: ...


async def connect(
    host: ConnectionParams | str,
    port: int | None = None,
    mode: ConnectionMode = ConnectionMode.ANY,
) -> ModbusConnection_Http | ModbusConnection_Pymodbus | None:
    if isinstance(host, ConnectionParams):
        connection_params = host
    else:
        connection_params = ConnectionParams(host=host, port=port, mode=mode)

    connection_variants = _get_all_connection_variants(connection_params)
    for variant in connection_variants:
        assert variant.mode != ConnectionMode.ANY

        cls = _get_connection_cls(variant.mode)
        connection_obj = cls(variant.host, variant.port)

        logger.debug(f"Trying to connect to inverter using {variant.mode} connection")
        if await connection_obj.connect():
            logger.debug("Successfully connected to inverter")
            return connection_obj

    logger.debug("Failed to connect to inverter")
    return None
