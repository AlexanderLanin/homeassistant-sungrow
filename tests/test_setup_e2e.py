"""
Test the Simple Integration config flow.

You can run this file e.g. via:
clear && pytest -k config_flow_e2e --log-cli-level=DEBUG
"""
import logging

import pytest
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SLAVE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, entity_registry

from tests import e2e_setup
from tests.test_config_flow import (
    always_enable_custom_integrations,  # noqa: F401
    cleanup_lingering_inverter_connections,  # noqa: F401
    start_config_flow,
)

pytestmark = [pytest.mark.asyncio]
DOMAIN = "sungrow"

# log everything... except pymodbus
logging.basicConfig(level=logging.INFO)
logging.getLogger("pymodbus").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def test_successful_config_flow_e2e_up_to_sensor_entities(hass: HomeAssistant):
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
        # Note: this will go through the entire config flow, including entry creation
        # via async_setup and async_setup_entry.
        assert result.get("errors") is None
        logger.debug(f"config flow result: {result}")

        sn = next(iter(hass.data[DOMAIN]["inverters"]))
        dr = device_registry.async_get(hass)
        device = dr.async_get_device(
            identifiers={(DOMAIN, sn)},
        )
        assert device

        er = entity_registry.async_get(hass)
        # ~40 sensors created
        assert len(er._entities_data) > 30
