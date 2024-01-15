"""
The abstraction level is chosen at the lowest point which does not need to know how
signals are queried. This is where all signals are read() at once, so this class
can perform a clever optimization to reduce the number of queries.
"""

import logging

from custom_components.sungrow.core.modbus_range_builder import build_ranges
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


def map_raw_to_signals(
    raw_data: dict[RegisterType, RawData], signal_list: list[Signal]
) -> MappedData:
    """
    Note: While this doesn't sound like it belongs into this class,
    it's usually also not intended to be called directly, but by read().
    But for some less common use cases it might be useful to call this directly
    """
    return {
        signal.name: ModbusConnectionBase._get_values_for_signal(
            raw_data[signal.register_type], signal
        )
        for signal in signal_list
    }


def split_range_into_halfs(
    signals: list[Signal], range: RegisterRange
) -> tuple[RegisterRange, RegisterRange]:
    """
    Splits the given range into two halfs.
    The first half will be shorter if the range has an odd length.
    """
    # FIXME split across signals, not registers

    assert range.length > 1
    t = range.register_type
    first_half = RegisterRange(t, range.start, range.length // 2)
    second_half = RegisterRange(t, first_half.end, range.end - first_half.end)

    assert first_half.length + second_half.length == range.length
    assert second_half.end == range.end

    return first_half, second_half


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

    def __init__(self, host: str, port: int, slave: int):
        self._host = host
        self._port = port
        self._slave = slave
        self._detached = False
        self._read_calls = 0 # Make this a full blown stats object? e.g. connections, read calls, read errors, etc.

        # These signals are not supported by the inverter.
        # This is required, as we read entire ranges at once and need to avoid having
        # any of these within the range we reading.
        self._problematic_registers: dict[RegisterType, list[int]] = {
            RegisterType.READ: [],
            RegisterType.HOLD: [],
        }

    @property
    def read_calls(self):
        return self._read_calls

    def detach(self):
        """Detach from context manager."""
        self._detached = True
        return self

    async def connect(self):
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
        logger.debug(f"read_raw({len(signal_list)} signals)")

        if not await self.connect():
            raise CannotConnectError("Not connected to inverter, but read() was called")

        # We cannot query all signals at once, as the inverter will not respond.
        # So we split the signals into ranges and query each range separately.
        # Build as few ranges as possible:
        ranges = build_ranges(
            signal_list, max_combined_registers, self._problematic_registers
        )
        logger.debug(f"Ranges: {ranges}")

        # Read each range
        raw_data: dict[RegisterType, RawData] = {r: {} for r in RegisterType}
        for r in ranges:
            values = await self._read_range_base(signal_list, r)
            raw_data[r.register_type].update(values)
        return raw_data

    async def __aenter__(self):
        """Called on 'async with' enter."""
        if not await self.connect():
            raise CannotConnectError()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Called on 'async with' exit."""
        if not self._detached:
            await self.disconnect()

    async def _call_read_raw(self, range: RegisterRange) -> RawData:
        """Wrapper for _read_range() that returns RawData."""
        logger.debug(f"_call_read_raw({range})")

        self._read_calls += 1

        # _read_range() is implemented by the subclass.
        # It's returning a list of registers, so we need to map it.
        raw_list = await self._read_range(
            register_type=range.register_type,
            address_start=range.start,
            address_count=range.length,
        )
        raw_dict: RawData = {range.start + i: value for i, value in enumerate(raw_list)}
        return raw_dict

    async def _read_range_base(
        self, signal_list: list[Signal], reg_range: RegisterRange
    ) -> RawData:
        """Wrapper for _read_range() that handles unsupported registers."""
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
            # We'll abort when a single register is queried or when a single signal is
            # queried.
            # FIXME: overlap is wrong!! covered by a single signal is the question!!
            # Since we might not have all signals in the list! Only the ones that were
            # actually queried.
            overlapping = signals_overlapping_range(signal_list, reg_range)
            if reg_range.length == 1 or len(overlapping) == 1:
                logger.debug(f"Failed to read {reg_range} ({overlapping})")
                for addr in range(reg_range.start, reg_range.end):
                    self._problematic_registers[reg_range.register_type].append(addr)

                # Indicate that this signal is not supported.
                return {r: None for r in range(reg_range.start, reg_range.end)}
            else:
                # Let's try to find out which signal is causing the problem.
                # We do this by splitting the range in half and trying each half.
                first_half, second_half = split_range_into_halfs(overlapping, reg_range)
                logger.debug(
                    "Calling _read_range_base recursively on "
                    f"{first_half} and {second_half}"
                )
                a = await self._read_range_base(signal_list, first_half)
                b = await self._read_range_base(signal_list, second_half)
                assert a.keys().isdisjoint(b.keys())
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

    @staticmethod
    def _get_values_for_signal(r: RawData, signal: Signal):
        all_available = all(
            r.get(addr) is not None
            for addr in range(signal.address, signal.end)
        )
        if not all_available:
            return None

        return [r[signal.address + i] for i in range(signal.length)]

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
