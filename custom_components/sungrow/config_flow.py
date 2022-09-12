"""Sungrow Inverter config flow."""
from __future__ import annotations

import logging
from typing import Any
from pprint import pformat
import pathlib, yaml, os

import voluptuous as vol

from .SunGather.inverter import SungrowInverter

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
    vol.Optional("level", default=2): int
})


class SungrowInverterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Sungrow Inverter config flow."""

    VERSION = 1

    async def validate_input(self, hass: HomeAssistant, config_inverter: dict = None) -> dict[str, Any]:
        """Validate the user input allows us to connect.
        Data has the keys from DATA_SCHEMA with values provided by the user.
        """

        logger.debug(f'validate_input config_inverter={pformat(config_inverter)}')

        # Accumulate validation errors. Key is name of field from DATA_SCHEMA
        errors = {}

        if not config_inverter:
            logger.debug(f'validate_input returning None due to no config')
            return None

        # Validate the data can be used to set up a connection.
        logger.debug(f'validate_input creating SungrowInverter')
        # inverter: SungrowInverter = SungrowInverter(config)
        # logger.debug(f'validate_input inverter={inverter}')
        
        # TODO
        # registersfile = yaml.safe_load(open('registers-sungrow.yaml', encoding="utf-8"))
        # inverter.configure_registers(registersfile)

        # is_connect_success = inverter.checkConnection()
        # pwd = pathlib.Path(__file__).parent.absolute()
        # registersfile = yaml.safe_load(
        #     open(os.path.join(pwd, 'registers-sungrow.yaml'), encoding="utf-8"))
        # inverter.configure_registers(registersfile)

        # Async construct inverter object
        def create_inverter():
            pwd = pathlib.Path(__file__).parent.absolute()
            registersfile = yaml.safe_load(
                open(os.path.join(pwd, 'registers-sungrow.yaml'), encoding="utf-8"))
            inverter = SungrowInverter(config_inverter)
            if not inverter.checkConnection():
                logger.error(
                    f"Error: Connection to inverter failed: {config_inverter.get('host')}:{config_inverter.get('port')}")
            inverter.configure_registers(registersfile)
            if not inverter.inverter_config['connection'] == "http":
                inverter.close()
            return inverter
        inverter: SungrowInverter = await hass.async_add_executor_job(create_inverter)
        logger.debug(f'validate_input inverter={inverter}')

        is_success = await hass.async_add_executor_job(lambda: inverter.scrape())

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
        return (errors, inverter)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""

        logger.debug(f'async_step_user user_input={pformat(user_input)}')

        if not user_input:
            logger.debug('async_step_user displaying user data entry form')
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)
        else:

            # Both info and errors are None when config flow is first invoked
            errors, inverter = await self.validate_input(self.hass, user_input)

            logger.debug(f'async_step_user errors={pformat(errors)}')

            if not errors or not len(errors.keys()):
                unique_id = inverter.latest_scrape.get('serial_number')
                logger.debug(f'async_step_user assigning unique_id {unique_id}')
                self._abort_if_unique_id_configured(updates={CONF_HOST: user_input[CONF_HOST]})
                await self.async_set_unique_id(unique_id)

                logger.debug(f'async_step_user calling async_create_entry with unique_id {unique_id}')
                return self.async_create_entry(title=DEFAULT_NAME, data=user_input)
            else:
                # If there is no user input or there were errors, show the form again,
                # including any errors that were found with the input.
                logger.debug(
                    f'async_step_user calling async_show_form step_id="user"')
                return self.async_show_form(
                    step_id="user", data_schema=DATA_SCHEMA, errors=errors
                )
