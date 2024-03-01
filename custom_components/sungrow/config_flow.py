import logging
from typing import Any

import voluptuous as vol  # type: ignore
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SLAVE
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from custom_components.sungrow.core import modbus_base

from .const import DOMAIN
from .core.inverter import connect_and_get_basic_data, slave_master_standalone_str

logger = logging.getLogger(__name__ + " @ ")


class SungrowInverterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Sungrow Inverter config flow."""

    VERSION = 1

    async def _async_show_user_form(
        self, user_input: dict[str, Any], errors: dict[str, str]
    ):
        # TODO: define CONFIG_SCHEMA, see https://github.com/home-assistant/core/pull/93587
        schema = {
            vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "")): str,
            vol.Optional(CONF_PORT, default=user_input.get(CONF_PORT, "")): int,
            vol.Optional(CONF_SLAVE, default=user_input.get(CONF_SLAVE, "")): int,
            vol.Optional(
                "connection", default=user_input.get("connection", "auto")
            ): SelectSelector(
                SelectSelectorConfig(
                    options=["auto", "modbus", "http"], translation_key="connection"
                )
            ),
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema),
            errors=errors,
        )

    async def async_step_user(self, user_input=None):
        """Currently it's all in one step"""

        # New config flow. Just show the form.
        if user_input is None:
            return await self._async_show_user_form({}, {})

        # TODO: schema has two ways of specifying defaults. Which one is better?
        host: str = user_input[CONF_HOST]
        port: int = user_input[CONF_PORT]
        slave: int = user_input[CONF_SLAVE]
        connection: str | None = (
            None if user_input["connection"] == "auto" else user_input["connection"]
        )

        try:
            ic = await connect_and_get_basic_data(host, port, slave, connection)
            if ic:
                logger.debug(f"Connected to inverter: {ic.data}")

                # Store the inverter in hass.data, so we can access it from the sensor
                # platform without establishing a new connection.
                self.hass.data.setdefault(DOMAIN, {"inverters": {}})
                self.hass.data[DOMAIN]["inverters"][ic.data["serial_number"]] = ic

                # We need to pass the serial number to the sensor platform,
                # otherwise it won't know which connection to use.
                # data will be stored persistently in the config entry.
                # So we want to keep it as small as possible.
                data = dict(user_input)
                data["serial_number"] = ic.data["serial_number"]

                logger.debug(f"Calling async_create_entry({data})")
                return self.async_create_entry(
                    # Note: name can be changed in the UI!
                    title="Sungrow Inverter " + slave_master_standalone_str(ic.data),
                    data=data,
                    # TODO: description=f"Found inverter {inverter.serial_number}", etc
                )
            else:
                logger.debug("Cannot connect to inverter")
                return await self._async_show_user_form(
                    user_input, {"base": "cannot_connect"}
                )
        except modbus_base.ModbusError as e:
            logger.debug(f"Cannot connect to inverter: {e}")
            return await self._async_show_user_form(
                user_input, {"base": f"cannot_connect: {e}"}
            )
