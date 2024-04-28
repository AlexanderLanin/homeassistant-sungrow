"""
Contains all the signals that can be read from the inverter,
and the code to decode them.
It does NOT know about modbus (except for "RegisterType").
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml
from aiohttp import DefaultResolver

from custom_components.sungrow.core.modbus_types import RegisterRange

from .modbus_base import Signal  # ToDo: signal imports Signal sounds wrong :D
from .modbus_py import RegisterType

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


DatapointValueTypeBase = bool | int | float | str | None
DatapointValueType = DatapointValueTypeBase | dict[int, DatapointValueTypeBase] | None


@dataclass
class SungrowSignalDefinition(Signal):
    unit_of_measurement: str | None
    disabled: list[str]  # str instead of bool to allow comments
    group: list[str] | None
    accuracy: float | None
    mask: int | None
    decoded: dict[int, str] | None
    models: list[str] | None
    models_exclude: list[str] | None
    level: int | None
    base_datatype: str | None = None

    potentially_unsupported_value: DatapointValueTypeBase = None
    """
    In some cases (especially WiNet), not supported is not reported correctly.
    This is the value that is being returned, although the signal is not supported.
    """

    array_length: int | None = None
    """ Length of the array. None if not an array. """

    _is_supported: bool | None = None
    """
    Yes, No, Unknown. Careful how you compare this!
    Note: this is unrelated to 'disabled'. This is what the inverter actually supports,
    while 'disabled' is what we want to disable (what we think the inverter supports).
    TODO: rename disabled to is_supported_guess + disabled_reasons?
    """

    def __post_init__(self):
        # If yaml does not define a specific value, we assume 0.
        # When we query multiple registers, the inverter/WiNet will respond with 0,
        # if the signal is not supported.
        if self.potentially_unsupported_value is None:
            self.potentially_unsupported_value = 0

    @property
    def is_supported(self):
        return self._is_supported

    @is_supported.setter
    def is_supported(self, value: bool):
        if self._is_supported is None:
            if value and self.disabled:
                logger.warning(
                    f"Signal {self.name} was disabled ({self.disabled}), "
                    f"but has been received"
                )
            if not value:
                logger.info(f"Signal {self.name} is not supported by inverter")
                self.disabled.append("not supported by inverter")
            self._is_supported = value
        else:
            assert self._is_supported == value

    def is_value_supported(self, value) -> bool:
        return value is not None and value != self.potentially_unsupported_value

    def is_value_unsupported(self, value) -> bool:
        return value is None

    def determine_and_mark_supported(self, value):
        if self.is_value_supported(value):
            self.is_supported = True
        elif self.is_value_unsupported(value):
            self.is_supported = False

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
    def __init__(self, definitions: dict[str, SungrowSignalDefinition]):
        self._definitions = definitions

    def all_signals(self) -> list[SungrowSignalDefinition]:
        return list(self._definitions.values())

    def enabled_signals(self):
        filtered: list[SungrowSignalDefinition] = []
        for signal in self._definitions.values():
            if not signal.disabled:
                filtered.append(signal)
        return filtered

    def enabled_modbus_signals(self):
        return cast(list[Signal], self.enabled_signals())

    def all_modbus_signals(self):
        return cast(list[Signal], list(self._definitions.values()))

    def get_all_signals_contained_in_registers(self, registers: RegisterRange):
        return [
            signal
            for signal in self._definitions.values()
            if signal.contained_in(registers)
        ]

    def get_active_signals_for_level(self, level: int):
        return [
            signal
            for signal in self._definitions.values()
            if signal.level is not None
            and signal.level <= level
            and not signal.disabled
        ]

    def get_signal_definition_by_name(self, name: str):
        # Note: differentiating between read and hold registers is not needed here.
        # Names do not overlap.
        return self._definitions[name]

    def get_signal_definitions_by_name(self, names: list[str]):
        return [self._definitions[name] for name in names]

    def disable_winet_signals(self):
        """
        Including certain signals in the WiNet query, will ruin the entire query,
        so we disable them.
        """

        for signal in self._definitions.values():
            if signal.models_exclude and "WiNet" in signal.models_exclude:
                signal.disabled.append("disabled for WiNet")

    def get_signals_for_group(self, group: str):
        signals: dict[str, SungrowSignalDefinition] = {}
        for signal in self._definitions.values():
            if signal.group and group in signal.group:
                signals[signal.name] = signal
        return signals

    def get_groups(self):
        """Return a list of all groups"""
        groups: dict[str, dict[str, SungrowSignalDefinition]] = {}
        for signal in self._definitions.values():
            if signal.group:
                for group in signal.group:
                    groups.setdefault(group, {})[signal.name] = signal
        return groups

    # ToDo: move to inverter.py. This is clearly business logic.
    def mark_signals_disabled_based_on_groups(self, data):
        assert data, "data must have been pulled from the inverter first!"
        """Note: this returns extra_data to be included!"""

        logger.debug(f"Data: {data}")

        extra_data = {}

        # now filter groups where all signals are inactive
        for group, group_signals in self.get_groups().items():
            has_enabled_signal = False
            all_zero = True
            for signal in group_signals.values():
                v = data.get(signal.name)
                logger.debug(f"Group {group}: Signal {signal.name} = {v}")
                if not signal.disabled:
                    has_enabled_signal = True
                    if not is_zero(v):
                        logger.debug(
                            f"Group {group}: Signal {signal.name} is not zero: {v}"
                        )
                        all_zero = False

            if not has_enabled_signal:
                logger.debug(
                    f"Group {group}: not supported by inverter "
                    "(all signals in group are already disabled)"
                )
                # extra_data[group] = False
            elif all_zero:
                logger.debug(f"Group {group}: all signals are zero")
                for signal in group_signals.values():
                    signal.disabled.append(f"all (enabled) signals in {group} are zero")
                # extra_data[group] = False
            else:
                extra_data[group] = True

        return extra_data

    # ToDo: move to inverter.py. This is clearly business logic.
    def mark_signals_below_level_as_disabled(self, level):
        for signal in self._definitions.values():
            if signal.level and signal.level > level:
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

    all_signals: dict[str, SungrowSignalDefinition] = {}

    for register_type in [RegisterType.READ, RegisterType.HOLD]:
        for entry in data[str(register_type)]:
            assert isinstance(entry, dict)

            def get(type_, key: str):
                if key in entry:
                    return type_(entry[key])
                return None

            group = entry.get("group", None)
            if group is not None and isinstance(group, str):
                group = [group]

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

            signal = SungrowSignalDefinition(
                name=entry["name"],
                unit_of_measurement=entry.get("unit_of_measurement"),
                accuracy=get(float, "accuracy"),
                mask=entry.get("mask"),
                decoded=entry.get("decoded"),
                models=entry.get("models"),
                models_exclude=entry.get("models_exclude"),
                group=group,
                disabled=[],
                level=entry.get("level"),
                array_length=array_length,
                base_datatype=base_datatype,
                registers=RegisterRange(
                    register_type=RegisterType(register_type),
                    start=entry["address"],
                    length=array_length * base_datatype_length,
                ),
                potentially_unsupported_value=entry.get("unsupported_value"),
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
