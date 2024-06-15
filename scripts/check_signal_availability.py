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
from custom_components.sungrow.core.inverter_types import Level

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def check(host: str):
    logger.info(f"Checking {host}...")
    ic = await inverter.SungrowInverter.create(
        connection.ConnectionParams(host, None, "pymodbus"),
        None,
        level_of_detail=Level.DEBUG,
    )
    if not ic:
        sys.exit("Failed to connect to the inverter.")

    logger.info(f"IC: {ic}")

    await check_signals(ic)


async def check_signals(ic: inverter.SungrowInverter):
    # FIXME: query everything and mark all non zero values as supported.
    # Then query only the remaining values one by one!

    for signal in tqdm(ic._signal_definitions.all_signals()):
        _ = await inverter.pull_single_signal(ic._client, signal)


async def main(args):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", help="The host to connect to.")
    parsed = parser.parse_args(args)
    await check(parsed.host)


if __name__ == "__main__":
    run(main(args=sys.argv[1:]))
