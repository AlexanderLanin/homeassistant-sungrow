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
class ModbusSignal:
    class Supported(StrEnum):
        NEVER_ATTEMPTED = "never_attempted"  # Initial state

        # Needs to be queried individually for a potentially better classification
        UNKNOWN_FROM_MULTI_SIGNAL_QUERY = "returns_zero"

        # Was queried individually, still no better classification. It will remain unknown.
        # No need to query individually again.
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

    def query_individually(self):
        return self._is_supported == self.Supported.UNKNOWN_FROM_MULTI_SIGNAL_QUERY

    def update_supported(self, value: Supported):
        assert value != self.Supported.NEVER_ATTEMPTED

        # Quick exit, if there is no change.
        if value == self._is_supported:
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
        old_rank = ranks[self._is_supported]
        new_rank = ranks[value]

        if new_rank >= old_rank:
            if value in (self.Supported.YES, self.Supported.NO):
                if self._is_supported in (self.Supported.YES, self.Supported.NO):
                    logger.warning(
                        f"Signal {self.name} changed support status "
                        f"from {self._is_supported} to {value}."
                    )
                else:
                    s = "supported" if value == self.Supported.YES else "not supported"
                    logger.debug(f"Signal {self.name} is {s}.")
            self._is_supported = value


# In case the register is not supported, the value is None
# e.g. {0: 123, 1: 456: 2: None}
RawData = dict[int, int | None]

# In case the signal is not supported, the value is None
# e.g. {"ac_power": [123, 456], "ac_current": None}
MappedData = dict[str, list[int] | None]
