import logging
import aiohttp
import asyncio
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_PUPIL_ID,
    CONF_REFRESH_INTERVAL,
    CONF_DAYS_TO_FETCH,
    LOGIN_URL,  # Ensure this is defined in your const.py
)

_LOGGER = logging.getLogger(__name__)

class ClassChartsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Class Charts."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step where the user enters credentials."""
        errors = {}

        if user_input is not None:
            # 1. Test the credentials against the actual API
            is_valid = await self._test_credentials(
                user_input[CONF_EMAIL], 
                user_input[CONF_PASSWORD]
            )

            if is_valid:
                return self.async_create_entry(
                    title=user_input[CONF_EMAIL], 
                    data=user_input
                )
            else:
                # 2. This key "invalid_auth" must exist in your en.json
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_PUPIL_ID): str,
            }),
            errors=errors,
        )

    async def _test_credentials(self, email, password):
        """Return true if credentials are valid by hitting the API."""
        # Use the Home Assistant shared session (Best Practice)
        session = async_get_clientsession(self.hass)
        payload = {"email": email, "password": password}

        try:
            async with asyncio.timeout(10):
                async with session.post(LOGIN_URL, data=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Adjust "success" based on the actual Class Charts API response keys
                        return data.get("success", False) or "token" in data
                    return False
        except (aiohttp.ClientError, asyncio.TimeoutError):
            _LOGGER.error("Timeout or connection error connecting to Class Charts")
            return False
        except Exception as err:
            _LOGGER.exception(f"Unexpected error: {err}")
            return False

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Link the options flow to the config flow."""
        return ClassChartsOptionsFlowHandler(config_entry)


class ClassChartsOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Class Charts settings."""

    # REMOVE THE __init__ ENTIRELY
    # The base class now handles everything automatically.

    async def async_step_init(self, user_input=None):
        """Manage the actual settings menu."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Use self.config_entry (it is provided by the base class)
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
