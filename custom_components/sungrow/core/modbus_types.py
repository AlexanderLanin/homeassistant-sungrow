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

    def __str__(self):
        return f"Range({self.register_type}, {self.start}-{self.end-1})"


@dataclass
class Signal:
    name: str
    # TODO: use RegisterRange? However we don't know the length at construction time.
    register_type: RegisterType
    address: int
    element_length: int
    array_length: int

    @property
    def length(self):
        return self.element_length * self.array_length

    @property
    def end(self):
        """The address after the last address of the signal."""
        return self.address + self.length


# In case the register is not supported, the value is None
# e.g. {0: 123, 1: 456: 2: None}
RawData = dict[int, int | None]

# In case the signal is not supported, the value is None
# e.g. {"ac_power": [123, 456], "ac_current": None}
MappedData = dict[str, list[int] | None]
