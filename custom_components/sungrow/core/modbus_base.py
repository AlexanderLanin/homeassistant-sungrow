"""
The abstraction level is chosen at the lowest point which does not need to know how
signals are queried. This is where all signals are read() at once, so this class
can perform a clever optimization to reduce the number of queries.
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

    pass


class InvalidSlaveError(ModbusError):
    """
    Unfortunately this error almost never happens.
    Usually we simply get no response from the device.
    """

    pass


class CannotConnectError(ModbusError):
    pass


class UnsupportedRegisterQueriedError(ModbusError):
    """
    When the implementing class throws this, the base class will try to read
    each register individually to find out which one is not supported.

    It will then avoid querying that register in the future.
    """

    pass


def map_raw_to_signal(r: RawData, signal: Signal):
    all_available = all(
        r.get(addr) is not None for addr in range(signal.address, signal.end)
    )
    if not all_available:
        return None

    return [r[signal.address + i] for i in range(signal.length)]


def map_raw_to_signals(
    raw_data: dict[RegisterType, RawData], signal_list: list[Signal]
) -> MappedData:
    """
    Note: While this doesn't sound like it belongs into this class,
    it's usually also not intended to be called directly, but by read().
    But for some less common use cases it might be useful to call this directly
    """
    return {
        signal.name: map_raw_to_signal(raw_data[signal.register_type], signal)
        for signal in signal_list
    }


def signals_overlapping_range(
    signals: list[Signal], range: RegisterRange
) -> list[Signal]:
    """
    Returns a list of signals that partially overlap with the given range.
    """
    return [
        signal
        for signal in signals
        if signal.register_type == range.register_type
        and signal.address < range.end
        and signal.end > range.start
    ]


class ModbusConnectionBase:
    """A pymodbus connection to a single slave."""

    @dataclass
    class Stats:
        connections: int = 0
        read_calls: int = 0
        read_errors: int = 0

    def __init__(self, host: str, port: int, slave: int):
        self._host = host
        self._port = port
        self._slave = slave
        self._detached = False
        self._stats = ModbusConnectionBase.Stats()

        # These signals are not supported by the inverter.
        # This is required, as we read entire ranges at once and need to avoid having
        # any of these within the range we reading.
        self._problematic_registers: dict[RegisterType, list[int]] = {
            RegisterType.READ: [],
            RegisterType.HOLD: [],
        }

    @property
    def stats(self):
        return self._stats

    def detach(self):
        """Detach from context manager."""
        self._detached = True
        return self

    async def connect(self):
        # Note: for proper stats, you need to increase self._stats.connections
        raise NotImplementedError()

    async def disconnect(self):
        raise NotImplementedError()

    async def read(
        self, signal_list: list[Signal], max_combined_registers=100
    ) -> MappedData:
        raw_data = await self.read_raw(signal_list, max_combined_registers)
        return map_raw_to_signals(raw_data, signal_list)

    ## -- DETAILED IMPLEMENTATION --

    async def read_raw(
        self, signal_list: list[Signal], max_combined_registers=100
    ) -> dict[RegisterType, RawData]:
        if not await self.connect():
            raise CannotConnectError("Not connected to inverter, but read() was called")

        # We cannot query all signals at once, as the inverter will not respond.
        # So we split the signals into ranges and query each range separately.
        # Build as few ranges as possible:
        ranges = split_list(
            signal_list, max_combined_registers, self._problematic_registers
        )

        logger.debug(f"read_raw({len(signal_list)} signals) -> {len(ranges)} ranges")

        # Read each range
        raw_data: dict[RegisterType, RawData] = {r: {} for r in RegisterType}
        for range in ranges:
            assert range[-1].end - range[0].address <= max_combined_registers

            values = await self._read_range_base(range)
            raw_data[range[0].register_type].update(values)
        return raw_data

    async def __aenter__(self):
        """Called on 'async with' enter."""
        if not await self.connect():
            raise CannotConnectError("Cannot connect to inverter")
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Called on 'async with' exit."""
        if not self._detached:
            await self.disconnect()

    async def _call_read_raw(self, range: RegisterRange) -> RawData:
        """Wrapper for _read_range() that returns RawData."""
        logger.debug(f"_call_read_raw({range})")

        # _read_range() is implemented by the subclass.
        # It's returning a list of registers, so we need to map it.
        try:
            self._stats.read_calls += 1
            raw_list = await self._read_range(
                register_type=range.register_type,
                address_start=range.start,
                address_count=range.length,
            )
        except Exception:
            self._stats.read_errors += 1
            raise

        raw_dict: RawData = {range.start + i: value for i, value in enumerate(raw_list)}
        return raw_dict

    async def _read_range_base(self, signal_list: list[Signal]) -> RawData:
        """Wrapper for _read_range() that handles unsupported registers."""
        assert signal_list

        reg_range = RegisterRange(
            signal_list[0].register_type,
            signal_list[0].address,
            signal_list[-1].end - signal_list[0].address,
        )
        logger.debug(f"_read_range_base({reg_range})")

        try:
            # Try reading the entire range at once.
            # Usually this will work, except at startup.
            return await self._call_read_raw(reg_range)
        except UnsupportedRegisterQueriedError:
            logger.debug(f"{reg_range} contains unsupported registers.")

            # Some registers are not supported.
            # That means we need to break up the range and try again.

            # This if differentiates between first appearance of problem and
            # second attempt (recursive call).
            if len(signal_list) == 1:
                signal = signal_list[0]
                logger.debug(f"Failed to read {signal}")
                self._problematic_registers[signal.register_type].append(signal.address)
                return {r: None for r in range(signal.address, signal.end)}
            else:
                # Split in half and try again.
                first_half = signal_list[: len(signal_list) // 2]
                second_half = signal_list[len(signal_list) // 2 :]
                a = await self._read_range_base(first_half)
                b = await self._read_range_base(second_half)
                a.update(b)
                return a

    @staticmethod
    def _get_signals_in_a_register_range(
        signals: list[Signal], register_range: RegisterRange
    ) -> list[Signal]:
        """
        Returns a list of signals that are fully contained in the given register range.
        """
        # TODO: would it be simpler to store the signals within RegisterRange?
        return [
            signal
            for signal in signals
            # TODO: is_index_in_range(). See other TODO.
            if signal.register_type == register_range.register_type
            and signal.address >= register_range.start
            and signal.end <= register_range.end
        ]

    async def _read_range(
        self,
        register_type: RegisterType,
        address_start: int,
        address_count: int,
    ) -> list[int]:
        """
        Reads `address_count` registers of type `register_type` starting at
        `address_start`.
        Note: each register is 16 bits, so `address_count` is the number of registers,
        not bytes.
        """
        raise NotImplementedError()
