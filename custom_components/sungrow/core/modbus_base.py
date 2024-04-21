"""
The abstraction level is chosen so signals are read() at once, and all modbus
optimizations/limitations are handled within this class.
Basically it's pure modbus, with a (hopefully) better interface.
"""

import logging
from dataclasses import dataclass

from custom_components.sungrow.core.modbus_range_builder import split_list
from custom_components.sungrow.core.modbus_types import (
    MappedData,
    RawData,
    RegisterRange,
    RegisterType,
    Signal,
)

logger = logging.getLogger(__name__)


class ModbusError(Exception):
    """Generic error for all modbus related errors."""


class InvalidSlaveError(ModbusError):
    pass


class CannotConnectError(ModbusError):
    pass


class UnsupportedRegisterQueriedError(ModbusError):
    """
    WiNet: ALL queried registers are unsupported.

    Note: this exception is raised by implementations of ModbusConnectionBase, but it's
    never forwared to the user. Instead, the implementation will return None for the
    unsupported registers.
    """


def _map_raw_to_signal(r: RawData, signal: Signal):
    # We'll use the first register to check if signal is supported.
    if r[signal.registers.start] is None:
        return None
    else:
        result: list[int] = []
        for i in range(signal.registers.length):
            v = r[signal.registers.start + i]
            # This can never happen, as there is just no way for a None to appear
            # in the middle of a range.
            # Ranges are cut at signal borders.
            # Each signal is either fully supported or not at all.
            assert v is not None
            result.append(v)
        return result


def _map_raw_to_signals(
    raw_data: dict[RegisterType, RawData], signal_list: list[Signal]
) -> MappedData:
    """
    Note: While this doesn't sound like it belongs into this class,
    it's usually also not intended to be called directly, but by read().
    But for some less common use cases it might be useful to call this directly
    """
    return {
        signal.name: _map_raw_to_signal(
            raw_data[signal.registers.register_type], signal
        )
        for signal in signal_list
    }


class ModbusConnectionBase:
    """A pymodbus connection to a single slave."""

    @dataclass
    class Stats:
        connections: int = 0
        read_calls_success: int = 0
        read_calls_failed: int = 0
        retrieved_signals_success: int = 0
        retrieved_signals_failed: int = 0

    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
        self._stats = ModbusConnectionBase.Stats()
        self._slave: int | None = None

        # These signals are not supported by the inverter.
        # This is required, as we read entire ranges at once and need to avoid having
        # any of these within the range we reading.
        self._problematic_registers: dict[RegisterType, list[int]] = {
            RegisterType.READ: [],
            RegisterType.HOLD: [],
        }

    @property
    def slave(self):
        return self._slave

    @slave.setter
    def slave(self, value: int):
        logger.debug(f"Setting slave to {value}")
        self._slave = value

    @property
    def stats(self):
        return self._stats

    async def connect(self):
        # Note: for proper stats, you need to increase self._stats.connections
        raise NotImplementedError

    async def disconnect(self):
        raise NotImplementedError

    async def read(
        self, signal_list: list[Signal], max_combined_registers=100
    ) -> MappedData:
        raw_data = await self.read_raw(signal_list, max_combined_registers)
        return _map_raw_to_signals(raw_data, signal_list)

    ## -- DETAILED IMPLEMENTATION --

    async def read_raw(
        self, signal_list: list[Signal], max_combined_registers=100
    ) -> dict[RegisterType, RawData]:
        if not await self.connect():
            raise CannotConnectError("Not connected to inverter, but read() was called")

        # We cannot query all signals at once, as the inverter will not respond.
        # So we split the signals into ranges and query each range separately.
        # Build as few ranges as possible:
        ranges = split_list(signal_list, max_combined_registers)

        if len(ranges) > 1 or len(signal_list) > 5:
            logger.debug(
                f"read_raw({len(signal_list)} signals) in {len(ranges)} ranges"
            )
        else:
            logger.debug(f"read_raw({[s.name for s in signal_list]})")

        # Read each range
        raw_data: dict[RegisterType, RawData] = {r: {} for r in RegisterType}
        for signal_list in ranges:
            values = await self._read_range_base(signal_list)
            raw_data[signal_list[0].registers.register_type].update(values)

        return raw_data

    async def __aenter__(self):
        """Called on 'async with' enter."""
        logger.debug(f"__aenter__({self._host}, {self._port}, {self._slave})")
        if not await self.connect():
            raise CannotConnectError("Cannot connect to inverter")
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Called on 'async with' exit."""
        logger.debug(f"__aexit__({self._host}, {self._port}, {self._slave})")
        await self.disconnect()

    async def _call_read_raw(self, r: RegisterRange) -> RawData:
        """Wrapper for _read_range() that returns RawData."""
        # logger.debug(f"_call_read_raw({r})")

        # _read_range() is implemented by the subclass.
        # It's returning a list of registers, so we need to map it.
        try:
            raw_list = await self._read_range(r)
            self._stats.read_calls_success += 1
        except Exception:
            self._stats.read_calls_failed += 1
            raise

        raw_dict: RawData = {r.start + i: value for i, value in enumerate(raw_list)}
        return raw_dict

    async def _read_range_base(self, signal_list: list[Signal]) -> RawData:
        """
        Wrapper for _read_range() that handles unsupported registers.
        Returns None for unsupported registers.
        """
        assert signal_list

        reg_range = RegisterRange(
            signal_list[0].registers.register_type,
            signal_list[0].registers.start,
            signal_list[-1].registers.end - signal_list[0].registers.start,
        )
        # logger.debug(f"_read_range_base({reg_range})")

        try:
            # Try reading the entire range at once.
            # Usually this will work, except at startup.
            data = await self._call_read_raw(reg_range)
        except UnsupportedRegisterQueriedError:
            for signal in signal_list:
                self.stats.retrieved_signals_failed += 1
                logger.debug(
                    f"Unuspported Register: {signal.name} ({signal.registers})"
                )
                self._problematic_registers[signal.registers.register_type].append(
                    signal.registers.start
                )

            return {r: None for r in range(reg_range.start, reg_range.end)}
        else:
            self.stats.retrieved_signals_success += len(signal_list)
            return data

    async def _read_range(self, register_range: RegisterRange) -> list[int]:
        """
        Reads `address_count` registers of type `register_type` starting at
        `address_start`.
        Note: each register is 16 bits, so `address_count` is the number of registers,
        not bytes.
        """
        raise NotImplementedError
