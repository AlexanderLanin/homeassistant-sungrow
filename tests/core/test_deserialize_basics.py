import fix_path  # type: ignore  # noqa: F401

from custom_components.sungrow.core import deserialize, modbus_py, signals


def simple_signal(base_datatype, mask=None, accuracy=None, decoded=None):
    return signals.SungrowSignalDefinition(
        register_type=modbus_py.RegisterType.READ,
        address=0,
        array_length=1,
        name="test",
        base_datatype=base_datatype,
        element_length=1,  # do we need to adapt this for tests?
        unit_of_measurement=None,
        disabled=[],
        group=None,
        accuracy=accuracy,
        mask=mask,
        decoded=decoded,
        models=None,
        models_exclude=None,
        level=None,
    )


def decode_simple_signal(
    base_datatype: str, value: list[int], mask=None, accuracy=None, decoded=None
):
    signal = simple_signal(base_datatype, mask, accuracy, decoded)
    signal_definitions = signals.SignalDefinitions({"test_signal": signal})
    decoded = deserialize.decode_signals(signal_definitions, {"test_signal": value})
    return decoded["test_signal"]


def test_deserialize_int():
    # 0, 1, MAX, None
    assert decode_simple_signal("U16", [0]) == 0
    assert decode_simple_signal("U16", [1]) == 1
    assert decode_simple_signal("U16", [0xFFFE]) == 0xFFFE
    assert decode_simple_signal("U16", [0xFFFF]) is None

    # ToDo: is the register order actually correct this way? [1,0] or [0,1] for 1?
    # 0, 1, MAX, None
    assert decode_simple_signal("U32", [0, 0]) == 0
    assert decode_simple_signal("U32", [1, 0]) == 1
    assert decode_simple_signal("U32", [0xFFFE, 0xFFFF]) == 0xFFFFFFFE
    assert decode_simple_signal("U32", [0xFFFF, 0xFFFF]) is None

    # 0, 1, MAX, None, -MAX, -1
    assert decode_simple_signal("S16", [0]) == 0
    assert decode_simple_signal("S16", [1]) == 1
    assert decode_simple_signal("S16", [0x7FFE]) == 0x7FFE
    assert decode_simple_signal("S16", [0x7FFF]) is None
    assert decode_simple_signal("S16", [0x8000]) == -0x8000
    assert decode_simple_signal("S16", [0xFFFF]) == -1

    # 0, 1, MAX, None, -MAX, -1
    assert decode_simple_signal("S32", [0, 0]) == 0
    assert decode_simple_signal("S32", [1, 0]) == 1
    assert decode_simple_signal("S32", [0xFFFE, 0x7FFF]) == 0x7FFFFFFE
    assert decode_simple_signal("S32", [0xFFFF, 0x7FFF]) is None
    assert decode_simple_signal("S32", [0, 0x8000]) == -0x80000000
    assert decode_simple_signal("S32", [0xFFFF, 0xFFFF]) == -1
