import logging
from contextlib import asynccontextmanager
from tarfile import data_filter

import pytest
from result import Err, Ok, Result

from custom_components.sungrow.core import (
    connection_base,
    connection_factory,
    inverter,
    modbus_connection_base,
    modbus_types,
    signals2,
)
from custom_components.sungrow.core.inverter_types import Level

logging.basicConfig(level=logging.DEBUG)
pytest_plugins = ("pytest_asyncio",)


class FakeConnection(connection_base.Connection):
    def __init__(self, data: connection_base.DecodedSignals, only_expected=False):
        self.data = data
        self.data_on_slave: int = 1
        self.active_slave: int | None = None
        self.allow_connect = False
        self.allow_disconnect = False
        self._connected = True  #
        self.requested_signals = 0
        self.only_expected = only_expected

        self.logger = logging.getLogger(__name__ + " :: " + self.__class__.__name__)

    async def connect(self):
        if not self.allow_connect:
            raise AssertionError("Should not be called")

    async def disconnect(self):
        if not self.allow_disconnect:
            raise AssertionError("Should not be called")
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    async def _read(
        self,
        query: list[signals2.SignalDefinition],
    ) -> Result[connection_base.DecodedSignals, Exception]:
        self.requested_signals += len(query)

        if self.only_expected:
            for s in query:
                assert s.name in self.data, f"Unexpected signal {s.name} requested"

        if self.active_slave != self.data_on_slave:
            return Err(modbus_connection_base.InvalidSlaveError())

        return Ok({s.name: self.data.get(s.name) for s in query})

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
    def is_http(self) -> bool:
        return False


@asynccontextmanager
async def create_inv(con: FakeConnection):
    inv = await inverter.SungrowInverter.create(con)
    assert inv
    yield inv

    if con.allow_disconnect:
        assert not con._connected


@pytest.mark.asyncio()
async def test_create_inverter_with_no_signals_will_not_connect():
    con = FakeConnection({})
    con.allow_disconnect = True

    inv = await inverter.SungrowInverter.create(con)

    assert not inv
    assert not con._connected


@pytest.mark.asyncio()
async def test_create_inverter_with_minimal_signals():
    data: connection_base.DecodedSignals = {
        "device_type_code": "x",
        "serial_number": "sn",
    }

    async with create_inv(FakeConnection(data)) as inv:
        assert inv.serial_number == "sn"
        assert inv.model == "x"


@pytest.mark.asyncio()
async def test_create_inverter_auto_detect_slave_2():
    con = FakeConnection({"device_type_code": "x", "serial_number": "sn"})
    con.data_on_slave = 2

    async with create_inv(con) as inv:
        assert inv.serial_number == "sn"
        assert inv.model == "x"


def sig(inv: inverter.SungrowInverter, name):
    return inv._signal_definitions.get_signal_definition_by_name(name)


@pytest.mark.asyncio()
async def test_create_inverter_detect_no_meter_supported():
    async with create_inv(
        FakeConnection({"device_type_code": "x", "serial_number": "sn"})
    ) as inv:
        power = sig(inv, "meter_active_power")
        power_a = sig(inv, "meter_active_power_phase_a")
        power_b = sig(inv, "meter_active_power_phase_b")
        power_c = sig(inv, "meter_active_power_phase_c")

        s = modbus_types.ModbusSignal.Supported
        assert power.is_supported is s.NO
        assert power_a.is_supported is s.NEVER_ATTEMPTED
        assert power_b.is_supported is s.NEVER_ATTEMPTED
        assert power_c.is_supported is s.NEVER_ATTEMPTED

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

        s = modbus_types.ModbusSignal.Supported
        # assert power.is_supported is s.CONFIRMED_UNKNOWN # FIXME
        assert power_a.is_supported is s.NEVER_ATTEMPTED
        assert power_b.is_supported is s.NEVER_ATTEMPTED
        assert power_c.is_supported is s.NEVER_ATTEMPTED

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

        s = modbus_types.ModbusSignal.Supported
        assert power.is_supported is s.YES
        assert power_a.is_supported is s.NEVER_ATTEMPTED
        assert power_b.is_supported is s.NEVER_ATTEMPTED
        assert power_c.is_supported is s.NEVER_ATTEMPTED

        # Automatic detection should not disable all signals
        assert not power.disabled
        assert not power_a.disabled
        assert not power_b.disabled
        assert not power_c.disabled


