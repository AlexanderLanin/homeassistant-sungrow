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
import sys
from dataclasses import asdict, dataclass, is_dataclass
from enum import StrEnum

import scripts.fix_path  # noqa: F401
from custom_components.sungrow.core import (
    deserialize,
    modbus_base,
    modbus_http,
    modbus_py,
    signals,
)
from custom_components.sungrow.core.modbus_types import (
    MappedData,
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
    stats: int | None = None
    error: Exception | None = None


# FIXME data collection is way too slow.
# We need to re-add WiNet detection and/or filtering by models.
# e.g. ~130 unsupported registers = 130 useless queries.


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
            stats=connection.stats,
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
            stats=connection.read_calls,
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


def get_sn_from_raw_data(
    raw_data: dict[RegisterType, RawData],
    signal_definitions: signals.SignalDefinitions,
) -> str:
    sn_signal = signal_definitions.get_signal_definition_by_name("serial_number")
    raw_sn = modbus_base.map_raw_to_signal(raw_data[sn_signal.register_type], sn_signal)
    assert raw_sn
    sn = deserialize.decode_signal(sn_signal, raw_sn)
    assert isinstance(sn, str)
    return sn


@dataclass
class DataPerConnection(TaskResult):
    mapped_data: MappedData | None = None
    decoded: dict[str, signals.DatapointValueType] | None = None


def merge_by_inverter(
    results: list[TaskResult], signal_definitions: signals.SignalDefinitions
):
    r: dict[str, list[DataPerConnection]] = {}
    for d in sorted(results, key=lambda d: d.host):
        dpc = DataPerConnection(
            mode=d.mode,
            host=d.host,
            slave=d.slave,
            raw_data=d.raw_data,
            stats=d.stats,
            error=d.error,
        )
        if d.raw_data:
            dpc.mapped_data = modbus_base.map_raw_to_signals(
                d.raw_data, signal_definitions.all_modbus_signals()
            )
            dpc.decoded = deserialize.decode_signals(
                signal_definitions.all_signals(), dpc.mapped_data
            )
            sn = dpc.decoded["serial_number"]
            assert isinstance(sn, str)
        else:
            sn = "-"

        r.setdefault(sn, []).append(dpc)

    return dict(sorted(r.items()))


def collect_all_registers(inverter_data: list[DataPerConnection]):
    all_registers: dict[RegisterType, list[int]] = {
        RegisterType.READ: [],
        RegisterType.HOLD: [],
    }

    for per_connection in inverter_data:
        if not per_connection.raw_data:
            continue

        for register_type, registers in per_connection.raw_data.items():
            all_registers[register_type].extend(registers.keys())

    return all_registers


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
    except AttributeError:
        task_results = None
        logger.warning("Failed to load .compare_access_data.pickle")
        logger.warning("Running without cached results!")

    # This is intentionally not within the except block, as it makes error messages
    # easier to understand.
    if task_results is None:
        task_results = await collect_data(signal_definitions, hosts)
        print("Writing data to .compare_access_data.yaml: ", task_results)

        write_pickle(task_results)

    # TODO: remove pickle file and use json only.
    write_json(task_results)

    data_by_inverter = merge_by_inverter(task_results, signal_definitions)

    markdown_write_file("compare.md", signal_definitions, data_by_inverter)


def markdown_write_summary(f, data_by_inverter: dict[str, list[DataPerConnection]]):
    f.write("# Summary:\n\n")
    f.write("| SN | Host | Mode | Read Calls | Result | Errors |\n")
    f.write("| --- | --- | --- | --- | --- | --- |\n")
    for sn, connections in data_by_inverter.items():
        for per_connection in connections:
            if per_connection.raw_data:
                registers_ok = 0
                registers_skipped = 0
                for register_type in per_connection.raw_data:
                    for value in per_connection.raw_data[register_type].values():
                        if value is None:
                            registers_skipped += 1
                        else:
                            registers_ok += 1
                result = f"{registers_ok} registers retrieved"
                error = f"{registers_skipped} registers not supported"
            elif per_connection.error:
                result = "Failed"
                e = per_connection.error
                assert isinstance(e, Exception)
                error = f"{e.__class__.__name__}: {e}"
            else:
                result = "internal error"
                error = "internal error"

            f.write(
                f"| {sn} | {per_connection.host}/{per_connection.slave} | "
                f"{per_connection.mode} | "
                f"{per_connection.stats} | {result} | {error} |\n"
            )

    f.write("\n\n")


def markdown_write_signals(
    f,
    signal_definitions: signals.SignalDefinitions,
    data_by_inverter: dict[str, list[DataPerConnection]],
):
    for inverter_sn, inverter_data in data_by_inverter.items():
        if not inverter_data[0].raw_data:
            continue

        f.write(f"# {inverter_sn}\n")

        f.write(
            "| host/slave/mode | "
            + " | ".join(f"{c.host}/{c.slave}/{c.mode}" for c in inverter_data)
            + " |\n"
        )
        f.write("| --- " * (len(inverter_data) + 1) + "|\n")

        for signal in signal_definitions._definitions.values():
            line = f"| {signal.name} | "
            for c in inverter_data:
                value = (
                    c.decoded.get(signal.name, ["Not available"]) if c.decoded else []
                )
                line += str(value) + " | "
            f.write(line + "\n")

        f.write("\n\n")


def markdown_write_raw_data(
    f,
    signal_definitions: signals.SignalDefinitions,
    data_by_inverter: dict[str, list[DataPerConnection]],
):
    for inverter_sn, inverter_data in data_by_inverter.items():
        if not inverter_data[0].raw_data:
            continue

        f.write(f"# {inverter_sn}\n")

        f.write(
            "| host/slave/mode | "
            + " | ".join(f"{c.host}/{c.slave}/{c.mode}" for c in inverter_data)
            + " |\n"
        )
        f.write("| --- " * (len(inverter_data) + 1) + "|\n")

        all_registers = collect_all_registers(inverter_data)
        for register_type, registers in all_registers.items():
            for register in registers:
                line = f"| {register_type} {register} | "
                for c in inverter_data:
                    value = (
                        c.raw_data.get(register_type, {}).get(register)
                        if c.raw_data
                        else None
                    )
                    line += (hex(value) if value else "N/A") + " | "
                f.write(line + "\n")

        f.write("\n\n")


def markdown_write_file(
    outfile: str,
    signal_definitions: signals.SignalDefinitions,
    data_by_inverter: dict[str, list[DataPerConnection]],
):
    with open(outfile, "w") as f:
        markdown_write_summary(f, data_by_inverter)
        markdown_write_signals(f, signal_definitions, data_by_inverter)
        markdown_write_raw_data(f, signal_definitions, data_by_inverter)


def run():
    """Entry point for console_scripts and command line execution."""
    if len(sys.argv) == 1:
        print("Usage: dump.py <host> [<host> ...]")
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


if __name__ == "__main__":
    run()
