import logging
import asyncio
import aiohttp
import urllib.parse
import voluptuous as vol
import re  # Added for parsing the pupil HTML elements cleanly

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

NEW_LOGIN_URL = "https://www.classcharts.com/parent/login"
PARENT_DASHBOARD_URL = "https://www.classcharts.com/parent/"

class ClassChartsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a multi-step config flow for Class Charts."""

    VERSION = 1

    def __init__(self):
        """Initialize the multi-step memory structures."""
        self.login_data = {}
        self.discovered_students = {}

    async def async_step_user(self, user_input=None):
        """Step 1: Capture credentials and discover linked children."""
        errors = {}

        if user_input is not None:
            # Test credentials and fetch the student list using the active session
            students = await self._discover_students(
                user_input[CONF_EMAIL], 
                user_input[CONF_PASSWORD]
            )

            if students:
                self.discovered_students = students
                self.login_data = user_input
                
                # Move seamlessly to Step 2
                return await self.async_step_select_student()
            else:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )

    async def async_step_select_student(self, user_input=None):
        """Step 2: Present a clean dropdown list of children."""
        errors = {}

        if user_input is not None:
            selected_id = user_input["student_selection"]
            student_name = self.discovered_students[selected_id]

            # Merge the original login info with our newly selected pupil details
            final_data = {
                CONF_EMAIL: self.login_data[CONF_EMAIL],
                CONF_PASSWORD: self.login_data[CONF_PASSWORD],
                CONF_PUPIL_ID: selected_id,
                "student_name": student_name,
            }

            return self.async_create_entry(
                title=f"Class Charts ({student_name})", 
                data=final_data
            )

        # Map the dictionary keys into the voluptuous dynamic dropdown selector
        return self.async_show_form(
            step_id="select_student",
            data_schema=vol.Schema({
                vol.Required("student_selection"): vol.In(self.discovered_students)
            }),
            errors=errors,
        )

    async def _discover_students(self, email, password):
        """Authenticate and scrape the active session dashboard for linked student IDs."""
        session = async_get_clientsession(self.hass)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
            "Origin": "https://www.classcharts.com",
            "Referer": "https://www.classcharts.com/",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        payload = {
            "_method": "POST",
            "email": email,
            "logintype": "existing",
            "password": password,
            "recaptcha-token": "no-token-available"
        }
        
        encoded_payload = urllib.parse.urlencode(payload)

        try:
            async with asyncio.timeout(10):
                # Submit the core login wrapper handshake
                async with session.post(
                    NEW_LOGIN_URL, 
                    data=encoded_payload, 
                    headers=headers, 
                    allow_redirects=False
                ) as response:
                    
                    if response.status == 302 and "parent_session_credentials" in response.cookies:
                        _LOGGER.info("Auth successful. Stepping into dashboard discovery...")
                        
                        # Use the exact same active cookie jar to call the dashboard page
                        async with session.get(PARENT_DASHBOARD_URL, headers=headers) as dash_response:
                            html_content = await dash_response.text()
                            
                            # Regex patterns looking for standard child account switch configurations 
                            # (Matches typical dashboard URL endpoints: /parent/student/123456 or elements containing data strings)
                            student_matches = re.findall(r'href="[^"]*/parent/student/(\d+)"[^>]*>([^<]+)</a>', html_content)
                            
                            if not student_matches:
                                # Fallback match group if they handle the child selection elements via data attributes or dropdown options
                                student_matches = re.findall(r'value="(\d+)"[^>]*>([^<]+)</option>', html_content)

                            if student_matches:
                                # Build a clean dict: {"123456": "Jack", "789012": "Emily"}
                                found_kids = {str(uid): name.strip() for uid, name in student_matches if "Log out" not in name}
                                _LOGGER.info("Discovered Class Charts children: %s", found_kids)
                                return found_kids
                            
                            _LOGGER.error("Authenticated successfully, but could not parse any children from the dashboard view layout.")
                            return {}
                    else:
                        _LOGGER.error("Login redirected or failed without validating session cookie structures.")
                        return {}
                        
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("Connection or timeout error while running student discovery: %s", err)
            return {}
        except Exception as err:
            _LOGGER.exception(f"Unexpected crash during child array discovery sequence: {err}")
            return {}

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
                    default=options.get(CONF_SHOW_NO_SCHOOL, True),
                ): bool,
            }),
        )
