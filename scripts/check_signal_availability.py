#!/usr/bin/env python3
"""
Check whether our WiNet marks are up to date.

Note: this will probably not work via modbus proxies.

TODO: make this script completely false positive free and run it in the
background of normal operations. e.g. by running it piece by piece on the
requested ranges.
"""
import argparse
import logging
import sys
from asyncio import run

from tqdm import tqdm

from custom_components.sungrow.core import inverter
from custom_components.sungrow.core.inverter import (
    connect_and_get_basic_data,
    pull_single_signal,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def check(host: str):
    logger.info(f"Checking {host}...")
    ic = await connect_and_get_basic_data(host, None, None, "pymodbus")
    if not ic:
        sys.exit("Failed to connect to the inverter.")

    logger.info(f"IC: {ic}")

    await check_signals(ic)


async def check_signals(ic: inverter.InverterConnection):
    for signal in tqdm(ic.signal_definitions.all_signals()):
        value = await pull_single_signal(ic.connection, signal)

        if value is None and not signal.disabled:
            logging.warning(f"{signal.name} is not readable, but marked as supported")

        if signal.disabled and value is not None:
            if value != 0:
                logging.warning(f"{signal.name} is disabled and supported ({value})")
            else:
                logging.info(f"{signal.name} is disabled and supported ({value})")


async def main(args):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", help="The host to connect to.")
    parsed = parser.parse_args(args)
    await check(parsed.host)


if __name__ == "__main__":
    run(main(args=sys.argv[1:]))
