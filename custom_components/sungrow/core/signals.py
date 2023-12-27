"""
Contains all the signals that can be read from the inverter,
and the code to decode them.
It does NOT know about modbus (except for "RegisterType").
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

from .modbus import RegisterType

logger = logging.getLogger(__name__)


def are_all_values_zero(my_dict, keys):
    """Return True if all values in the dictionary are zero or missing."""
    return all(my_dict.get(key, 0) == 0 for key in keys)


@dataclass
class ModbusSignalDefinition:
    name: str
    address: int
    level: int
    datatype: str
    register_type: RegisterType
    slave: str
    disabled: list[str]  # str instead of bool to allow comments
    accuracy: int | None = None
    mask: int | None = None
    datarange: dict[int, str] | None = None
    models: list[str] | None = None
    models_exclude: list[str] | None = None
    group: str | None = None
    unit: str | None = None

    @property
    def register_count(self):
        """Return the number of registers needed to read this signal"""

        if self.datatype in ["U16", "S16"]:
            return 1
        elif self.datatype in ["U32", "S32"]:
            return 2
        elif self.datatype.startswith("UTF-8"):
            # format: UTF-8[<length>]
            length = int(self.datatype[6:-1])

            # Check if length is even valid
            if not length > 0 or not length < 256:
                raise RuntimeError(
                    f"Invalid yaml for {self.name}: "
                    "expected UTF-8[<length>] with length being a number between "
                    "1 and 255, e.g. UTF-8[10]"
                )

            return length
        else:
            raise RuntimeError(
                f"Invalid yaml for {self.name}: "
                "unknown datatype (expected U16, S16, U32, S32 or UTF-8[<length>])"
            )

    @property
    def na_value(self):
        """Return the value that indicates that the signal is not available"""

        return {
            "U16": 0xFFFF,
            "S16": 0x7FFF,
            "U32": 0xFFFFFFFF,
            "S32": 0x7FFFFFFF,
        }.get(self.datatype)


class SignalDefinitions:
    def __init__(self, definitions: dict[str, ModbusSignalDefinition] | None = None):
        if definitions is None:
            self._definitions = {}
        else:
            self._definitions = definitions

    def get_signal_definitions_by_address(
        self, register_type: RegisterType, address: int, count: int = 1
    ):
        match: list[ModbusSignalDefinition] = []
        for signal in self._definitions.values():
            if (
                signal.register_type == register_type
                and signal.address >= address
                and signal.address < (address + count)
            ):
                match.append(signal)
        return match

    def get_signal_definitions_by_name(self, name: str):
        # Note: differentiating between read and hold registers is not needed here.
        # They do not overlap.
        return self._definitions.get(name)

    def get_groups(self):
        """Return a list of all groups"""
        groups: dict[str, dict[str, ModbusSignalDefinition]] = {}
        for signal in self._definitions.values():
            if signal.group:
                groups.setdefault(signal.group, {})[signal.name] = signal
        return groups


@dataclass
class RegisterRange:
    type: RegisterType
    start: int
    length: int


@dataclass
class SunGatherYamlContent:
    signals: SignalDefinitions
    ranges: list[RegisterRange]


def load_sungather_yaml() -> SunGatherYamlContent:
    pwd = Path(__file__).parent.absolute()
    with open(pwd / "registers-sungrow.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    registers: dict[str, ModbusSignalDefinition] = {}

    for register_type, registers_list in {
        "read": data["registers"][0]["read"],
        "hold": data["registers"][1]["hold"],
    }.items():
        for register in registers_list:
            assert isinstance(register, dict)

            # Datarange is a list of dicts with "response" and "value" keys.
            # Convert it to a dict with "response" as key and "value" as value.
            if datarange := register.get("datarange"):
                datarange = {
                    int(item["response"]): str(item["value"]) for item in datarange
                }

            signal = ModbusSignalDefinition(
                name=register["name"],
                register_type=RegisterType(register_type),
                address=register["address"],
                level=register["level"],
                datatype=register["datatype"],
                slave=register.get("unit", ""),
                accuracy=register.get("accuracy"),
                mask=register.get("mask"),
                datarange=datarange,
                models=register.get("models"),
                models_exclude=register.get("models_exclude"),
                group=register.get("group"),
                disabled=[],
                unit=register.get("unit"),
            )
            # Deduplicate signal names
            # todo: Mostly they are for different models, but not all.
            while signal.name in registers:
                logger.debug(
                    "Duplicate signal name: "
                    f"{registers[signal.name]} vs {signal}. Appending '_'"
                )
                signal.name += "_"
            registers[signal.name] = signal

    ranges: list[RegisterRange] = []
    for register_type, ranges_list in {
        "read": data["scan"][0]["read"],
        "hold": data["scan"][1]["hold"],
    }.items():
        for range in ranges_list:
            assert isinstance(range, dict)
            ranges.append(
                # The ranges are sending address based, while the signals are
                # communication address based. To avoid confusion, nothing except
                # modbus.py is using sending addresses.
                # So we need to add 1 to the start address here.
                RegisterRange(
                    type=RegisterType(register_type),
                    start=int(range["start"]) + 1,
                    length=int(range["range"]),
                )
            )

    return SunGatherYamlContent(SignalDefinitions(registers), ranges)


def _decode_int_signal(
    registers: list[int],
    signal: ModbusSignalDefinition,
):
    int_value = int(registers[0])

    if signal.datatype in ["U32", "S32"]:
        # Each register is 16 bit. Combine the next register to get 32 bit.
        int_value += registers[1] << 16

    if int_value == signal.na_value:
        int_value = 0
    elif signal.datatype == "S16" and int_value > 0x7FFF:
        int_value -= 0x10000
    elif signal.datatype == "S32" and int_value > 0x7FFFFFFF:
        int_value -= 0x100000000

    value: str | int | float
    # mask is used for boolean values only
    if signal.mask:
        value = int(int_value & signal.mask)

    # "datarange" is used to decode values like "1" to "ON" or "0" to "OFF"
    elif signal.datarange:
        # ToDo: better error handling.
        # Exception is not an option, as it would be nice to e.g. support
        # unknown inverters.
        value = signal.datarange.get(int_value, int_value)

    elif signal.accuracy:
        assert isinstance(int_value, int)
        value = float(round(int_value * float(signal.accuracy), 2))

    else:
        value = int_value

    return value


def _decode_utf8_signal(registers: list[int], signal: ModbusSignalDefinition):
    try:
        value = "".join(
            [chr(c >> 8) + chr(c & 0xFF) for c in registers[0 : signal.register_count]]
        ).strip("\x00")
    except IndexError as exc:
        raise RuntimeError(
            f"Invalid yaml for {signal.name}: "
            "UTF-8[<length>] doesn't fit into scan ranges "
            f"(address + {signal.register_count} >= {len(registers)})"
        ) from exc

    return value


def decode_signal(
    registers: list[int],
    registers_start_addr: int,
    signal: ModbusSignalDefinition,
):
    pos = signal.address - registers_start_addr

    if signal.datatype in ["U16", "S16", "U32", "S32"]:
        return _decode_int_signal(registers[pos:], signal)

    elif signal.datatype.startswith("UTF-8"):
        return _decode_utf8_signal(registers[pos:], signal)

    else:
        raise RuntimeError(
            f"Invalid yaml for {signal.name}: "
            "unknown datatype (expected U16, S16, U32, S32 or UTF-8[<length>])"
        )


def decode_registers(
    registers: list,
    register_type: RegisterType,
    modbus_config: SignalDefinitions,
    start_addr: int,
) -> dict[str, str | int | float]:
    assert registers

    decoded = {}

    for signal in modbus_config.get_signal_definitions_by_address(
        register_type, start_addr, len(registers)
    ):
        if not signal.disabled:
            value = decode_signal(registers, start_addr, signal)
            # ToDo: how to handle errors? (value = None)
            decoded[signal.name] = value

    return decoded
