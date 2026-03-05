import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from .const import DOMAIN, CONF_PUPIL_ID

class ClassChartsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Class Charts."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step where the user enters their credentials."""
        errors = {}

        if user_input is not None:
            # Here you could add a 'test_login' function to verify 
            # credentials before saving!
            return self.async_create_entry(
                title=user_input[CONF_EMAIL], 
                data=user_input
            )

        # This defines the form the user sees in the UI
        data_schema = vol.Schema({
            vol.Required(CONF_EMAIL): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Required(CONF_PUPIL_ID): str,
        })

        return self.async_show_form(
            step_id="user", 
            data_schema=data_schema, 
            errors=errors
        )
from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol

# Add these constants if they aren't in your const.py yet
CONF_REFRESH_INTERVAL = "refresh_interval"
CONF_DAYS_TO_FETCH = "days_to_fetch"

class ClassChartsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    # ... your existing async_step_user code here ...

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ClassChartsOptionsFlowHandler(config_entry)

class ClassChartsOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle the options menu (Settings -> Configure)."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Build the settings form
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_REFRESH_INTERVAL, 
                    default=self.config_entry.options.get(CONF_REFRESH_INTERVAL, 24)
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=24)),
                vol.Optional(
                    CONF_DAYS_TO_FETCH, 
                    default=self.config_entry.options.get(CONF_DAYS_TO_FETCH, 7)
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=14)),
            })
        )
