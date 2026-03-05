import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from .const import DOMAIN, CONF_PUPIL_ID

class ClassChartsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Class Charts."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Initial setup step."""
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
        """This is what makes the 'COG' appear."""
        return ClassChartsOptionsFlowHandler(config_entry)

class ClassChartsOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle the settings menu."""
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("days_to_fetch", default=7): int,
                vol.Optional("refresh_interval", default=24): int,
            })
        )
