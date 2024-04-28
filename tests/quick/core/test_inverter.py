import logging
from contextlib import contextmanager
from multiprocessing import context
from typing import cast
from unittest.mock import patch

import pytest

from custom_components.sungrow.core import (
    connection,
    deserialize,
    inverter,
    signals,
)

logging.basicConfig(level=logging.DEBUG)
pytest_plugins = ("pytest_asyncio",)


# Implements the ConnectionProto protocol
class FakeConnection:
    def __init__(
        self,
        data: deserialize.DecodedSignals,
        expect_connect: bool = False,
        expect_disconnect: bool = False,
    ):
        # We intentionally do not call super().__init__ here!
        self.data = data
        self.slave: int | None = None
        self.expect_connect = expect_connect
        self.expect_disconnect = expect_disconnect
        self.connected = True

    async def connect(self):
        if not self.expect_connect:
            raise AssertionError("Should not be called")

    async def disconnect(self):
        if not self.expect_disconnect:
            raise AssertionError("Should not be called")
        self.connected = False

    async def read_single_signal(
        self,
        signal: signals.SungrowSignalDefinition,
    ) -> signals.DatapointValueType | None:
        return self.data.get(signal.name)

    async def read(
        self,
        query: list[signals.SungrowSignalDefinition],
    ) -> deserialize.DecodedSignals:
        return {s.name: self.data.get(s.name) for s in query}

    async def create_inverter(self, is_http: bool = False):
        return await inverter.SungrowInverter.create(
            inverter.SungrowInverter.ConnectionData(
                cast(connection.ConnectionProto, self), is_http
            )
        )


@pytest.mark.asyncio()
async def test_create_inverter_with_no_signals_will_not_connect():
    con = FakeConnection({}, expect_disconnect=True)
    inv = await con.create_inverter()
    assert inv is None
    assert con.connected is False


@pytest.mark.asyncio()
async def test_create_inverter_with_minimal_signals():
    con = FakeConnection({"device_type_code": "x", "serial_number": "sn"})
    inv = await con.create_inverter()
    assert inv is not None

    assert inv.serial_number == "sn"
    assert inv.model == "x"
