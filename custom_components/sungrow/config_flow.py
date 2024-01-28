import logging
from typing import Any

import voluptuous as vol  # type: ignore
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SLAVE
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from custom_components.sungrow.core import modbus_base

from .const import DOMAIN
from .core.inverter import connect_and_get_basic_data, slave_master_standalone_str

logger = logging.getLogger(__name__)


class SungrowInverterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Sungrow Inverter config flow."""

    VERSION = 1

    async def _async_show_user_form(
        self, user_input: dict[str, Any], errors: dict[str, str]
    ):
        schema = {
            vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "")): str,
            vol.Optional(CONF_PORT, default=user_input.get(CONF_PORT, "")): int,
            vol.Optional(CONF_SLAVE, default=user_input.get(CONF_SLAVE, "")): int,
            vol.Optional(
                "connection", default=user_input.get("connection", "modbus")
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

        try:
            async with await connect_and_get_basic_data(
                user_input[CONF_HOST],
                user_input[CONF_PORT],
                user_input[CONF_SLAVE],
                user_input["connection"],
            ) as ic:
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

                return self.async_create_entry(
                    # Note: name can be changed in the UI!
                    title="Sungrow Inverter "
                    + slave_master_standalone_str(ic.data),
                    data=data,
                    # TODO: description=f"Found inverter {inverter.serial_number}", etc
                )
        except modbus_base.ModbusError as e:
            logger.debug(f"Cannot connect to inverter: {e}")
            errors = {"base": f"cannot_connect: {e}"}
            return await self._async_show_user_form(user_input, errors)
