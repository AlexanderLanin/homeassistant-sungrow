"""
Test the Simple Integration config flow.

You can run this file e.g. via:
clear && pytest -k config_flow --log-cli-level=DEBUG
"""
import logging
from unittest.mock import MagicMock, patch

import aiohttp
import pytest
from beartype.claw import beartype_this_package
from homeassistant import config_entries, data_entry_flow, loader, runner, setup
from homeassistant import core as ha
from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_USER
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SLAVE,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant

from tests import e2e_setup

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.asyncio]
DOMAIN = "sungrow"
logging.basicConfig(level=logging.DEBUG)


# This will pull enable_custom_integrations into scope for all tests
@pytest.fixture(autouse=True)
def always_enable_custom_integrations(hass: HomeAssistant, enable_custom_integrations):
    yield


# This fixture bypasses the actual setup of the integration
# since we only want to test the config flow. We test the
# actual functionality of the integration in other test modules.
@pytest.fixture(autouse=True)
def bypass_setup_fixture():
    """Prevent setup."""
    with patch(
        "custom_components.sungrow.async_setup",
        return_value=True,
    ), patch(
        "custom_components.sungrow.async_setup_entry",
        return_value=True,
    ):
        yield


MOCK_CONFIG = {"host": "test_username", "ip": "test_password"}


async def test_user_is_presented_with_a_form(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_successful_config_flow(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    async with e2e_setup.simulated_inverter(
        "dump_master.yaml"
    ) as simulated_inverter_port:
        logger.debug(f"Simulated inverter started on port {simulated_inverter_port}")

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "localhost",
                CONF_PORT: simulated_inverter_port,
                CONF_SLAVE: 1,
            },
        )
        logger.debug(f"config flow result: {result}")
