from custom_components.sungrow.core.modbus_range_builder import build_ranges
from custom_components.sungrow.core.modbus_types import (
    RegisterRange,
    RegisterType,
    Signal,
)


def simple_signal(name, address, register_type=RegisterType.READ, element_length=1):
    return Signal(
        name=name,
        address=address,
        element_length=element_length,
        array_length=1,
        register_type=register_type,
    )


def test_modbus_calculate_ranges_trivial():
    signals = [simple_signal("A", 1000)]

    assert build_ranges(signals, 100) == [
        RegisterRange(RegisterType.READ, start=1000, length=1),
    ]


def test_modbus_calculate_ranges_bounds():
    signals = [
        simple_signal("A", 1000),
        simple_signal("B", 1099),
    ]

    assert build_ranges(signals, 100) == [
        RegisterRange(RegisterType.READ, start=1000, length=100),
    ]


def test_modbus_calculate_ranges_bounds_mixed():
    signals = [
        simple_signal("A", 1000),
        simple_signal("D", 1050, RegisterType.HOLD),
        simple_signal("B", 1099),
        simple_signal("E", 1149, RegisterType.HOLD),
    ]

    assert build_ranges(signals, 100) == [
        RegisterRange(RegisterType.READ, start=1000, length=100),
        RegisterRange(RegisterType.HOLD, start=1050, length=100),
    ]


def test_modbus_calculate_ranges_blocked():
    signals = [
        simple_signal("A", 5000),
        simple_signal("B", 5020),
    ]

    assert build_ranges(signals, 100) == [
        RegisterRange(RegisterType.READ, start=5000, length=21),
    ]

    # blocked registers outside the range should not matter
    assert build_ranges(signals, 100, {RegisterType.READ: [4999, 5021]}) == [
        RegisterRange(RegisterType.READ, start=5000, length=21),
    ]

    # blocked registers in the middle prevent merging
    assert build_ranges(signals, 100, {RegisterType.READ: [5010]}) == [
        RegisterRange(RegisterType.READ, start=5000, length=1),
        RegisterRange(RegisterType.READ, start=5020, length=1),
    ]
