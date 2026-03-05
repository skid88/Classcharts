import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from .const import DOMAIN, CONF_PUPIL_ID

class ClassChartsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Class Charts."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Initial setup."""
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
            })
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Create the options flow."""
        return ClassChartsOptionsFlowHandler()  # <-- No config_entry passed here anymore!

class ClassChartsOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle the settings menu."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # In modern HA, self.config_entry is already available automatically
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    "days_to_fetch", 
                    default=self.config_entry.options.get("days_to_fetch", 7)
                ): int,
                vol.Optional(
                    "refresh_interval", 
                    default=self.config_entry.options.get("refresh_interval", 24)
                ): int,
            })
        )
