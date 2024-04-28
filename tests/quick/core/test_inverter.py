import logging
from contextlib import asynccontextmanager, contextmanager
from functools import wraps
from multiprocessing import context
from typing import cast
from unittest.mock import patch

import pytest

from custom_components.sungrow.core import (
    connection,
    deserialize,
    inverter,
    modbus_base,
    signals,
)

logging.basicConfig(level=logging.DEBUG)
pytest_plugins = ("pytest_asyncio",)


class FakeConnection(connection.Connection):
    def __init__(
        self,
        data: deserialize.DecodedSignals,
    ):
        self.data = data
        self.data_on_slave: int = 1
        self.active_slave: int | None = None
        self.allow_connect = False
        self.allow_disconnect = False
        self.connected = True  #
        self.is_http = False

        self.logger = logging.getLogger(__name__ + " :: " + self.__class__.__name__)

    async def connect(self):
        if not self.allow_connect:
            raise AssertionError("Should not be called")

    async def disconnect(self):
        if not self.allow_disconnect:
            raise AssertionError("Should not be called")
        self.connected = False

    async def _read_single_signal(
        self,
        signal: signals.SungrowSignalDefinition,
    ) -> signals.DatapointValueType | None:
        if self.active_slave != self.data_on_slave:
            raise modbus_base.InvalidSlaveError

        self.logger.debug(f"Reading {signal.name} = {self.data.get(signal.name)}")
        return self.data.get(signal.name)

    async def _read(
        self,
        query: list[signals.SungrowSignalDefinition],
    ) -> deserialize.DecodedSignals:
        if self.active_slave != self.data_on_slave:
            raise modbus_base.InvalidSlaveError

        return {s.name: await self.read_single_signal(s) for s in query}

    @property
    def slave(self) -> int:
        if self.active_slave is None:
            return 0  # not sure when this happens. TODO.
        return self.active_slave

    @slave.setter
    def slave(self, value: int):
        self.logger.debug(f"Setting slave to {value}")
        self.active_slave = value

    @property
    def connection_data(self):
        return inverter.SungrowInverter.ConnectionData(self, self.is_http)


@asynccontextmanager
async def create_inv(con: FakeConnection):
    inv = await inverter.SungrowInverter.create(con.connection_data)
    assert inv
    yield inv

    if con.allow_disconnect:
        assert not con.connected


@pytest.mark.asyncio()
async def test_create_inverter_with_no_signals_will_not_connect():
    con = FakeConnection({})
    con.allow_disconnect = True

    inv = await inverter.SungrowInverter.create(con.connection_data)

    assert not inv
    assert not con.connected


@pytest.mark.asyncio()
async def test_create_inverter_with_minimal_signals():
    con = FakeConnection({"device_type_code": "x", "serial_number": "sn"})

    async with create_inv(con) as inv:
        assert inv.serial_number == "sn"
        assert inv.model == "x"


def sig(inv: inverter.SungrowInverter, name):
    return inv._signal_definitions.get_signal_definition_by_name(name)


@pytest.mark.asyncio()
async def test_create_inverter_auto_detect_slave_2():
    con = FakeConnection({"device_type_code": "x", "serial_number": "sn"})
    con.data_on_slave = 2

    async with create_inv(con) as inv:
        assert inv.serial_number == "sn"
        assert inv.model == "x"


@pytest.mark.asyncio()
async def test_create_inverter_detect_no_meter_supported():
    async with create_inv(
        FakeConnection({"device_type_code": "x", "serial_number": "sn"})
    ) as inv:
        power = sig(inv, "meter_active_power")
        power_a = sig(inv, "meter_active_power_phase_a")
        power_b = sig(inv, "meter_active_power_phase_b")
        power_c = sig(inv, "meter_active_power_phase_c")

        assert power.is_supported is False  # not supported
        assert power_a.is_supported is None  # never queried
        assert power_b.is_supported is None  # never queried
        assert power_c.is_supported is None  # never queried

        # Automatic detection should disable all signals
        assert power.disabled
        assert power_a.disabled
        assert power_b.disabled
        assert power_c.disabled


@pytest.mark.asyncio()
async def test_create_inverter_detect_no_meter_connected():
    async with create_inv(
        FakeConnection(
            {
                "device_type_code": "x",
                "serial_number": "sn",
                "meter_active_power": 0,
            }
        )
    ) as inv:
        power = sig(inv, "meter_active_power")
        power_a = sig(inv, "meter_active_power_phase_a")
        power_b = sig(inv, "meter_active_power_phase_b")
        power_c = sig(inv, "meter_active_power_phase_c")

        assert power.is_supported is None  # We don't know from 0 value!
        # assert power_a.is_supported is None
        # assert power_b.is_supported is None
        # assert power_c.is_supported is None

        assert not power.disabled
        assert not power_a.disabled
        assert not power_b.disabled
        assert not power_c.disabled


@pytest.mark.asyncio()
async def test_create_inverter_detect_meter():
    async with create_inv(
        FakeConnection(
            {
                "device_type_code": "x",
                "serial_number": "sn",
                "meter_active_power": 1,
            }
        )
    ) as inv:
        power = sig(inv, "meter_active_power")
        power_a = sig(inv, "meter_active_power_phase_a")
        power_b = sig(inv, "meter_active_power_phase_b")
        power_c = sig(inv, "meter_active_power_phase_c")

        assert power.is_supported is True  # supported and non zero
        assert power_a.is_supported is None  # never queried
        assert power_b.is_supported is None  # never queried
        assert power_c.is_supported is None  # never queried

        # Automatic detection should not disable all signals
        assert not power.disabled
        assert not power_a.disabled
        assert not power_b.disabled
        assert not power_c.disabled
