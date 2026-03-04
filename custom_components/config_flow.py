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
