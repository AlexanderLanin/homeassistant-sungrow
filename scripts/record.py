#!/usr/bin/env python3
"""Trigger specific interaction with the inverter and record response."""

import argparse
import asyncio
import logging
from math import log

from custom_components.sungrow.core import inverter
from custom_components.sungrow.core.inverter_types import Level
from scripts.common import helpers

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("pymodbus").setLevel(logging.WARNING)


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    helpers.add_host_param(parser)
    parsed = parser.parse_args()
    params = vars(parsed)
    params["host"], params["slave_id"] = helpers.parse_fully_qualified_host_param(
        parsed.host
    )
    return params


async def main():
    args = parse_arguments()

    host = args["host"]
    slave_id = args["slave_id"]

    print(f"Connecting to: {host} with slave_id: {slave_id}...")

    # FIXME: this runs way too many queries at once in the beginning...
    _inv = await inverter.SungrowInverter.create(
        host, slave_id, level_of_detail=Level.MINIMAL
    )

    # Record the response
    # response = inverter.record_response()

    # print(response)


asyncio.run(main())
