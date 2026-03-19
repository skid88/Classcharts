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
    """Fetch both Timetable and Homework data safely."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 HA-Integration",
        "Content-Type": "application/x-www-form-urlencoded"
    })
    
    try:
        # 1. Login
        login_resp = session.post(
            LOGIN_URL, 
            data={"email": email, "password": password, "remember": "true"},
            timeout=15
        )
        login_resp.raise_for_status()
        login_json = login_resp.json()

        token = login_json.get("meta", {}).get("session_id")
        if not token:
            raise UpdateFailed("No session_id found in login response")

        auth_headers = {"Authorization": f"Basic {token}"}
        
        # 2. Fetch Timetable
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
                full_schedule[date_str] = [_normalize_lesson(l) for l in lessons]

        # 3. Fetch Homework
        hw_from = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        hw_to = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        hw_url = f"https://www.classcharts.com/apiv2parent/homeworks/{pupil_id}"
        
        hw_resp = session.get(
            hw_url,
            params={"display_date": "due_date", "from": hw_from, "to": hw_to},
            headers=auth_headers,
            timeout=10
        )
        
        homework_data = hw_resp.json() if hw_resp.status_code == 200 else {}

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
        
        # We need to make sure these match the strings in const.py
        # Defaulting to 14 if the setting isn't found
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
        # This log line will tell us EXACTLY what the code is doing
        _LOGGER.info("Class Charts: Fetching %s days of data", self.days_to_fetch)
        
        return await self.hass.async_add_executor_job(
            sync_get_classcharts_data,
            self.entry.data[CONF_EMAIL],
            self.entry.data[CONF_PASSWORD],
            self.entry.data[CONF_PUPIL_ID],
            self.days_to_fetch
        )
