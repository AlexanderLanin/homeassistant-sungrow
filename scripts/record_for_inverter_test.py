#!/usr/bin/env python3
"""Trigger specific interaction with the inverter and record response."""

import argparse
import asyncio
import logging
import sys

from result import Err, Ok, Result

from custom_components.sungrow.core import connection_factory, inverter, signals
from custom_components.sungrow.core.connection_base import Connection, DecodedSignals
from custom_components.sungrow.core.inverter_types import Level
from scripts.common import helpers

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("pymodbus").setLevel(logging.WARNING)


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    helpers.add_host_param(parser)
    return parser.parse_args()


class RecordingConnectionSpy(Connection):
    def __init__(self, connection: Connection):
        self.real_connection = connection

    async def connect(self):
        await self.real_connection.connect()

    async def disconnect(self):
        await self.real_connection.disconnect()

    @property
    def is_http(self) -> bool:
        return self.real_connection.is_http

    @property
    def connected(self) -> bool:
        return self.real_connection.connected

    @property
    def slave(self) -> int:
        return self.real_connection.slave

    @slave.setter
    def slave(self, value: int):
        self.real_connection.slave = value

    async def read(
        self,
        query: list[signals.SignalDefinition] | signals.SignalDefinition,
    ) -> Result[DecodedSignals, Exception]:
        # Always convert to a list to avoid different code paths
        if isinstance(query, signals.SignalDefinition):
            query = [query]

        result = await self.real_connection.read(query)
        if isinstance(result, Ok):
            values = result.ok_value
            for key, value in values.items():
                print(f"Recorded: {key}: {value}")
        else:
            for signal in query:
                print(f"Recorded Failure to query: {signal}")

        return result


async def main():
    args = parse_arguments()
    res = helpers.parse_fully_qualified_host_param(args.host)
    if isinstance(res, Err):
        sys.exit(res.err_value)

    host, slave_id = res.ok_value
    print(f"Connecting to: {host} with slave_id: {slave_id}...")

    real_connection = await connection_factory.connect(host)
    if not real_connection:
        sys.exit("Could not connect to inverter")

    # Wrap the connection in a spy
    connection_wrapper = RecordingConnectionSpy(real_connection)

    # FIXME: this runs way too many queries at once in the beginning...
    _inv = await inverter.SungrowInverter.create(
        connection_wrapper, slave_id, level_of_detail=Level.MINIMAL
    )

    # Record the response
    # response = inverter.record_response()

    # print(response)


asyncio.run(main())
