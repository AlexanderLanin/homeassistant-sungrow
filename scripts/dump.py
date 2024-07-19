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
import sys
from dataclasses import asdict, dataclass, is_dataclass
from enum import StrEnum
from pathlib import Path

from result import Err, Ok

from scripts.common import helpers

if __package__ is None:
    # Script was executed from the command line via ./scripts/dump.py
    import fix_path  # type: ignore  # noqa: F401

from custom_components.sungrow.core import (
    connection_base,
    connection_factory,
    modbus_connection_base,
    signals,
)
from custom_components.sungrow.core.connection_factory import ConnectionParams
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

ConnectionParamInclSlaveId = tuple[ConnectionParams, int | None]


@dataclass
class TaskResult:
    connection_params: ConnectionParams
    slave: int | None = None
    signal_definitions: signals.SignalDefinitions | None = None
    data: connection_base.DecodedSignals | None = None
    stats: modbus_connection_base.ModbusConnection_Base.Stats | None = None
    error: Exception | str | None = None


async def collect_data_from(
    params: ConnectionParams,
    slave: int | None,
) -> TaskResult:
    assert params.connection, "Must have been set before"
    try:
        inv: SungrowInverter | None = None

        def info_msg(msg):
            if inv:
                prefix = (
                    f"slave: {inv._client.slave}, mode: {inv.readable_connection_mode}"
                )
            else:
                prefix = (
                    f"slave: {slave or 'unknown'}, mode: {params.connection or 'any'}"
                )
            logger.info(f"{params.host} ({prefix}): {msg}")

        info_msg("Connecting...")
        con = await connection_factory.connect(params)
        if not con:
            info_msg("Failed to connect")
            return TaskResult(params, slave, error="Failed to connect")
        info_msg("Connected")

        info_msg("Retrieving initial data...")
        inv = await SungrowInverter.create(con, slave)
        if not inv:
            info_msg("Failed to retrieve intial data")
            await con.disconnect()
            return TaskResult(params, slave, error="Failed to retrieve intial data")
        info_msg("Initial data retrieved")

        info_msg("Querying ALL data...")
        async with inv:
            # We need to read all, inclusive disabled signals, to establish if
            # they are correctly disabled. That's why we cannot use inv.pull_data()
            # here. However, there is no need to requery data already queried during
            # initial handshake.
            query = [
                s
                for s in inv._signal_definitions.all_signals()
                if s.is_supported
                in (
                    signals.ModbusSignal.Supported.NEVER_ATTEMPTED,
                    signals.ModbusSignal.Supported.UNKNOWN_FROM_MULTI_SIGNAL_QUERY,
                )
            ]

            res = await inv.pull_data(query)
            if isinstance(res, Ok):
                inv.data.update(res.ok_value)
                err_value = None
            else:
                err_value = res.err_value

            return TaskResult(
                connection_params=params,
                slave=inv._client.slave,
                signal_definitions=inv._signal_definitions,
                data=inv.data,
                error=err_value,
            )
            # Note: inv is being closed here.

    except Exception as e:
        info_msg(f"Unexpected error during query ({e}, {type(e).__name__})")
        logger.debug("Details:", exc_info=True)
        return TaskResult(params, slave=slave, error=e)


async def collect_data_from_all_hosts(
    hosts: list[ConnectionParamInclSlaveId],
    parallel: bool = False,
) -> list[TaskResult]:
    tasks = [collect_data_from(host, slave_id) for host, slave_id in hosts]

    # parallel will probably not work with sungrow inverters?!
    if parallel:
        return await asyncio.gather(*tasks)
    else:
        return [await task for task in tasks]


def merge_by_inverter(results: list[TaskResult]):
    r: dict[str, list[TaskResult]] = {}
    for d in sorted(results, key=lambda d: d.connection_params.host):
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


def load_from_cache_if_available(_hosts: list[ConnectionParamInclSlaveId]):
    # TODO: remove pickle file and use json only.
    try:
        with Path(pickle_filename).open("rb") as f:
            logger.warning("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            logger.warning(f"Loading data from {pickle_filename}")
            logger.warning("Because you specified --cached parameter.")
            logger.warning("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            return pickle.load(f)
    except FileNotFoundError:
        logger.warning(f"No cachefile at {pickle_filename}.")
        return None
    except AttributeError:
        logger.warning(f"Failed to load data from {pickle_filename}.")
        return None


def write_to_cache(task_results: list[TaskResult]):
    print(f"Writing data to {pickle_filename}...")
    write_pickle(task_results)


async def main(hosts: list[ConnectionParamInclSlaveId], load_cached: bool):
    all_signals = signals.load_yaml()

    # Expand all possible connection params (e.g. one entry for http and one modbus)
    hosts = [
        (host, slave)
        for host_param, slave in hosts
        for host in connection_factory.all_possible_connection_params(host_param)
    ]

    task_results: list[TaskResult] | None = None
    if load_cached:
        task_results = load_from_cache_if_available(hosts)
        if task_results is None:
            sys.exit("Loading cached data failed.")
    else:
        task_results = await collect_data_from_all_hosts(hosts)
        write_to_cache(task_results)

    write_json(task_results)
    print("Data written to dump.json")

    data_by_inverter = merge_by_inverter(task_results)

    markdown_write_file("dump.md", all_signals, data_by_inverter)
    print("Summary written to dump.md")


def markdown_write_summary(f, data_by_inverter: dict[str, list[TaskResult]]):
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
                f"| {sn} | {per_connection.connection_params.host}/{per_connection.slave} | "
                f"{per_connection.connection_params.connection} | "
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
                f"{c.connection_params.host}/{c.slave}/{c.connection_params.connection}"
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

    parsed_hosts = [
        helpers.parse_fully_qualified_host_param(h).unwrap() for h in args.hosts
    ]

    asyncio.run(main(parsed_hosts, load_cached=args.cached))


if __name__ == "__main__":
    run()
