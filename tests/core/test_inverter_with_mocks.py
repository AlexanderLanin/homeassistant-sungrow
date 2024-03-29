import logging
from unittest.mock import patch

import pytest

from custom_components.sungrow.core import inverter, modbus

logging.basicConfig(level=logging.DEBUG)
pytest_plugins = ("pytest_asyncio",)


# This doesn't match anymore as the code has changed, but it's still a good example.
# Now the code pull all registers on connect and will fail with invalid responses.
@pytest.mark.asyncio
async def te_st_create_inverter_with_mocked_modbus():
    with (
        patch.object(modbus.Connection, "connect") as mock_connect,
        patch.object(modbus.Connection, "read") as mock_read,
    ):
        # Create method will connect to the inverter and read the model number
        mock_connect.return_value = True
        mock_read.return_value = [0x42]

        inv = await inverter.SungrowInverter.create(
            {"host": "<fake ip>", "port": 502, "unit": 1}
        )

        mock_connect.assert_called_once()
        mock_read.assert_called_once_with(modbus.RegisterType.READ, 5000, 1)

        assert inv.model == 0x42
