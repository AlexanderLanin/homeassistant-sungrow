import logging
from datetime import datetime
from typing import cast

from result import Ok, Result

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
    def connected(self) -> bool:
        raise NotImplementedError

    @property
    def slave(self) -> int:
        raise NotImplementedError

    @slave.setter
    def slave(self, value: int):
        raise NotImplementedError

    async def read(
        self,
        query: list[signals.SungrowSignalDefinition] | signals.SungrowSignalDefinition,
    ) -> Result[deserialize.DecodedSignals, Exception]:
        # Always convert to a list to avoid different code paths
        if isinstance(query, signals.SungrowSignalDefinition):
            query = [query]
        single_item_query = len(query) == 1

        def get_signal_by_name(name):
            return next((signal for signal in query if signal.name == name), None)

        result = await self._read(query)
        if isinstance(result, Ok):
            decoded = result.ok_value
            for name, value in decoded.items():
                signal = get_signal_by_name(name)
                assert signal
                signal.update_supported_state_based_on_value(
                    value, was_queried_individually=single_item_query
                )

        return result

    async def _read(
        self,
        query: list[signals.SungrowSignalDefinition],
    ) -> Result[deserialize.DecodedSignals, Exception]:
        raise NotImplementedError


# TODO: move to own file or somewhere. Maybe even merge into modbus_base.py
class DecodedModbusConnection(Connection):
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
    def connected(self) -> bool:
        return self.__modbus_connection.connected

    @property
    def slave(self):
        return self.__modbus_connection.slave

    @slave.setter
    def slave(self, value):
        self.__modbus_connection.slave = value

    async def _read(
        self,
        query: list[signals.SungrowSignalDefinition],
    ) -> Result[deserialize.DecodedSignals, Exception]:
        """Pull data from inverter"""

        # Downcast to base class to make mypy happy
        signal_definitions_base = cast(list[modbus_types.Signal], query)

        pull_start = datetime.now()
        raw_data_result = await self.__modbus_connection.read(signal_definitions_base)
        elapsed = datetime.now() - pull_start
        logger.debug(
            f"Inverter: Pulled {len(query)} signals in "
            f"{elapsed.seconds}.{elapsed.microseconds} secs"
        )

        if isinstance(raw_data_result, Ok):
            raw_data = raw_data_result.ok_value
            decoded = deserialize.decode_signals(
                query,
                raw_data,
            )
            return Ok(decoded)
        else:
            return raw_data_result

    async def __aenter__(self):
        await self.__modbus_connection.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.__modbus_connection.__aexit__(exc_type, exc_value, traceback)
