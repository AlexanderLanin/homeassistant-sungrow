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
