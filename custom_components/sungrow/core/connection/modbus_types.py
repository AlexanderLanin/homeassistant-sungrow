import logging
from dataclasses import dataclass
from enum import StrEnum

from .signals import SignalDefinition

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


def query_individually(self: SignalDefinition):
    return self._supported == self.Supported.UNKNOWN_FROM_MULTI_SIGNAL_QUERY

def update_supported(self: SignalDefinition, value: SignalDefinition.Supported):
    assert value != self.Supported.NEVER_ATTEMPTED

    # Quick exit, if there is no change.
    if value == self._supported:
        return

    # Is it an "update"?
    # E.g. when the signal was set to YES, but is now UNKNOWN, we want to keep the YES
    ranks = {
        self.Supported.NEVER_ATTEMPTED: 0,
        self.Supported.UNKNOWN_FROM_MULTI_SIGNAL_QUERY: 1,
        self.Supported.CONFIRMED_UNKNOWN: 2,
        self.Supported.YES: 3,
        self.Supported.NO: 3,
    }
    old_rank = ranks[self._supported]
    new_rank = ranks[value]

    if new_rank >= old_rank:
        if value in (self.Supported.YES, self.Supported.NO):
            if self._supported in (self.Supported.YES, self.Supported.NO):
                logger.warning(
                    f"Signal {self.name} changed support status "
                    f"from {self._supported} to {value}."
                )
            else:
                s = "supported" if value == self.Supported.YES else "not supported"
                logger.debug(f"Signal {self.name} is {s}.")
        self._supported = value


# In case the register is not supported, the value is None
# e.g. {0: 123, 1: 456: 2: None}
RawData = dict[int, int | None]

# In case the signal is not supported, the value is None
# e.g. {"ac_power": [123, 456], "ac_current": None}
MappedData = dict[str, list[int] | None]
