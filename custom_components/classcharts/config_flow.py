"""The Class Charts integration."""
import logging
import asyncio
import aiohttp
import urllib.parse
import voluptuous as vol
import re  # Added for parsing the pupil HTML elements cleanly

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback

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
        """Step 1: Capture credentials using your exact imported constants."""
        errors = {}

        if user_input is not None:
            # Explicitly extract using your core constants to avoid key mismatches
            students = await self._discover_students(
                user_input[CONF_EMAIL], 
                user_input[CONF_PASSWORD]
            )

            if students:
                self.discovered_students = students
                # Save the input to memory using explicit raw string keys for Step 2
                self.login_data = {
                    "email": user_input[CONF_EMAIL],
                    "password": user_input[CONF_PASSWORD]
                }
                
                return await self.async_step_select_student()
            else:
                errors["base"] = "invalid_auth"

        # Fix the form presentation to use your exact imported const variables
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
                CONF_EMAIL: self.login_data["email"],
                CONF_PASSWORD: self.login_data["password"],
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
        """Authenticate using an isolated session container to hold validation cookies firmly."""
        
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
                # FORCE a fresh standalone client session context manager
                async with aiohttp.ClientSession() as session:
                    
                    # Submit the core login wrapper handshake
                    async with session.post(
                        NEW_LOGIN_URL, 
                        data=encoded_payload, 
                        headers=headers, 
                        allow_redirects=False
                    ) as response:
                        
                        if response.status == 302 and "parent_session_credentials" in response.cookies:
                            _LOGGER.info("Auth successful. Stepping into dashboard discovery...")
                            
                            # Use the exact same private session container to execute dashboard reads
                            async with session.get(PARENT_DASHBOARD_URL, headers=headers) as dash_response:
                                html_content = await dash_response.text()
                                
                                # 1. Broad match: Look for standard profile link anchor structures
                                student_matches = re.findall(r'href="[^"]*/parent/student/(\d+)"[^>]*>([^<]+)</a>', html_content)
                                
                                # 2. Secondary check: Look for select dropdown options containing numeric IDs
                                if not student_matches:
                                    student_matches = re.findall(r'value="(\d+)"[^>]*>([^<]+)</option>', html_content)
                                    
                                # 3. Ultimate Fallback: Target raw data-id attributes used by modern JavaScript elements
                                if not student_matches:
                                    raw_ids = re.findall(r'data(?:-student)?-id=["\'](\d+)["\']', html_content)
                                    if raw_ids:
                                        student_matches = [(uid, f"Student Profile ({uid})") for uid in set(raw_ids)]

                                if student_matches:
                                    # Build a clean dict: {"123456": "Jack", "789012": "Emily"}
                                    found_kids = {str(uid): name.strip() for uid, name in student_matches if "Log out" not in name and "Select" not in name}
                                    _LOGGER.info("Discovered Class Charts children: %s", found_kids)
                                    return found_kids
                                
                                _LOGGER.error("Authenticated successfully, but could not parse any children from the dashboard view layout.")
                                return {}
                        else:
                            _LOGGER.error(
                                "Login handshake dropped. Status code returned: %s. Cookies caught: %s", 
                                response.status, 
                                list(response.cookies.keys())
                            )
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
