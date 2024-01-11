"""
A convinience wrapper for pymodbus.

The abstraction level is chosen at the lowest point which does not need to know how
signals are queried. This is where all signals are read() at once, so this class
can perform a clever optimization to reduce the number of queries.
"""

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from enum import StrEnum

import pymodbus
import pymodbus.client
import pymodbus.exceptions
import pymodbus.pdu

logger = logging.getLogger(__name__)


class RegisterType(StrEnum):
    READ = "read"
    HOLD = "hold"


# e.g. {RegisterType.READ: {0: 123, 1: 456}}
RawData = dict[RegisterType, dict[int, int]]

# e.g. {"ac_power": [123, 456]}
MappedData = dict[str, list[int]]


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


@dataclass
class Signal:
    name: str
    register_type: RegisterType
    address: int
    element_length: int
    array_length: int

    @property
    def length(self):
        return self.element_length * self.array_length


class Connection:
    """A pymodbus connection to a single slave."""

    def __init__(self, host: str, port: int, slave: int):
        self._slave = slave
        self._detached = False

        self._client = pymodbus.client.AsyncModbusTcpClient(
            host=host, port=port, timeout=2, retries=1, retry_on_empty=True
        )

    def detach(self):
        """Detach from context manager."""
        self._detached = True
        return self

    async def connect(self):
        if self._client.connected:
            return True
        else:
            return await self._client.connect()

    async def disconnect(self):
        # The _client has a 'reconnect_task' which it will cancel and delete on close().
        # But we want to wait for it to actually finish before returning,
        # so we are cleaning up properly.
        # Specifically, pytest will complain about lingering tasks if we don't wait for
        # this task to finish.
        reconnect_task = self._client.reconnect_task
        self._client.close()
        if reconnect_task:
            # Catch CancelledError, as this is expected.
            with contextlib.suppress(asyncio.CancelledError):
                await reconnect_task

    async def read(
        self,
        signal_list: list[Signal],
    ) -> MappedData:
        """
        Read a list of signals.
        """

        raw_values = await self.read_raw(signal_list)
        return Connection.map_raw_to_signals(raw_values, signal_list)

    async def detect_signals_causing_problems(
        self, signal_list: list[Signal]
    ) -> list[str]:
        """
        This will try to read every signal separately.
        It's slow!
        """

        problematic: list[str] = []

        for i, signal in enumerate(signal_list):
            if not await self.connect():
                raise RuntimeError("Could not connect")

            try:
                _value = await self._read_range(
                    register_type=signal.register_type,
                    address_start=signal.address,
                    address_count=signal.length,
                )
            except ModbusError:
                problematic.append(signal.name)

                await self.disconnect()
                await asyncio.sleep(2)

            print(f"{i+1}/{len(signal_list)} ({signal.name})")

        if not await self.connect():
            raise RuntimeError("Could not connect")

        return problematic

    ## -- DETAILED IMPLEMENTATION --

    @dataclass(frozen=True)
    class RegisterRange:
        register_type: RegisterType
        start: int
        length: int

    async def __aenter__(self):
        """Called on 'async with' enter."""
        if not await self.connect():
            raise CannotConnectError()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Called on 'async with' exit."""
        if not self._detached:
            await self.disconnect()

    @staticmethod
    # @lru_cache -> neither Signal nor list is hasheable :/
    def _calculate_ranges(
        signals: list[Signal], max_length_per_range=100
    ) -> list[RegisterRange]:
        """
        Create as few ranges as possible from a list of signals.

        Note: this accepts a tuple of signals, not a list.
        The idea is that usually the same list of signals is passed to this function.
        This is a simple attempt to speed up the function.
        """

        ranges: list[Connection.RegisterRange] = []

        @dataclass
        class Range:
            start: int
            length: int

        for register_type in RegisterType:
            next_range: Range | None = None

            for signal in sorted(signals, key=lambda s: s.address):
                if signal.register_type != register_type:
                    continue

                assert signal.length > 0

                if next_range is None:
                    next_range = Range(signal.address, signal.length)

                elif (
                    signal.address + signal.length
                    > next_range.start + max_length_per_range
                ):
                    # Range is too big. Start a new one.
                    ranges.append(
                        Connection.RegisterRange(
                            register_type,
                            next_range.start,
                            next_range.length,
                        )
                    )
                    next_range = Range(signal.address, signal.length)

                else:
                    next_range.length = (
                        signal.address + signal.length - next_range.start
                    )

            if next_range:
                ranges.append(
                    Connection.RegisterRange(
                        register_type, next_range.start, next_range.length
                    )
                )

        return ranges

    async def read_raw(
        self,
        signal_list: list[Signal],
        max_combined_registers: int = 100,
    ) -> RawData:
        """
        Returns a dict of queried register ranges and their values.
        This probably includes more registers than requested.
        """
        if not await self.connect():
            raise CannotConnectError()

        # We cannot query all signals at once, as the inverter will not respond.
        # So we split the signals into ranges and query each range separately.
        ranges = Connection._calculate_ranges(
            signal_list, max_length_per_range=max_combined_registers
        )

        raw_values: RawData = {}

        # Read each range
        for r in ranges:
            range_values = await self._read_range(
                register_type=r.register_type,
                address_start=r.start,
                address_count=r.length,
            )
            if r.register_type not in raw_values:
                raw_values[r.register_type] = {}

            for i, value in enumerate(range_values):
                raw_values[r.register_type][r.start + i] = value

        return raw_values

    @staticmethod
    def map_raw_to_signals(raw_data: RawData, signal_list: list[Signal]) -> MappedData:
        """
        Note: While this doesn't sound like it belongs into this class,
        it's usually also not intended to be called directly, but by read().
        But for some less common use cases it might be useful to call this directly
        """
        mapped: MappedData = {}

        for signal in signal_list:
            mapped[signal.name] = Connection._get_signal_relevant_registers(
                raw_data[signal.register_type], signal
            )

        assert len(mapped) == len(signal_list)
        return mapped

    @staticmethod
    def _get_signal_relevant_registers(registers: dict[int, int], signal: Signal):
        all_available = all(
            addr in registers
            for addr in range(signal.address, signal.address + signal.length)
        )
        if not all_available:
            raise ModbusError(
                f"not all registers available for signal {signal.name} "
                f"at address {signal.address}"
            )

        return [registers[signal.address + i] for i in range(signal.length)]

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
        if not await self.connect():
            raise CannotConnectError()

        try:
            func = {
                RegisterType.READ: self._client.read_input_registers,
                RegisterType.HOLD: self._client.read_holding_registers,
            }[register_type]
            # Note: sending address = protocol address - 1.
            # This is the only line in the module that needs to know about this detail!
            rr = await func(address_start - 1, count=address_count, slave=self._slave)  # type: ignore
        except pymodbus.ModbusException as e:
            # e.g. no response from device
            raise ModbusError(
                f"connection error (for {register_type}, "
                f"{address_start}-{address_start+address_count})"
            ) from e

        if rr.isError():
            logger.info(
                f"device error for {register_type}, "
                f"{address_start}-{address_start+address_count}"
            )

            if isinstance(rr, pymodbus.pdu.ExceptionResponse):
                if rr.exception_code == pymodbus.pdu.ModbusExceptions.GatewayNoResponse:
                    raise InvalidSlaveError(f"Slave ID {self._slave} is invalid")
                else:
                    raise ModbusError(f"Unknown exception response: {rr}")
            else:
                raise ModbusError(f"Unknown error response: {rr}")

        if len(rr.registers) != address_count:
            raise ModbusError(
                f"Mismatched number of registers "
                f"(requested {address_count}) and responded {len(rr.registers)})"
            )

        assert isinstance(rr.registers, list)
        return rr.registers
