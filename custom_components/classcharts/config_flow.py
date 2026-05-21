"""The Class Charts integration."""
import logging
import asyncio
import json
import aiohttp
import urllib.parse
import voluptuous as vol

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
        """Authenticate and poll the internal JSON APIs directly for pupil lists."""
        
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
                async with aiohttp.ClientSession() as session:
                    
                    # Submit the core login wrapper handshake
                    async with session.post(
                        NEW_LOGIN_URL, 
                        data=encoded_payload, 
                        headers=headers, 
                        allow_redirects=False
                    ) as response:
                        
                        if response.status == 302 and "parent_session_credentials" in response.cookies:
                            _LOGGER.info("Auth successful. Querying Class Charts Pupil API endpoints...")
                            
                            # Standard AJAX headers to negotiate JSON responses cleanly
                            api_headers = {
                                **headers,
                                "Accept": "application/json, text/plain, */*",
                                "X-Requested-With": "XMLHttpRequest"
                            }
                            
                            # Route 1: Modern Parent Ping Endpoint
                            async with session.get("https://www.classcharts.com/api/v1/parent/ping", headers=api_headers) as api_response:
                                if api_response.status == 200:
                                    try:
                                        json_data = await api_response.json()
                                        
                                        # DEBUG DUMP TO LOGS
                                        _LOGGER.info("=== CLASS CHARTS PING API PAYLOAD ===")
                                        _LOGGER.info(json.dumps(json_data))
                                        
                                        pupils_list = json_data.get("data", {}).get("pupils", []) or json_data.get("pupils", [])
                                        if pupils_list and isinstance(pupils_list, list):
                                            found_kids = {}
                                            for p in pupils_list:
                                                p_id = str(p.get("id") or p.get("pupil_id") or "")
                                                p_name = p.get("name") or p.get("first_name", f"Student {p_id}")
                                                if p_id:
                                                    found_kids[p_id] = p_name.strip()
                                            
                                            if found_kids:
                                                _LOGGER.info("Discovered Class Charts children via API v1: %s", found_kids)
                                                return found_kids
                                    except Exception as json_err:
                                        _LOGGER.debug("API v1 parse skipped or failed: %s", json_err)

                            # Route 2: Dedicated Explicit Pupils List Endpoint
                            async with session.get("https://www.classcharts.com/api/v1/parent/pupils", headers=api_headers) as pupils_response:
                                if pupils_response.status == 200:
                                    try:
                                        json_data = await pupils_response.json()
                                        
                                        # DEBUG DUMP TO LOGS
                                        _LOGGER.info("=== CLASS CHARTS PUPILS API PAYLOAD ===")
                                        _LOGGER.info(json.dumps(json_data))
                                        
                                        pupils_list = json_data.get("data", []) if isinstance(json_data.get("data"), list) else json_data.get("data", {}).get("pupils", [])
                                        if not pupils_list and isinstance(json_data, list):
                                            pupils_list = json_data

                                        if pupils_list:
                                            found_kids = {}
                                            for p in pupils_list:
                                                p_id = str(p.get("id") or "")
                                                p_name = p.get("name") or p.get("first_name", f"Student {p_id}")
                                                if p_id:
                                                    found_kids[p_id] = p_name.strip()
                                            if found_kids:
                                                _LOGGER.info("Discovered Class Charts children via dedicated pupils API: %s", found_kids)
                                                return found_kids
                                    except Exception as json_err:
                                        _LOGGER.debug("Dedicated pupils API parse skipped: %s", json_err)

                            # Route 3: Traditional Base Ping Endpoint
                            async with session.get("https://www.classcharts.com/parent/ping", headers=api_headers) as alt_response:
                                if alt_response.status == 200:
                                    try:
                                        json_data = await alt_response.json()
                                        
                                        # DEBUG DUMP TO LOGS
                                        _LOGGER.info("=== CLASS CHARTS LEGACY PING PAYLOAD ===")
                                        _LOGGER.info(json.dumps(json_data))
                                        
                                        pupils_list = json_data.get("pupils", [])
                                        if isinstance(pupils_list, list) and pupils_list:
                                            found_kids = {str(p.get("id")): p.get("name", "").strip() for p in pupils_list if p.get("id")}
                                            if found_kids:
                                                _LOGGER.info("Discovered Class Charts children via legacy API: %s", found_kids)
                                                return found_kids
                                    except Exception as json_err:
                                        _LOGGER.debug("Legacy API parse skipped or failed: %s", json_err)

                            _LOGGER.error("Authenticated successfully, but API endpoints did not return an expected pupil array structure.")
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
