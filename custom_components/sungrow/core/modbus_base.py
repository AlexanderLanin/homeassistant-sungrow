"""
The abstraction level is chosen at the lowest point which does not need to know how
signals are queried. This is where all signals are read() at once, so this class
can perform a clever optimization to reduce the number of queries.
"""

import logging

from custom_components.sungrow.core.modbus_range_builder import build_ranges
from custom_components.sungrow.core.modbus_types import (
    RegisterRange,
    RegisterType,
    Signal,
)

logger = logging.getLogger(__name__)

# e.g. {RegisterType.READ: {0: 123, 1: 456}}
# in case the register is not supported, the value is None
RawData = dict[RegisterType, dict[int, int | None]]

# e.g. {"ac_power": [123, 456]}
MappedData = dict[str, list[int] | None]


class ModbusError(Exception):
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
    pass


class ModbusConnectionBase:
    """A pymodbus connection to a single slave."""

    def __init__(self, host: str, port: int, slave: int):
        self._host = host
        self._port = port
        self._slave = slave
        self._detached = False

        # These signals are not supported by the inverter.
        # We will not try to read them again.
        # This is required, as we read entire ranges at once and need to avoid having
        # any of these within the range we reading.
        self._problematic_registers: list[int] = []

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
        if not await self.connect():
            raise CannotConnectError("Not connected to inverter, but read() was called")

        # We cannot query all signals at once, as the inverter will not respond.
        # So we split the signals into ranges and query each range separately.
        ranges = self._calculate_ranges(
            signal_list, max_length_per_range=max_combined_registers
        )

        # Read each range
        # TODO: can we run these in parallel? via asyncio.gather()
        all: MappedData = {}
        for r in ranges:
            range_values = await self._read_range_base(signal_list, r)
            all.update(range_values)
        return all

    ## -- DETAILED IMPLEMENTATION --

    async def __aenter__(self):
        """Called on 'async with' enter."""
        if not await self.connect():
            raise CannotConnectError()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Called on 'async with' exit."""
        if not self._detached:
            await self.disconnect()

    def _calculate_ranges(
        self, signals: list[Signal], max_length_per_range=100
    ) -> list[RegisterRange]:
        """
        Create as few ranges as possible from a list of signals.

        Note: this accepts a tuple of signals, not a list.
        The idea is that usually the same list of signals is passed to this function.
        This is a simple attempt to speed up the function.
        """
        return build_ranges(signals, max_length_per_range, self._problematic_registers)

    async def _call_read_raw_and_map_to_signals(
        self, range: RegisterRange, signal_list: list[Signal]
    ) -> MappedData:
        raw_list = await self._read_range(
            register_type=range.register_type,
            address_start=range.start,
            address_count=range.length,
        )
        raw_dict: RawData = {
            range.register_type: {
                range.start + i: value for i, value in enumerate(raw_list)
            }
        }
        return ModbusConnectionBase.map_raw_to_signals(raw_dict, signal_list)

    async def _read_range_base(
        self, signal_list: list[Signal], range: RegisterRange
    ) -> MappedData:
        try:
            # Try reading the entire range at once.
            # Usually this will work, except at startup.
            return await self._call_read_raw_and_map_to_signals(range, signal_list)
        except UnsupportedRegisterQueriedError:
            logger.debug(
                f"Failed to read {range.register_type} registers "
                f"from {range.start} to {range.start + range.length}."
            )

            # Some registers are not supported by WiNet.
            # That means we need to break up the range and try again.
            signals_in_failed_range = (
                ModbusConnectionBase._get_signals_in_a_register_range(
                    signal_list, range
                )
            )
            # This if differentiates between first appearance of problem and
            # second attempt (recursive call).
            if len(signals_in_failed_range) == 1:
                signal = signals_in_failed_range[0]

                logger.debug(
                    f"Failed to read {signal.name}, stopping further attempts."
                )
                # It's enough to store the address, not the length.
                # Future ranges will not be extended over that address.
                self._problematic_registers.append(signal.address)

                # Indicate that this signal is not supported.
                return {signal.name: None}
            else:
                # Let's try to find out which signal is causing the problem.
                # This is slow, but as it's only done once per inverter, there is no
                # major need to optimize this.
                logger.debug("Reading each signal individually...")
                # FIXME as we dont read the entire range this could miss the problematic register!!!
                # That means we always end up in the exceptional case.
                return await self.read(
                    signals_in_failed_range, max_combined_registers=1
                )

    @staticmethod
    def map_raw_to_signals(raw_data: RawData, signal_list: list[Signal]) -> MappedData:
        """
        Note: While this doesn't sound like it belongs into this class,
        it's usually also not intended to be called directly, but by read().
        But for some less common use cases it might be useful to call this directly
        """
        return {
            signal.name: ModbusConnectionBase._get_values_for_signal(raw_data, signal)
            for signal in signal_list
        }

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
            if signal.register_type == register_range.register_type
            and signal.address >= register_range.start
            and signal.address + signal.length
            <= register_range.start + register_range.length
        ]

    @staticmethod
    def _get_values_for_signal(all_data: RawData, signal: Signal):
        r = all_data[signal.register_type]

        all_available = all(
            r.get(addr) is not None
            for addr in range(signal.address, signal.address + signal.length)
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
