"""
Test the Simple Integration config flow.

You can run this file e.g. via:
clear && pytest -k config_flow --log-cli-level=DEBUG
"""
import logging
from unittest.mock import patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SLAVE,
)
from homeassistant.core import HomeAssistant

from custom_components.sungrow.core.inverter import InitialConnection
from tests import e2e_setup

pytestmark = [pytest.mark.asyncio]
DOMAIN = "sungrow"

# log everything... except pymodbus
logging.basicConfig(level=logging.INFO)
logging.getLogger("pymodbus").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
async def always_enable_custom_integrations(
    hass: HomeAssistant, enable_custom_integrations
):
    """Pull our sungrow integration into the test environment."""
    # Integration has been enabled by enable_custom_integrations fixture.
    yield


@pytest.fixture(autouse=True)
def bypass_setup_fixture():
    """Prevent actual setup of the integration, so these tests run faster."""
    with patch(
        "custom_components.sungrow.async_setup",
        return_value=True,
    ), patch(
        "custom_components.sungrow.async_setup_entry",
        return_value=True,
    ):
        yield


@pytest.fixture(autouse=True)
async def cleanup_lingering_inverter_connections(hass: HomeAssistant):
    yield
    # Unfortunately tests here are not even aware of any connection, as it's internal
    # to the config_flow.
    # Fortunately the connection is stored in the global hass object, so we can
    # access it from here.
    if DOMAIN in hass.data:
        for ic in hass.data[DOMAIN]["inverters"].values():
            assert isinstance(ic, InitialConnection)
            if ic.connection:
                await ic.connection.disconnect()


async def start_config_flow(hass: HomeAssistant) -> str:
    """Returns flow_id for the newly started config flow."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}
    assert isinstance(result["flow_id"], str)
    return result["flow_id"]


async def test_non_responding_inverter(hass: HomeAssistant):
    flow_id = await start_config_flow(hass)

    async with e2e_setup.simulated_inverter(None) as simulated_inverter_port:
        result = await hass.config_entries.flow.async_configure(
            flow_id,
            user_input={
                CONF_HOST: "localhost",
                CONF_PORT: simulated_inverter_port,
                CONF_SLAVE: 0,
            },
        )
        # TODO: is this translated correctly with the string only starting
        # with "cannot_connect"?
        # assert result["errors"]["base"] == "cannot_connect"
        assert result["errors"]["base"].startswith("cannot_connect")


async def test_successful_config_flow_only(hass: HomeAssistant, bypass_setup_fixture):
    flow_id = await start_config_flow(hass)

    async with e2e_setup.simulated_inverter(
        "dump_master.yaml"
    ) as simulated_inverter_port:
        logger.debug(f"Simulated inverter started on port {simulated_inverter_port}")

        result = await hass.config_entries.flow.async_configure(
            flow_id,
            user_input={
                CONF_HOST: "localhost",
                CONF_PORT: simulated_inverter_port,
                CONF_SLAVE: 0,  # TODO: what exactly is vol.Optional passing when empty?
            },
        )

        # Flow finished successfully
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert not result.get("errors")
