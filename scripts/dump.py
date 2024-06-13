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

from result import Err, Ok

if __package__ is None:
    # Script was executed from the command line via ./scripts/dump.py
    import fix_path  # type: ignore  # noqa: F401

from custom_components.sungrow.core import (
    deserialize,
    modbus_base,
    signals,
)
from custom_components.sungrow.core.inverter import SungrowInverter

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("pymodbus").setLevel(logging.INFO)
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
    connection: SungrowInverter.ConnectionParams
    slave: int | None = None
    signal_definitions: signals.SignalDefinitions | None = None
    data: deserialize.DecodedSignals | None = None
    stats: modbus_base.ModbusConnectionBase.Stats | None = None
    error: Exception | str | None = None


async def collect_data_from(
    params: SungrowInverter.ConnectionParams,
    slave: int | None,
) -> TaskResult:
    inv: SungrowInverter | None = None

    def info_msg(msg):
        if inv:
            prefix = f"slave: {inv._client.slave}, mode: {inv.connection_mode}"
        else:
            prefix = f"slave: {slave or 'unknown'}, mode: {params.connection or 'any'}"
        logger.info(f"{params.host} ({prefix}): {msg}")

    info_msg("Connecting...")
    try:
        inv = await SungrowInverter.create(params, slave)
        if not inv:
            info_msg("Failed to connect")
            return TaskResult(params, slave, error="Failed to connect")

        con = SungrowInverter.ConnectionParams(
            host=params.host, port=None, connection=inv.connection_mode
        )

        async with inv:
            # mode = inv.get_connection_mode() TODO: implement this in SungrowInverter
            info_msg(f"Connected via {inv.connection_mode}")

            # We need to read all, inclusive disabled signals, to establish if
            # they are correctly disabled. That's why we cannot use inv.pull_data()
            # here.
            # However, there is no need to requery known data.
            query = [
                s
                for s in inv._signal_definitions.all_signals()
                if s.is_supported == signals.ModbusSignal.Supported.NEVER_ATTEMPTED
            ]
            res = await inv._client.read(query)

            if isinstance(res, Ok):
                inv.data.update(res.ok_value)
                err_value = None
            else:
                err_value = res.err_value

            return TaskResult(
                connection=con,
                slave=inv._client.slave,
                signal_definitions=inv._signal_definitions,
                data=inv.data,
                error=err_value,
            )

    except modbus_base.CannotConnectError as e:
        info_msg(f"Failed to connect ({e}, {type(e).__name__})")
        logger.debug("Details:", exc_info=True)
        return TaskResult(params, slave=slave, error=e)
    except Exception as e:
        info_msg(f"Unexpected error during query ({e}, {type(e).__name__})")
        logger.debug("Details:", exc_info=True)
        return TaskResult(params, slave=slave, error=e)


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
        cp = SungrowInverter.ConnectionParams(host, None, None)
        tasks.append(collect_data_from(cp, slave))

    # parallel will probably not work with sungrow inverters?!
    if parallel:
        return await asyncio.gather(*tasks)
    else:
        return [await task for task in tasks]


def merge_by_inverter(results: list[TaskResult]):
    r: dict[str, list[TaskResult]] = {}
    for d in sorted(results, key=lambda d: d.connection.host):
        if d.data:
            sn = d.data["serial_number"]
            assert isinstance(sn, str)
        else:
            sn = "-"

        r.setdefault(sn, []).append(d)

    return dict(sorted(r.items()))


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


def markdown_write_summary(f, data_by_inverter: dict[str, list[TaskResult]]):
    f.write("# Summary:\n\n")
    f.write("| SN | Host | Mode | Read Calls | Errors |\n")
    f.write("| --- | --- | --- | --- | --- |\n")
    for sn, connections in data_by_inverter.items():
        for per_connection in connections:
            assert per_connection.data

            if per_connection.error:
                e = per_connection.error
                if isinstance(e, Exception):
                    error = f"{e.__class__.__name__}: {e}"
                else:
                    error = str(e)
            else:
                error = None

            f.write(
                f"| {sn} | {per_connection.connection.host}/{per_connection.slave} | "
                f"{per_connection.connection.connection} | "
                f"{per_connection.stats} | {error} |\n"
            )

    f.write("\n\n")


def markdown_write_signals(
    f,
    all_signals: signals.SignalDefinitions,
    data_by_inverter: dict[str, list[TaskResult]],
):
    for inverter_sn, results_for_same_sn in data_by_inverter.items():
        if not results_for_same_sn[0].data:
            continue

        f.write(f"# {inverter_sn}\n")

        f.write(
            "| host/slave/mode | "
            + " | ".join(
                f"{c.connection.host}/{c.slave}/{c.connection.connection}"
                for c in results_for_same_sn
            )
            + " |\n"
        )
        f.write("| --- " * (len(results_for_same_sn) + 1) + "|\n")

        for signal in all_signals.all_signals():
            line = f"| {signal.name} | "
            for result in results_for_same_sn:
                assert result.data
                value = result.data.get(signal.name, "-")
                line += f"{signal.is_supported} {value} | "
            f.write(line + "\n")

        f.write("\n\n")


def markdown_write_file(
    outfile: str,
    all_signals: signals.SignalDefinitions,
    data_by_inverter: dict[str, list[TaskResult]],
):
    with Path(outfile).open("w") as f:
        markdown_write_summary(f, data_by_inverter)
        markdown_write_signals(f, all_signals, data_by_inverter)


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
