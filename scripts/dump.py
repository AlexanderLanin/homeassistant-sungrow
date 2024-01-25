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

try:
    import scripts.fix_path  # noqa: F401
except ImportError:
    import fix_path  # noqa: F401

from custom_components.sungrow.core import (
    deserialize,
    modbus_base,
    signals,
)
from custom_components.sungrow.core.inverter import connect_and_get_basic_data
from custom_components.sungrow.core.modbus_types import (
    MappedData,
    RawData,
    RegisterType,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Log DEBUG to file.
file_handler = logging.FileHandler("dump.log", "w")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s %(name)s [%(levelname)s] %(message)s")
)
logging.getLogger().addHandler(file_handler)


@dataclass
class TaskResult:
    mode: str
    host: str
    slave: int | None = None
    signal_definitions: signals.SignalDefinitions | None = None
    raw_data: dict[RegisterType, RawData] | None = None
    stats: modbus_base.ModbusConnectionBase.Stats | None = None
    error: Exception | str | None = None


async def collect_data_from(
    host: str,
    port: int | None,
    slave: int,
    connection_mode: str,
) -> TaskResult:
    def info(msg):
        logger.info(f"{host}/{slave}/{connection_mode}: {msg}")

    info("Attempting to connect...")
    try:
        ic = await connect_and_get_basic_data(
            host, port=port, slave=slave, connection=connection_mode
        )
        if ic:
            async with ic.connection:
                logger.info(f"{host}/{slave}/pymodbus: Connected")

                raw_data = await ic.connection.read_raw(
                    ic.signal_definitions.enabled_modbus_signals()
                )

            suffix = " WiNet" if await ic.is_modbus_winet() else ""
            return TaskResult(
                connection_mode + suffix,
                host,
                slave,
                signal_definitions=ic.signal_definitions,
                stats=ic.connection.stats,
                raw_data=raw_data,
            )
        else:
            return TaskResult(connection_mode, host, slave, error="No connection")
    except modbus_base.CannotConnectError as e:
        info(f"Failed to connect ({e})")
        return TaskResult(connection_mode, host, slave, error=e)
    except modbus_base.ModbusError as e:
        logger.warning(f"{host}/{slave}/pymodbus: Failed during query ({e})")
        return TaskResult(connection_mode, host, slave, error=e)


async def collect_data(
    hosts: list[str],
    parallel: bool = False,
) -> list[TaskResult]:
    tasks = []
    for host in hosts:
        if "/" in host:
            host, slave_str = host.split("/")
            slave = int(slave_str)
        else:
            slave = 1

        # Parse port from host string?
        port = None  # Auto

        tasks.append(collect_data_from(host, port, slave, "http"))
        tasks.append(collect_data_from(host, port, slave, "pymodbus"))

    # parallel will probably not work with sungrow inverters?!
    if parallel:
        return await asyncio.gather(*tasks)
    else:
        results = []
        for task in tasks:
            r = await task
            results.append(r)
            logger.info(f"Collected data for {r.host}/{r.slave} via {r.mode}:")
            if r.raw_data:
                logger.info(
                    f"registers: {len(r.raw_data[RegisterType.READ])} READ + "
                    f"{len(r.raw_data[RegisterType.HOLD])} HOLD"
                )
            if r.error:
                logger.info(f"error: {r.error}")
            logger.info(f"stats: {r.stats}")
            logger.info("Pausing 5 seconds before next task...")
            await asyncio.sleep(5)
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


def merge_by_inverter(results: list[TaskResult]):
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
            assert d.signal_definitions
            dpc.mapped_data = modbus_base.map_raw_to_signals(
                d.raw_data, d.signal_definitions.enabled_modbus_signals()
            )
            dpc.decoded = deserialize.decode_signals(
                d.signal_definitions.enabled_modbus_signals(), dpc.mapped_data
            )
            sn = dpc.decoded["serial_number"]
            assert isinstance(sn, str)
        else:
            sn = "-"

        r.setdefault(sn, []).append(dpc)

    return dict(sorted(r.items()))


