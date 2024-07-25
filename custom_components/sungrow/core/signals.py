"""
Contains all the signals that can be read from the inverter,
and the code to decode them.
It does NOT know about modbus (except for "RegisterType").
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar, cast

import yaml

from custom_components.sungrow.core.inverter_types import Level
from custom_components.sungrow.core.modbus_types import RegisterRange

from .modbus_types import ModbusSignal, RegisterType

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
class SignalDefinition(ModbusSignal):
    unit_of_measurement: str | None
    disabled: list[str]  # list[str] instead of bool to allow comments
    group_supported_indicator: str | None  # Idea: use SignalDefinition instead of str
    only_if_group_supported: str | None  # Idea: use SignalDefinition instead of str
    accuracy: float | None
    mask: int | None
    decoded: dict[int, str] | None
    models: list[str] | None
    models_exclude: list[str] | None
    level: int | None
    base_datatype: str | None = None

    value_with_no_meaning: DatapointBaseValueType = None
    """
    In some cases (especially WiNet), not supported is not reported correctly.
    This is the value that is being returned, although the signal is not supported.
    """

    array_length: int | None = None
    """ Length of the array. None if not an array. """

    def __post_init__(self):
        # If yaml does not define a specific value, we assume 0.
        # When we query multiple registers, the inverter/WiNet will respond with 0,
        # if the signal is not supported.
        if self.value_with_no_meaning is None:
            self.value_with_no_meaning = 0

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
    def is_supported(self):
        return super().is_supported

    def update_supported(self, value: ModbusSignal.Supported):
        if value == ModbusSignal.Supported.YES and self.disabled:
            logger.warning(
                f"Signal {self.name} was disabled ({self.disabled}), "
                f"but has been received"
            )

        # temp workaround, as we commonly only check for disabled, not for unsupported.
        if value == ModbusSignal.Supported.NO:
            self.disabled.append("not supported by inverter")

        # TODO: if the signal is an indicator we can mark all other signals now..
        super().update_supported(value)

    def does_value_indicate_supported(self, value) -> bool:
        # ToDo: What about na_value?
        return value is not None and value != self.value_with_no_meaning

    # def is_value_unsupported(self, value) -> bool:
    #     return value is None

    def update_supported_state_based_on_value(
        self,
        value,
        was_queried_individually,
        all_signals: "SignalDefinitions",
    ):
        if value is None:
            if (
                self.is_supported != ModbusSignal.Supported.NO
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


class SignalDefinitions:
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


def load_yaml() -> SignalDefinitions:
    """
    This is specific to our yaml file format.
    For parsing other formats, see script_sync_yaml.py
    """
    pwd = Path(__file__).parent.absolute()
    with Path(pwd / "registers-sungrow.yaml").open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise TypeError("Invalid yaml: expected a dictionary as root element")

    all_signals: dict[str, SignalDefinition] = {}

    for register_type in [RegisterType.READ, RegisterType.HOLD]:
        for entry in data[str(register_type)]:
            assert isinstance(entry, dict)

            def get(type_, key: str):
                if key in entry:
                    return type_(entry[key])
                return None

            T = TypeVar("T")

            def get_list(key: str, type_: type[T]) -> list[T] | None:
                val = entry.get(key)
                if val:
                    if isinstance(val, str):
                        return [type_(val)]  # type: ignore
                    else:
                        return [type_(v) for v in val]  # type: ignore
                return None

            array_length: None | int = _parse_array_length(entry["data_type"])
            base_datatype = _parse_base_datatype(entry["data_type"])

            if base_datatype in ["U16", "S16", "UTF-8"]:
                base_datatype_length = 1
            elif base_datatype in ["U32", "S32"]:
                base_datatype_length = 2
            else:
                raise RuntimeError(
                    "Unknown datatype (expected U16, S16, U32, S32 or UTF-8, "
                    f"not {base_datatype})"
                )

            if array_length is None:
                array_length = 1

            signal = SignalDefinition(
                name=entry["name"],
                unit_of_measurement=entry.get("unit_of_measurement"),
                accuracy=get(float, "accuracy"),
                mask=entry.get("mask"),
                decoded=entry.get("decoded"),
                models=entry.get("models"),
                models_exclude=entry.get("models_exclude"),
                group_supported_indicator=entry.get("group_supported_indicator"),
                only_if_group_supported=entry.get("only_if_group_supported"),
                disabled=[],
                level=entry.get("level"),
                array_length=array_length,
                base_datatype=base_datatype,
                registers=RegisterRange(
                    register_type=RegisterType(register_type),
                    start=entry["address"],
                    length=array_length * base_datatype_length,
                ),
                value_with_no_meaning=entry.get("unsupported_value"),
            )

            if signal.decoded:
                assert isinstance(signal.decoded, dict), f"{signal.decoded}"
                assert all(isinstance(k, int) for k in signal.decoded)
                assert all(isinstance(v, str) for v in signal.decoded.values())

            # Deduplicate signal names
            # todo: Mostly they are for different models, but not all.
            while signal.name in all_signals:
                # logger.debug(
                #     "Duplicate signal name: "
                #     f"{registers[signal.name]} vs {signal}. Appending '_'"
                # )
                signal.name += "_"
            all_signals[signal.name] = signal

    return SignalDefinitions(all_signals)
