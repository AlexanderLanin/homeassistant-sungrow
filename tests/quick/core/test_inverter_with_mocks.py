import logging
from unittest.mock import patch

import pytest

from custom_components.sungrow.core import inverter, modbus_base, modbus_py
from custom_components.sungrow.core.modbus_types import MappedData, Signal

logging.basicConfig(level=logging.DEBUG)
pytest_plugins = ("pytest_asyncio",)


class FakeConnection(modbus_base.ModbusConnectionBase):
    def __init__(self, data: MappedData):
        self.data = data

    async def connect(self):
        raise AssertionError("Should not be called")

    async def disconnect(self):
        raise AssertionError("Should not be called")

    # TODO: it would be easier to mock this with decoded data...!!!
    async def read(
        self, signal_list: list[Signal], _max_combined_registers=100
    ) -> MappedData:
        return {s.name: self.data[s.name] for s in signal_list}


@pytest.mark.asyncio()
async def test_create_inverter_with_mocked_modbus():
    fake_connection = FakeConnection({"ac_power": [123], "ac_current": [456]})
    fake_connection.data = {
        "model": "SG110CX",
        "serial_number": "123456789",
        "firmware_version": "1.2.3",
    }
    inv = inverter.SungrowInverter.create(fake_connection)
    assert inv is not None
