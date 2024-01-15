#!/usr/bin/env python3

"""
This script will query an inverter via:
* modbus
* WiNet modbus
* via WiNet http
and compare the results.
"""

import asyncio
import json
import logging
import pickle
from dataclasses import asdict, dataclass, is_dataclass
from enum import StrEnum

import fix_path  # type: ignore  # noqa: F401
import yaml

from custom_components.sungrow.core import (
    deserialize,
    modbus_base,
    modbus_http,
    modbus_py,
    signals,
)
from custom_components.sungrow.core.modbus_types import (
    RawData,
    RegisterType,
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
logging.getLogger().addHandler(logging.FileHandler(".compare_access.log", "w"))


@dataclass
class TaskResult:
    mode: str
    host: str
    slave: int | None = None
    raw_data: dict[RegisterType, RawData] | None = None
    read_calls: int = None
    error: Exception | None = None


async def collect_data_via_py_modbus(
    signal_definitions: signals.SignalDefinitions, host: str, slave: int
) -> TaskResult:
    logger.info(f"{host}/{slave}/pymodbus: Attempting to connect...")
    try:
        async with modbus_py.PymodbusConnection(
            host, port=502, slave=slave
        ) as connection:
            logger.info(f"{host}/{slave}/pymodbus: Connected")

            raw_data = await connection.read_raw(
                signal_definitions.all_modbus_signals()
            )

        logger.info(f"{host}/{slave}/pymodbus: {len(raw_data)} registers retrieved")

        return TaskResult(
            "pymodbus",
            host,
            slave,
            read_calls=connection.read_calls,
            raw_data=raw_data,
        )
    except modbus_base.CannotConnectError as e:
        logger.info(f"{host}/{slave}/pymodbus: Failed to connect ({e})")
        return TaskResult("pymodbus", host, slave, error=e)
    except modbus_base.ModbusError as e:
        logger.warning(f"{host}/{slave}/pymodbus: Failed during query ({e})")
        return TaskResult("pymodbus", host, slave, error=e)


async def collect_data_via_winet_http(
    signal_definitions: signals.SignalDefinitions, host: str
) -> TaskResult:
    logger.info(f"{host}/winet_http: Attempting to connect...")
    try:
        async with modbus_http.HttpConnection(host) as connection:
            logger.info(
                f"{host}/winet_http: Connected (Note: this could be any HTTP server)"
            )
            raw_data = await connection.read_raw(
                signal_definitions.all_modbus_signals()
            )
        logger.info(f"{host}/winet_http: {len(raw_data)} registers retrieved")

        return TaskResult(
            "winet_http",
            host,
            read_calls=connection.read_calls,
            raw_data=raw_data,
        )
    except modbus_base.CannotConnectError as e:
        logger.info(f"{host}/winet_http: Failed to connect ({e}))")
        return TaskResult("winet_http", host, error=e)
    except modbus_base.ModbusError as e:
        logger.warning(f"{host}/winet_http: Error during query ({e})")
        return TaskResult("winet_http", host, error=e)


async def collect_data(
    signal_definitions,
    hosts: list[str],
    parallel: bool = False,
) -> list[TaskResult]:
    tasks = []
    for host in hosts:
        slave = 1  # in WiNet modbus, the slave is always 1
        if "/" in host:
            host, slave_str = host.split("/")
            slave = int(slave_str)

        tasks.append(collect_data_via_py_modbus(signal_definitions, host, slave))
        tasks.append(collect_data_via_winet_http(signal_definitions, host))

    if parallel:
        return await asyncio.gather(*tasks)
    else:
        results = []
        for task in tasks:
            results.append(await task)
        return results


def split_data_by_inverter(
    results: list[TaskResult], signal_definitions: signals.SignalDefinitions
):
    """
    In: [{"serial_number": "123", "a": 1}, {"serial_number": "123", "b": 2}]
    Out: {"123": [{"a": 1}, {"b": 2}]}

    serial_number becomes the key.
    The value is a list of dicts, where each dict contains the data for a single signal.
    """

    r: dict[str, list[dict[str, signals.DatapointValueType]]] = {}
    for d in results:
        if d.error or not d.raw_data:
            continue
        mapped = modbus_base.map_raw_to_signals(
            d.raw_data, signal_definitions.all_modbus_signals()
        )
        decoded = deserialize.decode_signals(signal_definitions, mapped)
        decoded["mode"] = f"{d.mode}/{d.host}/{d.slave}"
        sn = decoded["serial_number"]
        assert isinstance(sn, str)
        if sn not in r:
            r[sn] = []
        r[sn].append(decoded)
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


def write_pickle(task_results: list[TaskResult]):
    with open(".compare_access_data.pickle", "wb") as file:
        pickle.dump(task_results, file)


def write_json(task_results: list[TaskResult]):
    class EnhancedJSONEncoder(json.JSONEncoder):
        def default(self, o):
            if is_dataclass(o):
                return asdict(o)
            if isinstance(o, Exception):
                return f"{o.__class__.__name__}: {o}"
            if isinstance(o, StrEnum):
                return o.value
            return super().default(o)

    with open(".compare_access_data.json", "w") as file:
        json.dump(task_results, file, indent=4, cls=EnhancedJSONEncoder)


async def main(hosts: list[str]):
    signal_definitions = signals.load_yaml()

    # Store data in file for development of this script.
    # As we don't want to query the inverter every time.
    # TODO: add command line option to force re-querying the inverter.
    task_results: list[TaskResult] | None = None
    try:
        with open(".compare_access_data.pickle", "rb") as f:
            logger.warning("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            logger.warning("Loading data from .compare_access_data.*")
            logger.warning("Delete this file to re-run actual connections.")
            logger.warning("Note: you need to delete it if you query a different host!")
            logger.warning("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            task_results = pickle.load(f)
    except FileNotFoundError:
        task_results = None

    # This is intentionally not within the except block, as it makes error messages
    # easier to understand.
    if task_results is None:
        task_results = await collect_data(signal_definitions, hosts)
        print("Writing data to .compare_access_data.yaml: ", task_results)

        write_pickle(task_results)

    # TODO: remove pickle file and use json only.
    write_json(task_results)

    data_by_inverter = split_data_by_inverter(task_results, signal_definitions)

    markdown_write_file(
        "compare.md", signal_definitions, task_results, data_by_inverter
    )


def markdown_write_summary(f, task_results: list[TaskResult]):
    f.write("# Summary:\n\n")
    f.write("| Host | Mode | Read Calls | Result | Errors |\n")
    f.write("| --- | --- | --- | --- | --- |\n")
    for t in task_results:
        if t.raw_data:
            registers_ok = 0
            registers_skipped = 0
            for register_type in t.raw_data:
                for value in t.raw_data[register_type].values():
                    if value is None:
                        registers_skipped += 1
                    else:
                        registers_ok += 1
            result = f"{registers_ok} registers retrieved"
            error = f"{registers_skipped} registers not supported"
        elif t.error:
            result = "Failed"
            assert isinstance(t.error, Exception)
            error = f"{t.error.__class__.__name__}: {t.error}"
        else:
            result = "internal error"
            error = "internal error"

        f.write(
            f"| {t.host}/{t.slave} | {t.mode} | {t.read_calls} | {result} | {error} |\n"
        )

    f.write("\n\n")


def markdown_write_signals(
    f,
    signal_definitions: signals.SignalDefinitions,
    data_by_inverter: dict[str, list[dict[str, signals.DatapointValueType]]],
):
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


def markdown_write_file(
    outfile: str,
    signal_definitions: signals.SignalDefinitions,
    task_results: list[TaskResult],
    data_by_inverter: dict[str, list[dict[str, signals.DatapointValueType]]],
):
    with open(outfile, "w") as f:
        markdown_write_summary(f, task_results)
        markdown_write_signals(f, signal_definitions, data_by_inverter)


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
