"""
Contains all the signals that can be read from the inverter,
and the code to decode them.
It does NOT know about modbus (except for "RegisterType").
"""

from collections import defaultdict
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

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

class SupportedState:
    def __init__(self, supported: Supported):
        self._signals: dict["SignalDefinition", Supported] = {}

    def __setitem__(self, signal: "SignalDefinition", support: Supported):
        self._signals[signal] = support

    def __getitem__(self, signal: "SignalDefinition") -> Supported:
        return self._signals.get(signal, Supported.NEVER_ATTEMPTED)

class RegisterType(StrEnum):
    READ = "read"
    HOLD = "hold"


@dataclass(frozen=True)
class RegisterRange:
    register_type: RegisterType
    start: int
    length: int

    @property
    def end(self):
        """The address after the last address of the range."""
        return self.start + self.length

    def __repr__(self):
        return f"Range({str(self.register_type).upper()}, {self.start}-{self.end - 1})"

    def contains(self, other: "RegisterRange") -> bool:
        return (
            self.register_type == other.register_type
            and other.start >= self.start
            and other.end <= self.end
        )


def get_supported_state_based_on_value(
    sigdef: "SignalDefinition",
    value: DatapointBaseValueType,
    was_queried_individually: bool,
):
    if value is None:
        return Supported.NO

    if value != sigdef.value_with_no_meaning:
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
    base_datatype: str  # string????

    scale: float | None
    """
    scale resulting integer by this number before returning.
    """

    decoding_table: dict[int, DatapointBaseValueType] | None = None
    """
    A table that maps raw register values to decoded values.
    The keys are the register values interpreted as an int.
    The values are the decoded values.
    """

    bitmask: int | None = None
    """
    A mask to apply to the raw register value before decoding.
    Contrary to decoding_table the need for a mask will lead to diffent signals,
    while a decoding_table is just a mapping of values.
    """

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
