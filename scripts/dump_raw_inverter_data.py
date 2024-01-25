#!/usr/bin/env python3

import logging

import yaml

if __package__ is None:
    # Script was executed from the command line
    import fix_path  # type: ignore  # noqa: F401

from custom_components.sungrow.core import deserialize, inverter, modbus_base, modbus_py

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("pymodbus").setLevel(logging.WARNING)


async def main():
    # await dump("192.168.13.58", 502, 1, "dump_master_winets.yaml")
    # await dump("192.168.13.74", 502, 1, "dump_slave_winets.yaml")
    # await dump(modbus.Connection("192.168.13.79", 502, 1), "dump_master.yaml")
    await dump("192.168.13.79", 502, 200, "dump_battery.yaml")
    # await dump("192.168.13.80", 502, 2, "dump_slave.yaml")


async def dump(host: str, port: int, slave: int, filename: str) -> None:
    async with await inverter.connect_and_get_basic_data(
        host, port, slave, "pymodbus"
    ) as ic:
        raw_data = await ic.connection.read_raw(
            ic.signal_definitions.enabled_modbus_signals()
        )

    signal_raw_data = modbus_base.map_raw_to_signals(
        raw_data, ic.signal_definitions.enabled_modbus_signals()
    )

    signal_data = deserialize.decode_signals(ic.signal_definitions, signal_raw_data)

    with open(filename, "w") as dump_file:
        yaml.dump(
            {
                # Remap the keys so they come out readable.
                "registers": {
                    "read": raw_data[modbus_py.RegisterType.READ],
                    "hold": raw_data[modbus_py.RegisterType.HOLD],
                },
                "signals": signal_data,
            },
            dump_file,
            default_flow_style=False,
            sort_keys=False,
        )
