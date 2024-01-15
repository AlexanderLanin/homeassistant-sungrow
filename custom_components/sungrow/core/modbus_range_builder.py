"""
Builds the register ranges for the modbus read and hold requests.
This is complex enough to deserve its own module.
"""
import logging

from custom_components.sungrow.core.modbus_types import (
    RegisterRange,
    RegisterType,
    Signal,
)

logger = logging.getLogger(__name__)


def _sorted_and_filtered(
    signals: list[Signal], register_type: RegisterType
) -> list[Signal]:
    return sorted(
        filter(lambda s: s.register_type == register_type, signals),
        key=lambda s: s.address,
    )


class _ModifyableRange:
    register_type: RegisterType
    start: int
    length: int

    def __init__(self, signal: Signal):
        self.register_type = signal.register_type
        self.start = signal.address
        self.length = signal.length

    @property
    def end(self) -> int:
        """The register address after the last register in the range."""
        return self.start + self.length

    @end.setter
    def end(self, value: int):
        """Set the end register address, thats the last register + 1."""
        logger.debug(f"Setting end of {self} to {value}")
        assert 0 < value < 65536
        self.length = value - self.start
        assert 0 < self.length < 256

    def add(self, signal: Signal):
        """Add a signal to the range."""
        logger.debug(
            f"Adding {signal.name} ({signal.address}-{signal.end}) to range {self}"
        )
        assert signal.register_type == self.register_type
        self.end = signal.end

    def to_register_range(self) -> RegisterRange:
        return RegisterRange(self.register_type, self.start, self.length)

    def __str__(self):
        return f"Range({self.register_type}, {self.start}-{self.end-1})"

    def can_add(
        self,
        signal: Signal,
        max_registers_per_range: int,
        blocked_registers: list[int],
    ) -> bool:
        """Check if the signal can be added to the current range."""

        if signal.end - self.start > max_registers_per_range:
            return False

        anything_blocked = any(
            addr in blocked_registers for addr in range(self.end, signal.address)
        )

        if anything_blocked:
            return False

        return True


def _build_ranges(
    register_type: RegisterType,
    signals: list[Signal],
    max_registers_per_range: int,
    blocked_registers: dict[RegisterType, list[int]],
) -> list[RegisterRange]:
    ranges: list[RegisterRange] = []
    current_range: _ModifyableRange | None = None

    for signal in _sorted_and_filtered(signals, register_type):
        if current_range is None:
            current_range = _ModifyableRange(signal)
        elif current_range.can_add(signal, max_registers_per_range, blocked_registers):
            current_range.add(signal)
        else:
            ranges.append(current_range.to_register_range())
            current_range = _ModifyableRange(signal)

    if current_range is not None:
        ranges.append(current_range.to_register_range())

    return ranges


def build_ranges(
    signals: list[Signal],
    max_registers_per_range: int,
    blocked_registers: dict[RegisterType, list[int]],
) -> list[RegisterRange]:
    # We need to build the ranges for read and hold separately, as they can't be
    # mixed/combined.
    return [
        *_build_ranges(
            RegisterType.READ,
            signals,
            max_registers_per_range,
            blocked_registers[RegisterType.READ],
        ),
        *_build_ranges(
            RegisterType.HOLD,
            signals,
            max_registers_per_range,
            blocked_registers[RegisterType.HOLD],
        ),
    ]
