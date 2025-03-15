"""
Contains all the signals that can be read from the inverter,
and the code to decode them.
It does NOT know about modbus (except for "RegisterType").
"""

import logging
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TypeVar, cast
from collections.abc import Mapping

import yaml

from custom_components.sungrow.core.inverter_types import Level

from .modbus_types import RegisterRange, RegisterType

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


@dataclass
class SignalValue:
    defindition: "SignalDefinition"
    value: dict[int, str] | None
    supported: "Supported"

    def does_value_indicate_supported(self, value) -> bool:
        # ToDo: What about na_value?
        return value is not None and value != self.defindition.value_with_no_meaning

    class Supported(StrEnum):
        NEVER_ATTEMPTED = "never_attempted"  # Initial state

        # Needs to be queried individually for a potentially better classification
        UNKNOWN_FROM_MULTI_SIGNAL_QUERY = "returns_zero"

        # Was already queried individually, still no better classification.
        # It will probably remain unknown forever.
        CONFIRMED_UNKNOWN = "confirmed_unknown"

        YES = "yes"
        NO = "no"

    def update_supported_state_based_on_value(
        self,
        value,
        was_queried_individually,
        all_signals: "SignalDefinitions",
    ):
        logger.debug(
            f"Updating supported state for {self.name}: "
            f"{value} (was_queried_individually={was_queried_individually})"
        )
        if value is None:
            if (
                self.supported != ModbusSignal.Supported.NO
                and self.group_supported_indicator
            ):
                # New information! This group is not supported!
                all_signals.disable_group(self.group_supported_indicator)

            self.update_supported(ModbusSignal.Supported.NO)

        elif self.does_value_indicate_supported(value):
            self.update_supported(ModbusSignal.Supported.YES)
        else:
            if was_queried_individually:
                self.update_supported(ModbusSignal.Supported.CONFIRMED_UNKNOWN)
            else:
                self.update_supported(
                    ModbusSignal.Supported.UNKNOWN_FROM_MULTI_SIGNAL_QUERY
                )
        logger.debug(f"Signal {self.name} is now {self.supported}")


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
        """Return the value that indicates that the signal is not available"""
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

    def all_signals(self) -> list[SignalDefinition]:
        return list(self._definitions.values())

    def enabled_signals(self):
        return [signal for signal in self._definitions.values() if not signal.disabled]

    def enabled_modbus_signals(self):
        return cast(list[ModbusSignal], self.enabled_signals())

    def all_modbus_signals(self):
        return cast(list[ModbusSignal], list(self._definitions.values()))

    def get_all_signals_contained_in_registers(self, registers: RegisterRange):
        return [
            signal
            for signal in self._definitions.values()
            if signal.contained_in(registers)
        ]

    def get_active_signals_for_level(self, level: Level):
        return [
            signal
            for signal in self._definitions.values()
            if signal.level is not None
            and signal.level <= level.value
            and not signal.disabled
        ]

    def get_signal_definition_by_name(self, name: str):
        # Note: differentiating between read and hold registers is not needed here.
        # Names do not overlap.
        return self._definitions[name]

    def get_signal_definitions_by_name(self, names: list[str]):
        return [self._definitions[name] for name in names]

    def get_active_groups(self):
        return {
            signal.group_supported_indicator: not signal.disabled
            for signal in self._definitions.values()
            if signal.group_supported_indicator
        }

    def get_group_indiators(self):
        """Return a list of all group indicators"""
        return {
            signal.group_supported_indicator: signal
            for signal in self._definitions.values()
            if signal.group_supported_indicator
        }

    def get_group_indicator(self, group: str):
        """
        Return a signal that indicates if a group is supported or not.
        This is useful for groups that are not supported by all inverters.
        """
        return self.get_group_indiators().get(group)

    def get_group_member(self, group: str):
        """
        Return a signal that indicates if a group is supported or not.
        This is useful for groups that are not supported by all inverters.
        """
        return {
            signal.name: signal
            for signal in self._definitions.values()
            if signal.only_if_group_supported == group
        }

    def disable_group(self, group: str):
        indicator_signal = self.get_group_indicator(group)
        assert indicator_signal
        indicator_signal.disabled.append(f"Group {group} is disabled by this signal")

        for signal in self.get_group_member(group).values():
            signal.disabled.append(
                f"Group {group} is disabled by {indicator_signal.name}"
            )

    # ToDo: move to inverter.py. This is clearly business logic.
    def mark_signals_below_level_as_disabled(self, level: Level):
        for signal in self._definitions.values():
            if signal.level and signal.level > level.value:
                signal.disabled.append(
                    f"signal {signal.level} not enabled on level {level}"
                )


def _parse_base_datatype(data_type: str):
    """Return the datatype without length"""

    parts = data_type.split("[")
    return parts[0]


def _parse_array_length(data_type: str):
    """Return the length of the array"""

    parts = data_type.split("[")
    if len(parts) == 1:
        # Not an array
        return None

    length = int(parts[1][:-1])
    if length <= 0 or length >= 255:
        raise RuntimeError(
            "Invalid yaml: "
            "expected DATATYPE[<length>] with length being a number between "
            f"1 and 255, e.g. UTF-8[10], instead of {data_type}"
        )

    return length