def collect_all_registers(inverter_data: list[DataPerConnection]):
    all_registers: dict[RegisterType, set[int]] = {
        RegisterType.READ: set(),
        RegisterType.HOLD: set(),
    }

    for per_connection in inverter_data:
        if not per_connection.raw_data:
            continue

        for register_type, registers in per_connection.raw_data.items():
            all_registers[register_type].update(registers.keys())

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
            if isinstance(o, signals.SignalDefinitions):
                return o._definitions
            return super().default(o)

    with open(".compare_access_data.json", "w") as file:
        json.dump(task_results, file, indent=4, cls=EnhancedJSONEncoder)


async def main(hosts: list[str], cached: bool):
    all_signals = signals.load_yaml()

    # Store data in file for development of this script.
    # As we don't want to query the inverter every time.
    # TODO: add command line option to force re-querying the inverter.
    task_results: list[TaskResult] | None = None
    if cached:
        try:
            with open(".compare_access_data.pickle", "rb") as f:
                logger.warning("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                logger.warning("Loading data from .compare_access_data.*")
                logger.warning("Delete this file to re-run actual connections.")
                logger.warning(
                    "Note: you need to delete it if you query a different host!"
                )
                logger.warning("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                task_results = pickle.load(f)
        except FileNotFoundError:
            pass
        except AttributeError:
            logger.warning("Failed to load .compare_access_data.pickle")

    if task_results is None:
        task_results = await collect_data(hosts)
        print("Writing data to .compare_access_data...")
        write_pickle(task_results)

    # TODO: remove pickle file and use json only.
    write_json(task_results)

    data_by_inverter = merge_by_inverter(task_results)

    markdown_write_file("compare.md", all_signals, data_by_inverter)


def markdown_write_summary(f, data_by_inverter: dict[str, list[DataPerConnection]]):
    f.write("# Summary:\n\n")
    f.write("| SN | Host | Mode | Read Calls | Errors |\n")
    f.write("| --- | --- | --- | --- | --- |\n")
    for sn, connections in data_by_inverter.items():
        for per_connection in connections:
            if per_connection.error:
                e = per_connection.error
                assert isinstance(e, Exception)
                error = f"{e.__class__.__name__}: {e}"
            else:
                error = None

            f.write(
                f"| {sn} | {per_connection.host}/{per_connection.slave} | "
                f"{per_connection.mode} | "
                f"{per_connection.stats} | {error} |\n"
            )

    f.write("\n\n")


def markdown_write_signals(
    f,
    all_signals: signals.SignalDefinitions,
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

        for signal in all_signals.all_signals():
            line = f"| {signal.name} | "
            for c in inverter_data:
                value = (
                    c.decoded.get(signal.name, "Not supported")
                    if c.decoded
                    else "No data"
                )
                line += str(value) + " | "
            f.write(line + "\n")

        f.write("\n\n")


def markdown_write_raw_data(
    f,
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
            for register in sorted(registers):
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
    all_signals: signals.SignalDefinitions,
    data_by_inverter: dict[str, list[DataPerConnection]],
):
    with open(outfile, "w") as f:
        markdown_write_summary(f, data_by_inverter)
        markdown_write_signals(f, all_signals, data_by_inverter)
        markdown_write_raw_data(f, data_by_inverter)


def run():
    """Entry point for console_scripts and command line execution."""
    if len(sys.argv) == 1:
        print("Parameters: <host> [<host> ...]")
        print("Note: slave id can be appended to the host, separated by a slash.")
        print("Example for slave 2: 192.168.13.80/2")
        print("When no slave id is given, slave 1 is assumed.")
        print(
            "Example parameters: "
            "192.168.13.79 192.168.13.58 192.168.13.80/2 192.168.13.74"
        )
        exit(1)
    else:
        hosts = sys.argv[1:]
        if hosts[0] == "--cached":
            cached = True
            hosts = hosts[1:]
        else:
            cached = False

        print("command line: ", hosts)

        asyncio.run(main(hosts, cached=cached))


if __name__ == "__main__":
    run()
