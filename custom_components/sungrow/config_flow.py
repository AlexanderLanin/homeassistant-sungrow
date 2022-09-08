"""Sungrow Inverter config flow."""
from __future__ import annotations

import logging
from typing import Any
from pprint import pformat

import voluptuous as vol

from .sungather import SungrowInverter

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigFlow
from homeassistant.helpers.selector import selector

from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TIMEOUT,
    CONF_SLAVE
)

from .const import DOMAIN, DEFAULT_NAME

logger = logging.getLogger(__name__)

# This is the schema that used to display the UI to the user.
# TODO add CONF_SCAN_INTERVAL
DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_PORT, default=8082): int,
    vol.Required(CONF_TIMEOUT, default=3): int,
    vol.Required(CONF_SLAVE, default=0x01): int,
    vol.Required("connection", default='http'): selector({
        "select": {
            "options": ["http", "modbus", "sungrow"],
        }
    }),
    vol.Optional("model"): str,
    vol.Optional("use_local_time"): bool,
    vol.Optional("smart_meter"): bool,
    vol.Optional("level", default=3): int
})


class SungrowInverterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Sungrow Inverter config flow."""

    VERSION = 1

    async def validate_input(self, hass: HomeAssistant, config: dict = None) -> dict[str, Any]:
        """Validate the user input allows us to connect.
        Data has the keys from DATA_SCHEMA with values provided by the user.
        """

        logger.debug(f'validate_input config={pformat(config)}')

        # Accumulate validation errors. Key is name of field from DATA_SCHEMA
        errors = {}

        if not config:
            logger.debug(f'validate_input returning None due to no config')
            return None

        # Validate the data can be used to set up a connection.
        logger.debug(f'validate_input creating SungrowInverter')
        inverter: SungrowInverter = SungrowInverter(config)
        logger.debug(f'validate_input inverter={inverter}')
        
        # TODO
        # registersfile = yaml.safe_load(open('registers-sungrow.yaml', encoding="utf-8"))
        # inverter.configure_registers(registersfile)

        is_success = inverter.connect()
        # inverter.close()
        logger.debug(
            f'validate_input inverter.connect() is_success={is_success}')
        if not is_success:
            errors['base'] = 'cannot_connect'

        logger.debug(f'validate_input errors={pformat(errors)}')

        # Return info that you want to store in the config entry.
        # "Title" is what is displayed to the user for this hub device
        # It is stored internally in HA as part of the device config.
        # See `async_step_user` below for how this is used
        return errors

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""

        logger.debug(f'async_step_user user_input={pformat(user_input)}')

        if not user_input:
            logger.debug('async_step_user displaying user data entry form')
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)
        else:
            # Both info and errors are None when config flow is first invoked
            errors = await self.validate_input(self.hass, user_input)

            logger.debug(f'async_step_user errors={pformat(errors)}')

            if not errors or not len(errors.keys()):
                logger.debug(f'async_step_user calling async_create_entry')
                return self.async_create_entry(title=DEFAULT_NAME, data=user_input)
            else:
                # If there is no user input or there were errors, show the form again,
                # including any errors that were found with the input.
                logger.debug(
                    f'async_step_user calling async_show_form step_id="user"')
                return self.async_show_form(
                    step_id="user", data_schema=DATA_SCHEMA, errors=errors
                )
