import logging
import datetime
from datetime import timedelta
import requests

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from .const import (
    DOMAIN, LOGIN_URL, TIMETABLE_URL, CONF_PUPIL_ID,
    CONF_REFRESH_INTERVAL, CONF_DAYS_TO_FETCH
)

_LOGGER = logging.getLogger(__name__)

def _normalize_lesson(lesson):
    """Clean up lesson data."""
    subject = lesson.get("subject") or {}
    return {
        "subject_name": lesson.get("subject_name") or subject.get("name") or "Unknown",
        "teacher_name": lesson.get("teacher_name") or "Unknown",
        "room_name": lesson.get("room_name") or "N/A",
        "start_time": lesson.get("start_time") or lesson.get("start"),
        "end_time": lesson.get("end_time") or lesson.get("end"),
    }

def sync_get_classcharts_data(email, password, pupil_id, days_to_fetch):
    session = requests.Session()
    try:
        # 1. Login
        login_resp = session.post(LOGIN_URL, data={"email": email, "password": password, "remember": "true"}, timeout=10)
        login_resp.raise_for_status()
        token = login_resp.json().get("meta", {}).get("session_id")
        
        if not token:
            raise UpdateFailed("Login failed: No session_id")

        auth_headers = {"Authorization": f"Basic {token}"}
        
        # 2. Fetch Timetable (Dictionary of Days)
        full_schedule = {}
        for i in range(days_to_fetch):
            target_date = datetime.date.today() + datetime.timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")
            resp = session.get(f"{TIMETABLE_URL}/{pupil_id}?date={date_str}", headers=auth_headers, timeout=10)
            if resp.status_code == 200:
                lessons = resp.json().get("data", [])
                full_schedule[date_str] = [_normalize_lesson(l) for l in lessons]

        # 3. Fetch Homework
        hw_from = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        hw_to = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        hw_url = f"https://www.classcharts.com/apiv2parent/homeworks/{pupil_id}"
        hw_resp = session.get(hw_url, params={"display_date": "due_date", "from": hw_from, "to": hw_to}, headers=auth_headers, timeout=10)
        
        return {
            "timetable": full_schedule, 
            "homework": hw_resp.json() if hw_resp.status_code == 200 else {}
        }
    except Exception as e:
        raise UpdateFailed(f"API Error: {e}")
    finally:
        session.close()

class ClassChartsCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        interval = entry.options.get(CONF_REFRESH_INTERVAL, 2) # Default 2 hours
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(hours=interval))
        self.entry = entry
        self.days_to_fetch = entry.options.get(CONF_DAYS_TO_FETCH, 7)

    async def _async_update_data(self):
        return await self.hass.async_add_executor_job(
            sync_get_classcharts_data,
            self.entry.data[CONF_EMAIL], self.entry.data[CONF_PASSWORD],
            self.entry.data[CONF_PUPIL_ID], self.days_to_fetch
        )