async def run_and_compare_type(
    expected: inverter.SungrowInverter.ConnectionMode, **kwargs
):
    data = kwargs
    data.update({"device_type_code": "x", "serial_number": "sn"})
    con = FakeConnection(data)
    async with create_inv(con) as inv:
        if inv.type != expected:
            raise AssertionError(f"Expected {expected}, got {inv.type} for {kwargs}")


@pytest.mark.asyncio()
async def test_create_inverter_detect_mode_main_standalone():
    await run_and_compare_type(
        expected=inverter.SungrowInverter.ConnectionMode.STANDALONE,
        master_slave_mode="Disabled",
        master_slave_role="Master",
    )


@pytest.mark.asyncio()
async def test_create_inverter_detect_mode_main_master():
    await run_and_compare_type(
        expected=inverter.SungrowInverter.ConnectionMode.MASTER,
        master_slave_mode="Enabled",
        master_slave_role="Master",
    )


@pytest.mark.asyncio()
async def test_create_inverter_detect_mode_main_slave1():
    await run_and_compare_type(
        expected=inverter.SungrowInverter.ConnectionMode.STANDALONE,
        master_slave_mode="Disabled",
        master_slave_role="Slave 1",
    )


@pytest.mark.asyncio()
async def test_create_inverter_detect_mode_main_slave_pure():
    await run_and_compare_type(
        expected=inverter.SungrowInverter.ConnectionMode.SLAVE,
        master_slave_mode="Enabled",
        master_slave_role="Slave 1",
        inverter_count=2,
    )


@pytest.mark.asyncio()
async def test_create_inverter_detect_mode_main_slave_1():
    await run_and_compare_type(
        expected=inverter.SungrowInverter.ConnectionMode.SLAVE_1,
        master_slave_mode="Enabled",
        master_slave_role="Slave 1",
        inverter_count=3,
    )


@pytest.mark.asyncio()
async def test_create_inverter_detect_mode_heuristic_standalone():
    await run_and_compare_type(
        expected=inverter.SungrowInverter.ConnectionMode.STANDALONE,
        output_type="2P",
    )


# Anything imported/exported -> Master
@pytest.mark.asyncio()
async def test_create_inverter_detect_mode_heuristic_master_import():
    await run_and_compare_type(
        expected=inverter.SungrowInverter.ConnectionMode.MASTER,
        total_imported_energy="1",
    )


@pytest.mark.asyncio()
async def test_create_inverter_detect_mode_heuristic_master_export():
    await run_and_compare_type(
        expected=inverter.SungrowInverter.ConnectionMode.MASTER,
        total_exported_energy="1",
    )


@pytest.mark.asyncio()
async def test_create_inverter_detect_mode_heuristic_slave():
    # No imported/exported -> Slave
    await run_and_compare_type(
        expected=inverter.SungrowInverter.ConnectionMode.SLAVE,
    )


@pytest.mark.asyncio()
async def test_create_inverter_with_minimal_signal_queries():
    # All minimal level signals are expected
    data: connection_base.DecodedSignals = {
        s.name: None
        for s in signals2.load_yaml().get_active_signals_for_level(Level.MINIMAL.value)
    }
    # These two must have actual values
    data["device_type_code"] = "x"
    data["serial_number"] = "sn"

    # TODO: These should not be queried, but they are...
    data["meter_active_power"] = None
    data["array_insulation_resistance"] = None

    async with create_inv(FakeConnection(data, only_expected=True)) as _:
        pass
