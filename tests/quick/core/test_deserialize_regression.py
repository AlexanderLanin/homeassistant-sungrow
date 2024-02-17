import pathlib
from typing import cast

import pytest
import yaml

from custom_components.sungrow.core import deserialize, modbus_base, signals
from custom_components.sungrow.core.modbus_types import RegisterType

TEST_DATA = pathlib.Path(__file__).parent.parent / "test_data"


def first_key(d: dict):
    return next(iter(d.keys()))


def last_key(d: dict):
    return next(reversed(d.keys()))


def data_from_modbus_Connection_read_raw(  # noqa: N802
    filename: str,
) -> tuple[
    dict[RegisterType, modbus_base.RawData], dict[str, signals.DatapointValueType]
]:
    yaml_data = yaml.safe_load((TEST_DATA / filename).read_text())

    registers = {
        RegisterType.READ: yaml_data["registers"]["read"],
        RegisterType.HOLD: yaml_data["registers"]["hold"],
    }
    signal_data = cast(dict[str, signals.DatapointValueType], yaml_data["signals"])
    return registers, signal_data


def reencode_registers(
    filename: str,
) -> tuple[
    dict[str, signals.DatapointValueType], dict[str, signals.DatapointValueType]
]:
    # same as we get from the read_raw() call:
    raw_data, expected_signals = data_from_modbus_Connection_read_raw(filename)

    signal_list = signals.load_yaml()

    mapped_data = modbus_base.map_raw_to_signals(
        raw_data, signal_list.enabled_modbus_signals()
    )

    actual_signals = deserialize.decode_signals(signal_list.all_signals(), mapped_data)

    return expected_signals, actual_signals


@pytest.mark.skip(reason="Test is disabled. Not sure yet what do do with it.")
def test_decoding_regression_1():
    expected, actual = reencode_registers("dump_master.yaml")
    assert len(expected) == len(actual)
    for key in expected:
        assert expected[key] == actual[key]


@pytest.mark.skip(reason="Test is disabled. Not sure yet what do do with it.")
def test_decoding_regression_2():
    expected, actual = reencode_registers("dump_slave.yaml")
    assert len(expected) == len(actual)
    for key in expected:
        assert expected[key] == actual[key]