"""
Builds the register ranges for the modbus read and hold requests.
This is complex enough to deserve its own module.
"""
import logging

from custom_components.sungrow.core.modbus_types import (
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


def can_add(
    current_range: list[Signal],
    signal: Signal,
    max_registers_per_range: int,
    blocked_registers: list[int],
) -> bool:
    """Check if the signal can be added to the current range."""
    if not current_range:
        return True

    if signal.end - current_range[0].address > max_registers_per_range:
        return False

    anything_blocked = any(
        addr in blocked_registers
        for addr in range(current_range[-1].end, signal.address)
    )

    if anything_blocked:
        return False

    return True


def _build_ranges(
    register_type: RegisterType,
    signals: list[Signal],
    max_registers_per_range: int,
    blocked_registers: list[int],
) -> list[list[Signal]]:
    ranges: list[list[Signal]] = []

    current_range: list[Signal] = []

    for signal in _sorted_and_filtered(signals, register_type):
        if can_add(current_range, signal, max_registers_per_range, blocked_registers):
            current_range.append(signal)
        else:
            ranges.append(current_range)
            current_range = []

    if current_range:
        ranges.append(current_range)

    return ranges


def split_list(
    signals: list[Signal],
    max_registers_per_range: int,
    blocked_registers: dict[RegisterType, list[int]],
) -> list[list[Signal]]:
    """
    Split the list of signals into ranges.
    Each range is guaranteed to:
    - not contain any blocked registers
    - not exceed the max_registers_per_range
    - be sorted by address
    - only contain signals of the same register type
    """
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
