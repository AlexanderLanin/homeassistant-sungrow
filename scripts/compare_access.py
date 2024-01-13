#!/usr/bin/env python3

"""
This script will query an inverter via:
* modbus
* WiNet modbus
* via WiNet http
and compare the results.
"""

import asyncio
import logging

import fix_path  # type: ignore  # noqa: F401
import yaml

from custom_components.sungrow.core import (
    deserialize,
    inverter,
    modbus_base,
    modbus_http,
    modbus_py,
    signals,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def collect_data_via_py_modbus(
    signal_definitions: signals.SignalDefinitions, host: str, slave: int
) -> dict[str, signals.DatapointValueType]:
    logger.info(f"{host}/{slave}/pymodbus: Attempting to connect...")
    try:
        async with modbus_py.PymodbusConnection(
            host, port=502, slave=slave
        ) as connection:
            logger.info(f"{host}/{slave}/pymodbus: Connected")

            if await inverter.is_WiNet(host):
                logger.info(f"{host}/{slave}/pymodbus: WiNet detected")
                signal_raw_data = await connection.read(
                    signal_definitions.enabled_modbus_signals()
                )
                mode = "WiNet pymodbus"
            else:
                logger.info(
                    f"{host}/{slave}/pymodbus: WiNet not detected; direct connection"
                )
                signal_raw_data = await connection.read(
                    signal_definitions.all_modbus_signals()
                )
                mode = "direct pymodbus"
        logger.info(
            f"{host}/{slave}/pymodbus: Data received for {len(signal_raw_data)} signals"
        )

        data = deserialize.decode_signals(signal_definitions, signal_raw_data)
        data["mode"] = mode
        return data
    except modbus_base.CannotConnectError:
        logger.info(f"{host}/{slave}/pymodbus: Failed to connect")
        return {}
    except modbus_base.ModbusError:
        logger.warning(f"{host}/{slave}/pymodbus: Failed to connect")
        return {"mode": "pymodbus", "serial_number": "ERROR"}


async def collect_data_via_winet_http(
    signal_definitions: signals.SignalDefinitions, host: str
) -> dict[str, signals.DatapointValueType]:
    logger.info(f"{host}/winet_http: Attempting to connect...")
    try:
        # ToDo: we basically connect two times to WiNet http! FIXME
        async with modbus_http.HttpConnection(host) as connection:
            logger.info(f"{host}/winet_http: Connected")
            signal_raw_data = await connection.read(
                signal_definitions.all_modbus_signals()
            )
        logger.info(
            f"{host}/winet_http: Data received for {len(signal_raw_data)} signals"
        )

        data = deserialize.decode_signals(signal_definitions, signal_raw_data)
        data["mode"] = "WiNet http"
        return data
    except modbus_base.CannotConnectError:
        logger.info(f"{host}/winet_http: Failed to connect")
        return {}
    except modbus_base.ModbusError:
        logger.warning(f"{host}/winet_http: Error during query")
        return {"mode": "WiNet http", "serial_number": "ERROR"}


async def collect_data(
    signal_definitions, hosts: list[str]
) -> list[dict[str, signals.DatapointValueType]]:
    tasks = []
    for host in hosts:
        slave = 1  # in WiNet modbus, the slave is always 1
        if "/" in host:
            host, slave_str = host.split("/")
            slave = int(slave_str)

        tasks.append(collect_data_via_py_modbus(signal_definitions, host, slave))
        tasks.append(collect_data_via_winet_http(signal_definitions, host))

    # ToDo: switch to gather for parallel execution
    data = []
    for task in tasks:
        data.append(await task)
    return data
    # return await asyncio.gather(*tasks)


def split_data_by_inverter(data: list[dict[str, signals.DatapointValueType]]):
    """
    In: [{"serial_number": "123", "a": 1}, {"serial_number": "123", "b": 2}]
    Out: {"123": [{"a": 1}, {"b": 2}]}

    serial_number becomes the key.
    The value is a list of dicts, where each dict contains the data for a single signal.
    """

    r: dict[str, list[dict[str, signals.DatapointValueType]]] = {}
    for d in data:
        if not d:
            continue
        sn = d["serial_number"]
        assert isinstance(sn, str)
        if sn not in r:
            r[sn] = []
        r[sn].append(d)
    return r


def transpose_data_by_signal(
    inverter_data: list[dict[str, signals.DatapointValueType]],
):
    """
    inverter_data is a list of datapoints,
    where each list item is one connection method to the inverter.

    In: {"123": [{"a": 1}, {"b": 2}]}
    Out: {"a": [1], "b": [2]}

    signal.name becomes the key.
    The value is a list of datapoints for that signal. One per inverter.
    """
    r: dict[str, list[signals.DatapointValueType]] = {}
    for signal_data in inverter_data:
        for name, value in signal_data.items():
            if name not in r:
                r[name] = []
            r[name].append(value)
    return r


async def main(hosts: list[str]):
    print(
        "Warning: this script assumes that you have run "
        "scripts/sync_unsupported_winet_registers!"
    )
    signal_definitions = signals.load_yaml()

    # only winet pymodbus will use the disabled flag.
    signal_definitions.disable_winet_signals()

    # Store data in file for development of this script.
    # As we don't want to query the inverter every time.
    try:
        logger.warning("Loading data from .compare_access_data.yaml")
        logger.warning("Delete this file to re-query the inverter.")
        with open(".compare_access_data.yaml") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        data = await collect_data(signal_definitions, hosts)
        print("Writing data to .compare_access_data.yaml: ", data)

        with open(".compare_access_data.yaml", "w") as f:
            yaml.dump(data, f)

    data_by_inverter = split_data_by_inverter(data)

    # ToDo: add yaml, add raw register output
    print_markdown_table(signal_definitions, data_by_inverter, "compare.md")


def print_markdown_table(
    signal_definitions: signals.SignalDefinitions,
    data_by_inverter: dict[str, list[dict[str, signals.DatapointValueType]]],
    outfile: str,
):
    with open(outfile, "w") as f:
        for inverter_sn, inverter_data in data_by_inverter.items():
            f.write(f"# {inverter_sn}\n")

            # We print attribute by attribute, so we need to transpose the data.
            transposed_data = transpose_data_by_signal(inverter_data)

            header = "| Signal | "
            for column in transposed_data["mode"]:
                header += column + " | "
            f.write(header + "\n")
            f.write("| --- " * (len(transposed_data["mode"]) + 1) + "|\n")

            for signal in signal_definitions._definitions.values():
                line = f"| {signal.name} | "
                for value in transposed_data.get(signal.name, ["Not available"]):
                    line += str(value) + " | "
                f.write(line + "\n")

            f.write("\n\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        print("Usage: compare_access.py <host> [<host> ...]")
        print("Note: slave id can be appended to the host, separated by a slash.")
        print("Example for slave 2: 192.168.13.80/2")
        print("When no slave id is given, slave 1 is assumed.")
        print(
            "Example command line: scripts/compare_access.py "
            "192.168.13.79 192.168.13.58 192.168.13.80/2 192.168.13.74"
        )
        exit(1)
    else:
        hosts = sys.argv[1:]
        print("command line: ", hosts)

        asyncio.run(main(hosts))
