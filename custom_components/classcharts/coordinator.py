import logging
import datetime
from datetime import timedelta
import requests
import urllib.parse

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from .const import (
    DOMAIN, 
    TIMETABLE_URL, 
    CONF_PUPIL_ID,
    CONF_REFRESH_INTERVAL,
    CONF_DAYS_TO_FETCH
)

_LOGGER = logging.getLogger(__name__)

# Updated base URLs matching the new client specifications
NEW_LOGIN_URL = "https://www.classcharts.com/parent/login"

def _normalize_lesson(lesson):
    """Clean up lesson data for the sensors and calendar."""
    if not isinstance(lesson, dict):
        return {}
    subject = lesson.get("subject") or {}
    teacher = lesson.get("teacher") or {}
    room = lesson.get("room") or {}
    
    return {
        "subject_name": lesson.get("subject_name") or subject.get("name") or "Unknown",
        "teacher_name": lesson.get("teacher_name") or teacher.get("name") or "Unknown",
        "room_name": lesson.get("room_name") or room.get("name") or "N/A",
        "start_time": lesson.get("start_time") or lesson.get("start"),
        "end_time": lesson.get("end_time") or lesson.get("end"),
    }

def sync_get_classcharts_data(email, password, pupil_id, days_to_fetch):
    """Fetch data using the new browser-cookie authentication system."""
    session = requests.Session()
    
    # Standard authentic browser setup
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
        "Origin": "https://www.classcharts.com",
        "Referer": "https://www.classcharts.com/",
        "Content-Type": "application/x-www-form-urlencoded"
    })
    
    import urllib.parse  # <-- Add this import at the very top of your file

# ... inside sync_get_classcharts_data ...

    try:
        # 1. Format the login payload as a raw, strict URL-encoded string
        login_payload = {
            "_method": "POST",
            "email": email,
            "logintype": "existing",
            "password": password,
            "recaptcha-token": "no-token-available"
        }
        
        # This converts the dictionary into a literal string: _method=POST&email=...
        encoded_payload = urllib.parse.urlencode(login_payload)
        
        login_resp = session.post(
            NEW_LOGIN_URL, 
            data=encoded_payload,  # <-- Send the raw encoded string
            allow_redirects=False,
            timeout=15
        )

        # The new API signifies success via a 302 redirect back to the portal
        if login_resp.status_code != 302:
            _LOGGER.error("New login method rejected. HTTP Code: %s, Response: %s", login_resp.status_code, login_resp.text)
            raise UpdateFailed("ClassCharts rejected authentication credentials")
            
        # Verify the crucial parent credential cookie was injected into our session
        if "parent_session_credentials" not in session.cookies.get_dict():
            raise UpdateFailed("Authentication cookie 'parent_session_credentials' missing from response")

        # Adjust headers context from HTML navigation to JSON endpoint fetching
        session.headers.update({"Accept": "application/json, text/plain, */*"})
        if "Content-Type" in session.headers:
            del session.headers["Content-Type"]

        # 2. Fetch Timetable Data 
        full_schedule = {}
        for i in range(days_to_fetch):
            target_date = datetime.date.today() + datetime.timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")

            resp = session.get(
                f"{TIMETABLE_URL}/{pupil_id}?date={date_str}",
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Referer": "https://www.classcharts.com/parent/timetable",
                    "X-Requested-With": "XMLHttpRequest"  # <-- Tells the server this is a standard web app data request
                },
                timeout=10
            )
            
            if resp.status_code == 200:
                day_data = resp.json()
                lessons = day_data.get("data", []) if isinstance(day_data, dict) else []
                full_schedule[date_str] = [_normalize_lesson(l) for l in lessons] if isinstance(lessons, list) else []
            else:
                _LOGGER.warning("Timetable query failed for %s with status: %s", date_str, resp.status_code)

        # 3. Fetch Homework Data
        hw_from = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        hw_to = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        hw_url = f"{HOMEWORK_URL}/{pupil_id}"
        
        hw_resp = session.get(
            hw_url,
            params={"display_date": "due_date", "from": hw_from, "to": hw_to},
            headers={
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.classcharts.com/parent/homeworks",
                "X-Requested-With": "XMLHttpRequest"
            },
            timeout=10
        )
        
        homework_data = {"data": [], "meta": {}}
        if hw_resp.status_code == 200:
            hw_json = hw_resp.json()
            if isinstance(hw_json, list):
                homework_data = {"data": hw_json, "meta": {}}
            elif isinstance(hw_json, dict):
                homework_data = hw_json

        return {
            "timetable": full_schedule,
            "homework": homework_data,
        }

    except Exception as err:
        _LOGGER.error("Error fetching Class Charts data: %s", err)
        raise UpdateFailed(f"Error communicating with API: {err}")
    finally:
        session.close()

class ClassChartsCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Class Charts data."""
    def __init__(self, hass, entry):
        self.entry = entry
        
        self.days_to_fetch = entry.options.get(CONF_DAYS_TO_FETCH, 
                             entry.data.get(CONF_DAYS_TO_FETCH, 14))
        
        self.refresh_interval = entry.options.get(CONF_REFRESH_INTERVAL, 
                                entry.data.get(CONF_REFRESH_INTERVAL, 24))
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=max(1, self.refresh_interval)),
        )

    async def _async_update_data(self):
        """Fetch data from API using executor."""
        _LOGGER.info("Class Charts: Fetching %s days of data", self.days_to_fetch)
        
        return await self.hass.async_add_executor_job(
            sync_get_classcharts_data,
            self.entry.data[CONF_EMAIL],
            self.entry.data[CONF_PASSWORD],
            self.entry.data[CONF_PUPIL_ID],
            self.days_to_fetch
        )
