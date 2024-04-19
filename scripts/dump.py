#!/usr/bin/env python3

"""
This script will query an inverter via:
* modbus
* WiNet modbus
* via WiNet http
and compare the results.
"""

import argparse
import asyncio
import json
import logging
import pickle
from dataclasses import asdict, dataclass, is_dataclass
from enum import StrEnum
from pathlib import Path

if __package__ is None:
    # Script was executed from the command line via ./scripts/dump.py
    import fix_path  # type: ignore  # noqa: F401

from custom_components.sungrow.core import (
    deserialize,
    modbus_base,
    signals,
)
from custom_components.sungrow.core.inverter import SungrowInverter
from custom_components.sungrow.core.modbus_types import (
    MappedData,
    RawData,
    RegisterType,
)

logging.basicConfig(level=logging.INFO)
# logging.getLogger("pymodbus").setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# Log DEBUG to file.
file_handler = logging.FileHandler("dump.log", "w")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s %(name)s [%(levelname)s] %(message)s"),
)
logging.getLogger().addHandler(file_handler)


@dataclass
class TaskResult:
    mode: str | None
    host: str
    slave: int | None = None
    signal_definitions: signals.SignalDefinitions | None = None
    raw_data: dict[RegisterType, RawData] | None = None
    stats: modbus_base.ModbusConnectionBase.Stats | None = None
    error: Exception | str | None = None


async def collect_data_from(
    host: str,
    port: int | None,
    slave: int | None,
    connection_mode: str | None,
) -> TaskResult:
    inv: SungrowInverter | None = None

    def info_msg(msg):
        if inv:
            prefix = f"slave: {inv._client.slave}, mode: {inv.connection_mode}"
        else:
            prefix = f"slave: {slave or 'unknown'}, mode: {connection_mode or 'any'}"
        logger.info(f"{host} ({prefix}): {msg}")

    info_msg("Connecting...")
    try:
        inv = await SungrowInverter.create(
            host, port=port, slave=slave, connection=connection_mode
        )
        if not inv:
            info_msg("Failed to connect")
            return TaskResult(connection_mode, host, slave, error="Failed to connect")

        async with inv:
            # mode = inv.get_connection_mode() TODO: implement this in SungrowInverter
            info_msg(f"Connected via {inv.connection_mode}")

            raw_data = await inv._client.read_raw(
                inv._signal_definitions.enabled_modbus_signals()
            )

            if raw_data:
                info_msg(
                    f"retrieved registers: {len(raw_data[RegisterType.READ])} READ + "
                    f"{len(raw_data[RegisterType.HOLD])} HOLD"
                )
            info_msg(f"stats: {inv._client.stats}")

            return TaskResult(
                inv.connection_mode,
                host,
                inv._client.slave,
                signal_definitions=inv._signal_definitions,
                stats=inv._client.stats,
                raw_data=raw_data,
            )
    except modbus_base.CannotConnectError as e:
        info_msg(f"Failed to connect ({e})")
        logger.debug("Details:", exc_info=True)
        return TaskResult(connection_mode, host, slave, error=e)
    except Exception as e:
        info_msg(f"{host}/{slave}/pymodbus: Failed during query ({e})")
        logger.debug("Details:", exc_info=True)
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
            slave = None

        # Parse port from host string?
        port = None  # Auto

        tasks.append(collect_data_from(host, port, slave, None))

    # parallel will probably not work with sungrow inverters?!
    if parallel:
        return await asyncio.gather(*tasks)
    else:
        return [await task for task in tasks]


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
            print(d.signal_definitions.get_signal_definition_by_name("serial_number"))
            print(dpc.mapped_data["serial_number"])
            dpc.decoded = deserialize.decode_signals(
                d.signal_definitions.enabled_modbus_signals(), dpc.mapped_data
            )
            print(dpc.decoded)
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


pickle_filename = ".dump.pickle"


def write_pickle(task_results: list[TaskResult]):
    with Path(pickle_filename).open("wb") as file:
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

    with Path("dump.json").open("w") as file:
        json.dump(task_results, file, indent=4, cls=EnhancedJSONEncoder)


async def main(hosts: list[str], cached: bool):
    all_signals = signals.load_yaml()

    # Store data in file for development of this script.
    # As we don't want to query the inverter every time.
    # TODO: add command line option to force re-querying the inverter.
    task_results: list[TaskResult] | None = None
    if cached:
        try:
            with Path(pickle_filename).open("rb") as f:
                logger.warning("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                logger.warning(f"Loading data from {pickle_filename}")
                logger.warning("Delete this file to re-run actual connections.")
                logger.warning(
                    "Note: you need to delete it if you query a different host!"
                )
                logger.warning("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                task_results = pickle.load(f)
        except FileNotFoundError:
            pass
        except AttributeError:
            logger.warning(f"Failed to load data from {pickle_filename}.")

    if task_results is None:
        task_results = await collect_data(hosts)
        print(f"Writing data to {pickle_filename}...")
        write_pickle(task_results)

    # TODO: remove pickle file and use json only.
    write_json(task_results)

    data_by_inverter = merge_by_inverter(task_results)

    markdown_write_file("dump.md", all_signals, data_by_inverter)


def markdown_write_summary(f, data_by_inverter: dict[str, list[DataPerConnection]]):
    f.write("# Summary:\n\n")
    f.write("| SN | Host | Mode | Read Calls | Errors |\n")
    f.write("| --- | --- | --- | --- | --- |\n")
    for sn, connections in data_by_inverter.items():
        for per_connection in connections:
            if per_connection.error:
                e = per_connection.error
                if isinstance(e, Exception):
                    error = f"{e.__class__.__name__}: {e}"
                else:
                    error = str(e)
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
    with Path(outfile).open("w") as f:
        markdown_write_summary(f, data_by_inverter)
        markdown_write_signals(f, all_signals, data_by_inverter)
        markdown_write_raw_data(f, data_by_inverter)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Dump data from inverter.")
    parser.add_argument(
        "hosts",
        metavar="host",
        type=str,
        nargs="+",
        help="Hosts to query. "
        "Optionally with slave id, separated by a slash. "
        "Example for slave 2: 192.168.13.80/2",
    )
    parser.add_argument(
        "--cached",
        action="store_true",
        help="Use cached data from previous run.",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Query all hosts in parallel.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Increase output verbosity.",
    )
    return parser.parse_args()


def run():
    args = parse_arguments()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    asyncio.run(main(hosts=args.hosts, cached=args.cached))


if __name__ == "__main__":
    run()
