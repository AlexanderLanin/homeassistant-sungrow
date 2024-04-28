import logging
from datetime import datetime
from typing import cast

from custom_components.sungrow.core import (
    deserialize,
    modbus_types,
    signals,
)
from custom_components.sungrow.core.modbus_base import ModbusConnectionBase

logger = logging.getLogger(__name__)


class Connection:
    async def connect(self):
        raise NotImplementedError

    async def disconnect(self):
        raise NotImplementedError

    @property
    def slave(self) -> int:
        raise NotImplementedError

    @slave.setter
    def slave(self, value: int):
        raise NotImplementedError

    async def read_single_signal(
        self,
        signal: signals.SungrowSignalDefinition,
    ) -> signals.DatapointValueType | None:
        decoded = await self._read_single_signal(signal)
        signal.determine_and_mark_supported(decoded)
        return decoded

    async def _read_single_signal(
        self,
        signal: signals.SungrowSignalDefinition,
    ) -> signals.DatapointValueType | None:
        raise NotImplementedError

    async def read(
        self,
        query: list[signals.SungrowSignalDefinition],
    ) -> deserialize.DecodedSignals:
        decoded = await self._read(query)
        for name, value in decoded.items():
            signal = next((signal for signal in query if signal.name == name), None)
            assert signal
            signal.determine_and_mark_supported(value)
        return decoded

    async def _read(
        self,
        query: list[signals.SungrowSignalDefinition],
    ) -> deserialize.DecodedSignals:
        raise NotImplementedError


class ModbusConnection(Connection):
    """
    High level connection class.
    Currently it can only wrap a modbus_connection...
    but it should work with any raw connection class.
    Contrary to the wrapped class, this class provides decoded data method!
    """

    def __init__(self, modbus_connection: ModbusConnectionBase):
        super().__init__()
        self.__modbus_connection = modbus_connection

    async def connect(self):
        return await self.__modbus_connection.connect()

    async def disconnect(self):
        return await self.__modbus_connection.disconnect()

    @property
    def slave(self):
        return self.__modbus_connection.slave

    @slave.setter
    def slave(self, value):
        self.__modbus_connection.slave = value

    async def _read_single_signal(
        self,
        signal: signals.SungrowSignalDefinition,
    ) -> signals.DatapointValueType | None:
        """Warning: Very inefficient! Use pull_signals for multiple signals!!"""

        pull_start = datetime.now()
        raw = (await self.__modbus_connection.read([signal]))[signal.name]
        elapsed = datetime.now() - pull_start

        logger.debug(
            "Inverter: pulled single signal in "
            f"{elapsed.seconds}.{elapsed.microseconds} secs"
        )

        return deserialize.decode_signal(signal, raw) if raw else None

    async def _read(
        self,
        query: list[signals.SungrowSignalDefinition],
    ) -> deserialize.DecodedSignals:
        """Pull data from inverter"""

        pull_start = datetime.now()

        # Downcast to base class to make mypy happy
        signal_definitions_base = cast(list[modbus_types.Signal], query)
        raw_data = await self.__modbus_connection.read(signal_definitions_base)

        elapsed = datetime.now() - pull_start

        logger.debug(
            f"Inverter: Pulled {len(query)} signals in "
            f"{elapsed.seconds}.{elapsed.microseconds} secs"
        )

        return deserialize.decode_signals(
            query,
            raw_data,
        )

    async def __aenter__(self):
        await self.__modbus_connection.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.__modbus_connection.__aexit__(exc_type, exc_value, traceback)
