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


@dataclass
class SignalDefinition:
    name: str
    registers: RegisterRange

    # unit_of_measurement: str | None
    # disabled: list[str]  # list[str] instead of bool to allow comments
    group_supported_indicator: str | None  # Idea: use SignalDefinition instead of str
    only_if_group_supported: str | None  # Idea: use SignalDefinition instead of str
    accuracy: float | None
    mask: int | None
    decoded: dict[int, str] | None
    models: list[str] | None
    models_exclude: list[str] | None
    level: int | None
    base_datatype: str | None = None

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
