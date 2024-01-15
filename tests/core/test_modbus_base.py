from custom_components.sungrow.core.modbus_base import split_range_into_halfs
from custom_components.sungrow.core.modbus_types import (
    RegisterRange,
    RegisterType,
)

READ = RegisterType.READ
HOLD = RegisterType.HOLD


def test_split_range():
    assert split_range_into_halfs(RegisterRange(READ, 100, 10)) == (
        RegisterRange(READ, 100, 5),
        RegisterRange(READ, 105, 5),
    )

    assert split_range_into_halfs(RegisterRange(HOLD, 100, 11)) == (
        RegisterRange(HOLD, 100, 5),
        RegisterRange(HOLD, 105, 6),
    )
