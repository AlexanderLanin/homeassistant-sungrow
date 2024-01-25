from custom_components.sungrow.core.modbus_range_builder import (
    sorted_and_filtered,
    split_list,
)
from custom_components.sungrow.core.modbus_types import (
    RegisterType,
    Signal,
)


def call_split_list(
    signals: list[Signal],
    max_registers_per_range: int,
    blocked_registers: dict[RegisterType, list[int]] | None = None,
):
    if blocked_registers is None:
        blocked_registers = {RegisterType.READ: [], RegisterType.HOLD: []}
    else:
        if RegisterType.READ not in blocked_registers:
            blocked_registers[RegisterType.READ] = []
        if RegisterType.HOLD not in blocked_registers:
            blocked_registers[RegisterType.HOLD] = []

    return split_list(
        signals,
        max_registers_per_range,
        blocked_registers,
    )


def simple_signal(name, address, register_type=RegisterType.READ, element_length=1):
    return Signal(
        name=name,
        address=address,
        element_length=element_length,
        array_length=1,
        register_type=register_type,
    )


def test_trivial():
    signals = [simple_signal("A", 1000)]
    assert call_split_list(signals, 100) == [signals]


def test_bounds():
    signals = [
        simple_signal("A", 1000),
        simple_signal("B", 1099),
        simple_signal("C", 1100),
    ]
    assert call_split_list(signals, 100) == [signals[0:2], signals[2:3]]


def test_mixed():
    signals = [
        simple_signal("A", 1000),
        simple_signal("D", 1050, RegisterType.HOLD),
        simple_signal("B", 1099),
        simple_signal("E", 1149, RegisterType.HOLD),
    ]
    result = call_split_list(signals, 100)
    assert sorted_and_filtered(signals, RegisterType.READ) in result
    assert sorted_and_filtered(signals, RegisterType.HOLD) in result
    assert len(result) == 2


def test_blocked_registers():
    signals = [
        simple_signal("A", 5000),
        simple_signal("B", 5020),
    ]

    assert call_split_list(signals, 100) == [signals]

    # blocked registers outside the range should not matter
    assert call_split_list(signals, 100, {RegisterType.READ: [4999, 5021]}) == [signals]

    # blocked registers in the middle prevent merging
    assert call_split_list(signals, 100, {RegisterType.READ: [5010]}) == [
        [signals[0]],
        [signals[1]],
    ]
