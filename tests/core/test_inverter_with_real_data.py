"""
This is an end-to-end test that will connect to a fake inverter and pull data from it.
It's really great to test the whole stack, but (mostly) it's limited to the happy path.
"""
import logging
from pprint import pprint

import fix_path  # type: ignore  # noqa: F401
import pytest

from custom_components.sungrow.core import inverter, modbus_base
from tests.e2e_setup import e2e_setup, simulated_inverter

logging.basicConfig(level=logging.DEBUG)

# Mark all tests in this file as asyncio tests with a socket connection.
# pytest_plugins = ("pytest_asyncio")
pytestmark = [pytest.mark.asyncio, pytest.mark.enable_socket]


async def test_e2e_master():
    async with e2e_setup("dump_master.yaml", {"use_local_time": False}) as inv:
        # Dump was recorded with a SH8.0RT-20 (code 3602)
        assert inv.model in [3602, "SH8.0RT-20"]

        await inv.pull_data()

        # Dump was recorded on a master inverter with battery
        assert inv.data["has_battery"].value
        assert inv.data["is_master"].value

        assert inv.slave_master_standalone == "Master"

        pprint(inv.data.values())


async def test_e2e_slave():
    async with e2e_setup("dump_slave.yaml", {"use_local_time": False}) as inv:
        # Dump was recorded with a SH8.0RT-20 (code 3602)
        assert inv.model in [3602, "SH8.0RT-20"]

        await inv.pull_data()

        # Dump was recorded on a slave inverter without battery
        assert "has_battery" not in inv.data
        assert "is_master" not in inv.data

        assert inv.slave_master_standalone == "Slave"

        pprint(inv.data.values())


async def test_e2e_slave_unknown_model():
    async with e2e_setup(
        "slave_dump_unknown_model.yaml", {"use_local_time": False}
    ) as inv:
        # Dump was recorded with a SH8.0RT-20 (code 3602),
        # but model is manually removed from the dump.
        assert inv.model == 1

        await inv.pull_data()

        # Dump was recorded on a slave inverter without battery
        assert "has_battery" not in inv.data
        assert "is_master" not in inv.data

        pprint(inv.data.values())


async def test_e2e_fail_no_server():
    # should this really raise an exception?
    # or should it just return None? FIXME TODO
    with pytest.raises(modbus_base.CannotConnectError):
        await inverter.SungrowInverter.create(
            {"host": "localhost", "port": 500 * 1000, "slave": 1}
        )


async def test_e2e_fail_wrong_slave():
    async with simulated_inverter(None) as port:
        with pytest.raises((modbus_base.InvalidSlaveError, modbus_base.ModbusError)):
            print("creating inverter...")
            await inverter.SungrowInverter.create(
                # Note: simulation runs with slave 1
                {"host": "localhost", "port": port, "slave": 2}
            )


async def test_e2e_timestamp_removes_raw_values():
    async with e2e_setup(
        "dump_master.yaml", {"use_local_time": False, "level": 3}
    ) as inv:
        await inv.pull_data()

        assert inv.data["timestamp"].value
        for key in ["year", "month", "day", "hour", "minute", "second"]:
            assert key not in inv.data, f"key {key} should not be in data"

    async with e2e_setup(
        "dump_master.yaml", {"use_local_time": True, "level": 3}
    ) as inv:
        await inv.pull_data()

        assert inv.data["timestamp"].value
        for key in ["year", "month", "day", "hour", "minute", "second"]:
            assert key not in inv.data, f"key {key} should not be in data"
