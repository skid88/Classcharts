import logging
import asyncio
import aiohttp
import urllib.parse
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
    CONF_SHOW_NO_SCHOOL
)

_LOGGER = logging.getLogger(__name__)

# Target the updated web portal auth route
NEW_LOGIN_URL = "https://www.classcharts.com/parent/login"

class ClassChartsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Class Charts."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step where the user enters credentials."""
        errors = {}

        if user_input is not None:
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
        """Return true if credentials match the new cookie-based system architecture."""
        session = async_get_clientsession(self.hass)
        
        # Mirror the precise browser footprint to slip through Cloudflare protections
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
            "Origin": "https://www.classcharts.com",
            "Referer": "https://www.classcharts.com/",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Build the exact query structure used by the new web portal client
        payload = {
            "_method": "POST",
            "email": email,
            "logintype": "existing",
            "password": password,
            "recaptcha-token": "no-token-available"
        }
        
        # Enforce application/x-www-form-urlencoded string generation
        encoded_payload = urllib.parse.urlencode(payload)

        try:
            async with asyncio.timeout(10):
                # CRITICAL: allow_redirects=False captures the 302 sequence before aiohttp discards cookies
                async with session.post(
                    NEW_LOGIN_URL, 
                    data=encoded_payload, 
                    headers=headers, 
                    allow_redirects=False
                ) as response:
                    
                    if response.status == 302:
                        # Inspect the active cookie headers for authentication clearance
                        cookies = [val for header, val in response.raw_headers if header.lower() == b"set-cookie"]
                        cookie_string = "".join([c.decode("utf-8", errors="ignore") for c in cookies])
                        
                        if "parent_session_credentials" in cookie_string:
                            return True
                            
                    _LOGGER.error("Authentication handshake rejected. HTTP Status: %s", response.status)
                    return False
                    
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("Timeout or connection error connecting to Class Charts: %s", err)
            return False
        except Exception as err:
            _LOGGER.exception(f"Unexpected error inside config validation flow: {err}")
            return False

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Link the options flow to the config flow."""
        return ClassChartsOptionsFlowHandler()


class ClassChartsOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Class Charts settings."""

    async def async_step_init(self, user_input=None):
        """Manage the actual settings menu."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

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
                vol.Optional(
                    "show_completed_homework",
                    default=options.get("show_completed_homework", True),
                ): bool,
                vol.Optional(
                    CONF_SHOW_NO_SCHOOL,
                    default=self.config_entry.options.get(CONF_SHOW_NO_SCHOOL, True),
                ): bool,
            }),
        )
