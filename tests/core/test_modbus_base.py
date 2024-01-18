import fix_path  # type: ignore  # noqa: F401
import pytest

from custom_components.sungrow.core.modbus_base import split_range_into_halfs
from custom_components.sungrow.core.modbus_types import (
    RegisterRange,
    RegisterType,
    Signal,
)

READ = RegisterType.READ
HOLD = RegisterType.HOLD


def test_split_range_trivial_empty():
    signal_list = []
    with pytest.raises(ValueError):
        split_range_into_halfs(signal_list, RegisterRange(READ, 100, 10))


def test_split_range_trivial_single():
    signal_list = [
        Signal("A", READ, 103, 1, 1),
    ]
    with pytest.raises(ValueError):
        split_range_into_halfs(signal_list, RegisterRange(READ, 100, 10))


def test_split_range_trivial_small():
    signal_list = [
        Signal("A", READ, 100, 1, 1),
        Signal("B", READ, 101, 1, 1),
    ]
    assert split_range_into_halfs(signal_list, RegisterRange(READ, 100, 2)) == (
        RegisterRange(READ, 100, 1),
        RegisterRange(READ, 101, 1),
    )


def test_split_range_trivial_big():
    signal_list = [
        Signal("A", READ, 100, 5, 1),
        Signal("B", READ, 105, 5, 1),
    ]
    assert split_range_into_halfs(signal_list, RegisterRange(READ, 100, 10)) == (
        RegisterRange(READ, 100, 5),
        RegisterRange(READ, 105, 5),
    )


def test_split_range_account_for_empty_borders():
    # No signals at 100, 101, 109, 110
    signal_list = [
        Signal("A", READ, 102, 3, 1),
        Signal("B", READ, 105, 3, 1),
    ]
    assert split_range_into_halfs(signal_list, RegisterRange(READ, 100, 10)) == (
        RegisterRange(READ, 102, 3),
        RegisterRange(READ, 105, 3),
    )


def test_split_range_gaps():
    signal_list = [
        Signal("A", READ, 102, 2, 1),
        Signal("B", READ, 106, 2, 1),
    ]
    assert split_range_into_halfs(signal_list, RegisterRange(READ, 100, 10)) == (
        RegisterRange(READ, 102, 2),
        RegisterRange(READ, 106, 2),
    )


def test_split_range_uneven():
    signal_list = [
        Signal("A", READ, 101, 5, 1),
        Signal("B", READ, 106, 2, 1),
        Signal("C", READ, 108, 2, 1),
    ]
    assert split_range_into_halfs(signal_list, RegisterRange(READ, 100, 10)) == (
        RegisterRange(READ, 101, 5),
        RegisterRange(READ, 106, 4),
    )
