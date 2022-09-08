#!/usr/bin/env python3

import logging

import yaml

from custom_components.sungrow.core import deserialize, modbus, signals

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("pymodbus").setLevel(logging.WARNING)


async def main():
    await dump(modbus.Connection("192.168.13.79", 502, 1), "dump-master.yaml")
    await dump(modbus.Connection("192.168.13.80", 502, 2), "dump-slave.yaml")


def flatten_registers(raw_data: dict[modbus.Connection.RegisterRange, list[int]]):
    flat: dict[str, dict[int, int]] = {"read": {}, "hold": {}}
    for register_range, registers in raw_data.items():
        for addr in range(
            register_range.start, register_range.start + register_range.length
        ):
            flat[register_range.register_type][addr] = registers[
                addr - register_range.start
            ]
    return flat


async def dump(connection: modbus.Connection, filename: str) -> None:
    signal_definitions = signals.load_yaml()

    await connection.connect()
    raw_data = await connection.read_raw(signal_definitions.modbus_signal_list)
    await connection.disconnect()

    signal_raw_data = connection.map_raw_to_signals(
        raw_data, signal_definitions.modbus_signal_list
    )

    signal_data = deserialize.decode_signals(signal_definitions, signal_raw_data)

    with open(filename, "w") as dump_file:
        yaml.dump(
            {
                "registers": flatten_registers(raw_data),
                "signals": signal_data,
            },
            dump_file,
            default_flow_style=False,
            sort_keys=False,
        )
