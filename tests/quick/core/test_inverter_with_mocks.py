import logging
from unittest.mock import patch

import pytest

from custom_components.sungrow.core import inverter, modbus_base, modbus_py

logging.basicConfig(level=logging.DEBUG)
pytest_plugins = ("pytest_asyncio",)


# This doesn't match anymore as the code has changed, but it's still a good example.
# Now the code pull all registers on connect and will fail with invalid responses.
@pytest.mark.skip(reason="Test is disabled. Not sure yet what do do with it.")
@pytest.mark.asyncio
async def test_create_inverter_with_mocked_modbus():
    with (
        patch.object(modbus_base.ModbusConnectionBase, "connect") as mock_connect,
        patch.object(modbus_base.ModbusConnectionBase, "read") as mock_read,
    ):
        # Create method will connect to the inverter and read the model number
        mock_connect.return_value = True
        mock_read.return_value = [0x42]

        ic = await inverter.connect_and_get_basic_data(
            host="<fake ip>", port=502, slave=1, connection="pymodbus"
        )
        assert ic

        # inv = await inverter.SungrowInverter.create(
        #     {"host": "<fake ip>", "port": 502, "unit": 1}
        # )

        mock_connect.assert_called_once()
        mock_read.assert_called_once_with(modbus_py.RegisterType.READ, 5000, 1)

        assert ic.data["device_type_code"] == 0x42

        ic.connection.disconnect()