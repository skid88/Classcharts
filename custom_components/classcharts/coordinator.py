import logging
import datetime
import requests
import json
import urllib.parse
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN, 
    TIMETABLE_URL, 
    HOMEWORK_URL, 
    LOGIN_URL, 
    PING_URL,
    CONF_PUPIL_ID,
    CONF_DAYS_TO_FETCH
)

_LOGGER = logging.getLogger(__name__)

def sync_get_classcharts_data(email, password, pupil_id, days_to_fetch):
    """Fetch data using the verified hybrid Cookie + Auth + Ping initialization."""
    session = requests.Session()
    
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-GB,en;q=0.9",
        "Origin": "https://www.classcharts.com",
        "Referer": "https://www.classcharts.com/",
    })
    
    try:
        # 1. Step 1: Web Portal Login
        session.headers.update({"Content-Type": "application/x-www-form-urlencoded"})
        login_payload = {
            "_method": "POST",
            "email": email,
            "logintype": "existing",
            "password": password,
            "recaptcha-token": "no-token-available"
        }
        encoded_login = urllib.parse.urlencode(login_payload)
        
        login_resp = session.post(
            LOGIN_URL, 
            data=encoded_login,
            allow_redirects=False,
            timeout=15
        )

        if login_resp.status_code != 302:
            raise UpdateFailed(f"ClassCharts web login rejected credentials. Code: {login_resp.status_code}")

        # 2. Step 2: Extract Token from Cookie Jar
        cookies_dict = session.cookies.get_dict()
        raw_cookie_data = cookies_dict.get("parent_session_credentials")
        
        if not raw_cookie_data:
            raise UpdateFailed("Authentication missing parent_session_credentials cookie")
            
        decoded_cookie_str = urllib.parse.unquote(raw_cookie_data)
        cookie_json = json.loads(decoded_cookie_str)
        session_token = cookie_json.get("session_id")
        
        if not session_token:
            raise UpdateFailed("Failed to parse session_id out of cookie wrapper")

        # Apply hybrid authorization header base
        session.headers.update({
            "Authorization": f"Basic {session_token}",
            "X-Requested-With": "XMLHttpRequest"
        })
        if "Content-Type" in session.headers:
            del session.headers["Content-Type"]

        # 3. Step 3: Crucial Ping Handshake
        ping_payload = {"include_data": "true"}
        encoded_ping = urllib.parse.urlencode(ping_payload)
        
        session.headers.update({"Content-Type": "application/x-www-form-urlencoded"})
        ping_resp = session.post(PING_URL, data=encoded_ping, timeout=10)
        
        if "Content-Type" in session.headers:
            del session.headers["Content-Type"]

        if ping_resp.status_code != 200:
            raise UpdateFailed(f"API Session initialization via Ping failed. Code: {ping_resp.status_code}")

        # 4. Step 4: Fetch Timetable Data
        full_schedule = {}
        for i in range(days_to_fetch):
            target_date = datetime.date.today() + datetime.timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")

            resp = session.get(
                f"{TIMETABLE_URL}/{pupil_id}",
                params={"date": date_str},
                timeout=10
            )
            
            if resp.status_code == 200:
                day_data = resp.json()
                lessons = day_data.get("data", []) if isinstance(day_data, dict) else []
                full_schedule[date_str] = lessons if isinstance(lessons, list) else []
            else:
                _LOGGER.error("Timetable query failed for %s. Code: %s", date_str, resp.status_code)

        # 5. Step 5: Fetch Homework Data
        hw_from = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        hw_to = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        hw_url = f"{HOMEWORK_URL}/{pupil_id}"
        
        hw_resp = session.get(
            hw_url,
            params={"display_date": "due_date", "from": hw_from, "to": hw_to},
            timeout=10
        )
        
        homework_data = {"data": [], "meta": {}}
        if hw_resp.status_code == 200:
            hw_json = hw_resp.json()
            if isinstance(hw_json, list):
                homework_data = {"data": hw_json, "meta": {}}
            elif isinstance(hw_json, dict):
                homework_data = hw_json
        else:
            _LOGGER.error("Homework data retrieval failed with code: %s", hw_resp.status_code)

        return {
            "timetable": full_schedule,
            "homework": homework_data,
        }

    except Exception as err:
        _LOGGER.error("Error fetching Class Charts data payload: %s", err)
        raise UpdateFailed(f"Error communicating with API: {err}")
    finally:
        session.close()


class ClassChartsCoordinator(DataUpdateCoordinator):
    """The wrapper class Home Assistant uses to schedule updates."""

    def __init__(self, hass: HomeAssistant, entry):
        """Initialize the coordinator class."""
        self.entry = entry
        
        # Read parameters out of your config entry storage
        self.email = entry.data["email"]
        self.password = entry.data["password"]
        self.pupil_id = entry.data[CONF_PUPIL_ID]
        
        # Read update intervals safely with defaults
        refresh_interval = entry.options.get("refresh_interval", 24)
        self.days_to_fetch = entry.options.get(CONF_DAYS_TO_FETCH, 14)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=refresh_interval),
        )

    async def _async_update_data(self):
        """Route the async coordinator request down to our sync fetch loop."""
        return await self.hass.async_add_executor_job(
            sync_get_classcharts_data,
            self.email,
            self.password,
            self.pupil_id,
            self.days_to_fetch
        )
