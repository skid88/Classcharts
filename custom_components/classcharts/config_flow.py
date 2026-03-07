import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_PUPIL_ID,
    CONF_REFRESH_INTERVAL,
    CONF_DAYS_TO_FETCH,
)

class ClassChartsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Class Charts."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_EMAIL], 
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_PUPIL_ID): str,
            }),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Link the options flow to the config flow."""
        return ClassChartsOptionsFlowHandler(config_entry)


class ClassChartsOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Class Charts settings."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
    
        # The base class (OptionsFlow) handles it.
        super().__init__()

    async def async_step_init(self, user_input=None):
        """Manage the actual settings menu."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Access config_entry through the property provided by the base class
        options = self.config_entry.options

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_REFRESH_INTERVAL,
                    default=options.get(CONF_REFRESH_INTERVAL, 24),
                ): int,
                vol.Optional(
                    CONF_DAYS_TO_FETCH,
                    default=options.get(CONF_DAYS_TO_FETCH, 14),
                ): int,
            }),
        )
