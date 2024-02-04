"""
Test the Simple Integration config flow.

You can run this file e.g. via:
clear && pytest -k config_flow_e2e --log-cli-level=DEBUG
"""
import logging

import pytest
from homeassistant import data_entry_flow
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

    async with e2e_setup.simulate_modbus_inverter(
        "dump_master.yaml"
    ) as simulated_inverter_port:
        logger.debug(f"Simulated inverter started on port {simulated_inverter_port}")

        # Provide valid config flow input
        result = await hass.config_entries.flow.async_configure(
            flow_id,
            user_input={
                CONF_HOST: "127.0.0.1",
                CONF_PORT: simulated_inverter_port,
                CONF_SLAVE: 0,  # TODO: what exactly is vol.Optional passing when empty?
            },
        )
        # Flow finished successfully
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert not result.get("errors")

        # Device has been created
        sn = next(iter(hass.data[DOMAIN]["inverters"]))
        dr = device_registry.async_get(hass)
        device = dr.async_get_device(
            identifiers={(DOMAIN, sn)},
        )
        assert device

        # Sensor entities have been created
        er = entity_registry.async_get(hass)
        assert len(er._entities_data) > 30
