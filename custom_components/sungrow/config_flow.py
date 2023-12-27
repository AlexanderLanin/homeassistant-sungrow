import logging
from pprint import pformat
from typing import Any

import voluptuous as vol  # type: ignore
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SLAVE, CONF_TIMEOUT
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .const import DOMAIN
from .core.inverter import SungrowInverter

logger = logging.getLogger(__name__)


class SungrowInverterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Sungrow Inverter config flow."""

    VERSION = 1

    async def _async_show_user_form(
        self, user_input: dict[str, Any], errors: dict[str, str]
    ):
        logger.debug(
            "async_step_user displaying user data entry form "
            + f"with user_input={user_input} and errors={errors}"
        )

        schema = {
            vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "")): str,
            vol.Required(CONF_PORT, default=user_input.get(CONF_PORT, 8082)): int,
            vol.Required(CONF_TIMEOUT, default=user_input.get(CONF_TIMEOUT, 3)): int,
            vol.Required(CONF_SLAVE, default=user_input.get(CONF_SLAVE, 1)): int,
            vol.Required(
                "connection", default=user_input.get("connection", "modbus")
            ): SelectSelector(
                SelectSelectorConfig(
                    options=["modbus", "sungrow", "http"], translation_key="connection"
                )
            ),
            vol.Optional("model", default=user_input.get("model", "")): str,
            vol.Optional(
                "use_local_time",
                default=user_input.get("use_local_time", False),
            ): bool,
            vol.Optional(
                "smart_meter", default=user_input.get("smart_meter", False)
            ): bool,
            vol.Optional("level", default=user_input.get("level", 2)): int,
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema),
            errors=errors,
        )

    async def async_step_user(self, user_input=None):
        """Initial configuration step
        Either show config data entry form to the user, or create a config entry.
        """

        logger.debug(f"async_step_user user_input={pformat(user_input)}")

        # Either show modal form, or create config entry then move on
        if not user_input:  # Just show the modal form and return if no user input
            return await self._async_show_user_form(user_input, {})
        else:  # We got user input, so do something with it
            # Validate inputs and do a test connection/scrape of the inverter
            # Both info and errors are None when config flow is first invoked
            inverter = await SungrowInverter.create(user_input)
            if inverter:
                # ToDo: pass inverter object to async_create_entry, so we don't have to
                # disconnect and connect again
                await inverter.disconnect()
                return self.async_create_entry(
                    title="Sungrow Inverter", data=user_input
                )
            else:
                # FIXME: more precise error
                errors = {"base": "cannot_connect"}
                return await self._async_show_user_form(user_input, errors)
