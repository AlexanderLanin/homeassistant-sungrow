"""
The abstraction level is chosen at the lowest point which does not need to know how
signals are queried. This is where all signals are read() at once, so this class
can perform a clever optimization to reduce the number of queries.
"""

from dataclasses import dataclass
from enum import StrEnum


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
        return f"Range({str(self.register_type).upper()}, {self.start}-{self.end-1})"

    def contains(self, other: "RegisterRange") -> bool:
        return (
            self.register_type == other.register_type
            and other.start >= self.start
            and other.end <= self.end
        )


@dataclass
class Signal:
    name: str
    registers: RegisterRange

    # length_of_array: int | None
    # """None if not an array"""

    def contains(self, registers: RegisterRange) -> bool:
        return self.registers.contains(registers)

    def contained_in(self, registers: RegisterRange) -> bool:
        return registers.contains(self.registers)


# In case the register is not supported, the value is None
# e.g. {0: 123, 1: 456: 2: None}
RawData = dict[int, int | None]

# In case the signal is not supported, the value is None
# e.g. {"ac_power": [123, 456], "ac_current": None}
MappedData = dict[str, list[int] | None]
