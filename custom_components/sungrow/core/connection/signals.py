"""
Contains all the signals that can be read from the inverter,
and the code to decode them.
It does NOT know about modbus (except for "RegisterType").
"""

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from .modbus_types import RegisterRange

logger = logging.getLogger(__name__)


def is_zero(v):
    if v is None:
        return True

    if isinstance(v, list):
        return not any(v)
    elif isinstance(v, dict):
        return not any(v.values())
    else:
        return v == 0


DatapointBaseValueType = bool | int | float | str | None
DatapointValueType = DatapointBaseValueType | list[DatapointBaseValueType]


class Supported(StrEnum):
    NEVER_ATTEMPTED = "never_attempted"  # Initial state

    # Needs to be queried individually for a potentially better classification
    UNKNOWN_FROM_MULTI_SIGNAL_QUERY = "returns_zero"

    # Was already queried individually, still no better classification.
    # It will probably remain unknown forever.
    CONFIRMED_UNKNOWN = "confirmed_unknown"

    YES = "yes"
    NO = "no"


def get_new_supported_state_based_on_value(
    sigdef: "SignalDefinition",
    value: DatapointBaseValueType,
    was_queried_individually: bool,
):
    def does_value_indicate_supported(
        value: DatapointBaseValueType, sigdef: "SignalDefinition"
    ) -> bool:
        # ToDo: What about na_value?
        return value is not None and value != sigdef.value_with_no_meaning

    if value is None:
        return Supported.NO

    if does_value_indicate_supported(value, sigdef):
        return Supported.YES

    # Unknown, but which one?
    if was_queried_individually:
        return Supported.CONFIRMED_UNKNOWN
    else:
        return Supported.UNKNOWN_FROM_MULTI_SIGNAL_QUERY


@dataclass
class SignalDefinition:
    name: str
    registers: RegisterRange
    accuracy: float | None
    mask: int | None
    base_datatype: str | None = None

    value_with_no_meaning: DatapointBaseValueType = None
    """
    In some cases (especially WiNet), not supported is not reported correctly.
    This is the value that is being returned, although the signal is not supported.
    """

    array_length: int | None = None
    """ Length of the array. None if not an array. """

    def contains(self, registers: RegisterRange) -> bool:
        return self.registers.contains(registers)

    def contained_in(self, registers: RegisterRange) -> bool:
        return registers.contains(self.registers)

    @property
    def element_length(self):
        if self.array_length is None:
            return self.registers.length
        else:
            element_length = self.registers.length / self.array_length
            if element_length != int(element_length):
                raise RuntimeError(
                    f"Invalid yaml for {self.name}: "
                    "array length must be a multiple of the register length"
                )
            return int(element_length)

    @property
    def na_value(self):
        """
        Return the value that indicates that the signal is not available.
        TODO: does sungrow ever respond with any of these?
        """
        assert self.base_datatype

        return {
            "U16": 0xFFFF,
            "S16": 0x7FFF,
            "U32": 0xFFFFFFFF,
            "S32": 0x7FFFFFFF,
        }.get(self.base_datatype)


class SignalDefinitions(Mapping[str, SignalDefinition]):
    def __init__(self, definitions: dict[str, SignalDefinition]):
        self._definitions = definitions

    def as_dict(self):
        return self._definitions

    def to_list(self) -> list[SignalDefinition]:
        return list(self._definitions.values())

    def get_all_signals_contained_in_registers(self, registers: RegisterRange):
        return [
            signal
            for signal in self._definitions.values()
            if signal.contained_in(registers)
        ]

    def get_signal_definition_by_name(self, name: str):
        return self._definitions[name]

    def get_signal_definitions_by_name(self, names: list[str]):
        return [self._definitions[name] for name in names]
