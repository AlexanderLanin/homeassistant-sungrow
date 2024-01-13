from custom_components.sungrow.core.modbus_base import (
    ModbusConnectionBase,
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

    assert ModbusConnectionBase._calculate_ranges(signals) == [
        RegisterRange(RegisterType.READ, start=1000, length=1),
    ]


def test_modbus_calculate_ranges_bounds():
    signals = [
        simple_signal("A", 1000),
        simple_signal("B", 1099),
    ]

    assert ModbusConnectionBase._calculate_ranges(signals) == [
        RegisterRange(RegisterType.READ, start=1000, length=100),
    ]


def test_modbus_calculate_ranges_bounds_mixed():
    signals = [
        simple_signal("A", 1000),
        simple_signal("D", 1050, RegisterType.HOLD),
        simple_signal("B", 1099),
        simple_signal("E", 1149, RegisterType.HOLD),
    ]

    assert ModbusConnectionBase._calculate_ranges(signals) == [
        RegisterRange(RegisterType.READ, start=1000, length=100),
        RegisterRange(RegisterType.HOLD, start=1050, length=100),
    ]


def test_modbus_calculate_ranges_small():
    signals = [
        simple_signal("A", 4950, RegisterType.READ, 2),
        simple_signal("D", 1050, RegisterType.HOLD),
        simple_signal("B", 1099),
        simple_signal("E", 1149, RegisterType.HOLD),
    ]

    assert ModbusConnectionBase._calculate_ranges(signals) == [
        RegisterRange(RegisterType.READ, start=1000, length=100),
        RegisterRange(RegisterType.HOLD, start=1050, length=100),
    ]


def test_modbus_calculate_ranges_mixed():
    signals = [
        Signal(
            name="A",
            address=1000,
            element_length=10,
            array_length=1,
            register_type=RegisterType.READ,
        ),
        Signal(
            name="B",
            address=2000,
            element_length=5,
            array_length=1,
            register_type=RegisterType.READ,
        ),
        Signal(
            name="C",
            address=3000,
            element_length=20,
            array_length=1,
            register_type=RegisterType.HOLD,
        ),
        Signal(
            name="D",
            address=4000,
            element_length=15,
            array_length=1,
            register_type=RegisterType.READ,
        ),
    ]

    expected_ranges = [
        RegisterRange(RegisterType.READ, start=1000, length=10),
        RegisterRange(RegisterType.READ, start=2000, length=5),
        RegisterRange(RegisterType.READ, start=4000, length=15),
        RegisterRange(RegisterType.HOLD, start=3000, length=20),
    ]

    ranges = ModbusConnectionBase._calculate_ranges(signals)

    assert ranges == expected_ranges
