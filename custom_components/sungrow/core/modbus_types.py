"""
The abstraction level is chosen at the lowest point which does not need to know how
signals are queried. This is where all signals are read() at once, so this class
can perform a clever optimization to reduce the number of queries.
"""

import logging
from dataclasses import dataclass
from enum import StrEnum

logger = logging.getLogger(__name__)


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
    class Supported(StrEnum):
        NEVER_ATTEMPTED = "never_attempted"
        UNKNOWN = "returns_zero"
        CONFIRMED_UNKNOWN = "confirmed_unknown"
        YES = "yes"
        NO = "no"

    name: str
    registers: RegisterRange
    _is_supported = Supported.NEVER_ATTEMPTED

    def contains(self, registers: RegisterRange) -> bool:
        return self.registers.contains(registers)

    def contained_in(self, registers: RegisterRange) -> bool:
        return registers.contains(self.registers)

    @property
    def is_supported(self) -> Supported:
        return self._is_supported

    def set_supported(self, value: Supported):
        assert value != self.Supported.NEVER_ATTEMPTED

        # is_supported is a state machine with 5 states, where the transitions are:
        # - start: NEVER_ATTEMPTED
        # - NEVER_ATTEMPTED/UNKNOWN/CONFIRMED_UNKNOWN -> YES/NO
        # - NEVER_ATTEMPTED -> UNKNOWN
        # - UNKNOWN -> CONFIRMED_UNKNOWN
        # - YES/NO -> NO/YES (warning log message)
        # - CONFIRMED -> NO (warning log message)

        # Quick exit, if there is no change.
        # Simplifies the state machine.
        if value == self._is_supported:
            return

        if value in (self.Supported.YES, self.Supported.NO):
            if self._is_supported in (
                self.Supported.NEVER_ATTEMPTED,
                self.Supported.UNKNOWN,
            ):
                # - NEVER_ATTEMPTED/UNKNOWN -> YES/NO
                if value == self.Supported.YES:
                    logger.debug(f"Signal {self.name} is supported.")
                elif value == self.Supported.NO:
                    logger.debug(f"Signal {self.name} is not supported.")
            else:
                # - YES/NO -> NO/YES
                logger.warning(
                    f"Signal {self.name} changed support status "
                    f"from {self._is_supported} to {value}."
                )

        # NEVER_ATTEMPTED -> *
        # UNKNOWN/YES/NO -> NO/YES
        if self._is_supported == self.Supported.NEVER_ATTEMPTED or value in (
            self.Supported.YES,
            self.Supported.NO,
        ):
            self._is_supported = value


# In case the register is not supported, the value is None
# e.g. {0: 123, 1: 456: 2: None}
RawData = dict[int, int | None]

# In case the signal is not supported, the value is None
# e.g. {"ac_power": [123, 456], "ac_current": None}
MappedData = dict[str, list[int] | None]
