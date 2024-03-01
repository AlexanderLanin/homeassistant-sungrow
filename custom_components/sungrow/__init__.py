import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation

from .const import DOMAIN

logger = logging.getLogger(__name__)

# TODO: see https://github.com/home-assistant/core/pull/93587
CONFIG_SCHEMA = config_validation.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict):
    """
    Set up the Sungrow inverter component.

    Note: the very first config_flow is executed before this function is called!!
    """
    logger.warning(f"async_setup(config={config})")

    # We'll be storing connections to our inverter(s) in hass.data.
    # That's so we can pass them from the config flow to the sensor platform.
    hass.data.setdefault(DOMAIN, {"inverters": {}})

    # We don't need to do anything here, since we'll be setting up
    # our inverter(s) in async_setup_entry, which gets called later on
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Entry point to instantiate an inverter, based on a config."""

    # TODO: this is also called on "reload"! In that case it fails!
    # Maybe because unload didn't do its job?

    logger.debug(f"async_setup_entry(entry={entry})")

    # We'll be collecting some persistent data in hass.data
    hass.data.setdefault(DOMAIN, {})

    # Forward the setup to the sensor platform (sensor.py)
    return await hass.config_entries.async_forward_entry_setup(entry, Platform.SENSOR)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entry point to delete an inverter, based on a config."""

    logger.debug(f"async_unload_entry(entry={entry})")

    # Forward the unloading to the sensor platform (sensor.py)
    return await hass.config_entries.async_unload_platforms(entry, Platform.SENSOR)
    return await hass.config_entries.async_unload_platforms(entry, Platform.SENSOR)
