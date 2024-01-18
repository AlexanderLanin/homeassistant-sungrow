#!/usr/bin/env python3

import logging

import fix_path  # noqa: F401
import yaml

from custom_components.sungrow.core import deserialize, inverter, modbus_py, signals

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("pymodbus").setLevel(logging.WARNING)


async def main():
    # await dump("192.168.13.58", 502, 1, "dump_master_winets.yaml")
    # await dump("192.168.13.74", 502, 1, "dump_slave_winets.yaml")
    # await dump(modbus.Connection("192.168.13.79", 502, 1), "dump_master.yaml")
    await dump("192.168.13.79", 502, 200, "dump_battery.yaml")
    # await dump("192.168.13.80", 502, 2, "dump_slave.yaml")


async def dump(host: str, port: int, slave: int, filename: str) -> None:
    signal_definitions = signals.load_yaml()

    is_winet = await inverter.is_WiNet(host)
    if is_winet:
        logging.info("Detected WiNet inverter, disabling necessary signals")
        # signal_definitions.disable_winet_signals()
    else:
        logging.info("Detected non-WiNet inverter, querying all signals")

    async with modbus_py.PymodbusConnection(host, port, slave) as connection:
        raw_data = await connection.read_raw(
            signal_definitions.enabled_modbus_signals()
        )

    signal_raw_data = connection.map_raw_to_signals(
        raw_data, signal_definitions.enabled_modbus_signals()
    )

    signal_data = deserialize.decode_signals(signal_definitions, signal_raw_data)

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
