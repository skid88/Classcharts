import logging
import datetime
from datetime import timedelta
import requests

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from .const import (
    DOMAIN, 
    LOGIN_URL, 
    TIMETABLE_URL, 
    CONF_PUPIL_ID,
    CONF_REFRESH_INTERVAL,
    CONF_DAYS_TO_FETCH
)

_LOGGER = logging.getLogger(__name__)

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
    """Fetch both Timetable and Homework data safely with a valid browser context."""
    session = requests.Session()
    
    # 1. Bypass Cloudflare 500 Proxy errors by using a real Chrome desktop user agent
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-GB,en;q=0.9",
        "Origin": "https://www.classcharts.com",
        "Referer": "https://www.classcharts.com/",
        "Content-Type": "application/x-www-form-urlencoded"
    })
    
    try:
        # 2. Login (POST)
        login_resp = session.post(
            LOGIN_URL, 
            data={"email": email, "password": password, "remember": "true"},
            timeout=15
        )
        login_resp.raise_for_status()
        login_json = login_resp.json()

        if not isinstance(login_json, dict):
            raise UpdateFailed(f"Unexpected login response structure: {type(login_json)}")

        token = login_json.get("meta", {}).get("session_id") if isinstance(login_json.get("meta"), dict) else None
        if not token:
            raise UpdateFailed("No session_id found in login response")

        # Set up auth headers using the session ID
        auth_headers = {"Authorization": f"Basic {token}"}
        
        # Clear out the POST content-type from the persistent session so future GET requests look clean
        if "Content-Type" in session.headers:
            del session.headers["Content-Type"]
        
        # 3. Fetch Timetable (GET)
        full_schedule = {}
        for i in range(days_to_fetch):
            target_date = datetime.date.today() + datetime.timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")

            resp = session.get(
                f"{TIMETABLE_URL}/{pupil_id}?date={date_str}",
                headers=auth_headers,
                timeout=10
            )
            
            if resp.status_code == 200:
                day_data = resp.json()
                lessons = day_data.get("data", []) if isinstance(day_data, dict) else []
                full_schedule[date_str] = [_normalize_lesson(l) for l in lessons] if isinstance(lessons, list) else []

        # 4. Fetch Homework (GET)
        hw_from = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        hw_to = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        hw_url = f"https://www.classcharts.com/apiv2parent/homeworks/{pupil_id}"
        
        hw_resp = session.get(
            hw_url,
            params={"display_date": "due_date", "from": hw_from, "to": hw_to},
            headers=auth_headers,
            timeout=10
        )
        
        # Guard Check: If a child has no homework, ClassCharts sends a raw list []. 
        # We restructure it to a dict here so your sensor.py native_value never crashes.
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
