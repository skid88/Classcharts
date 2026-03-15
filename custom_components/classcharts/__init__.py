import logging
import datetime
from datetime import timedelta
import requests

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
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
    """Clean up lesson data for the sensors."""
    if not isinstance(lesson, dict):
        return {}
    subject = lesson.get("subject") or {}
    teacher = lesson.get("teacher") or {}
    room = lesson.get("room") or {}
    return {
        "subject_name": lesson.get("subject_name") or subject.get("name"),
        "teacher_name": lesson.get("teacher_name") or teacher.get("name"),
        "room_name": lesson.get("room_name") or room.get("name"),
        "start_time": lesson.get("start_time") or lesson.get("start"),
        "end_time": lesson.get("end_time") or lesson.get("end"),
        "raw": lesson,
    }


def sync_get_classcharts_data(email, password, pupil_id, days_to_fetch):
    """Fetch both Timetable and Homework data."""
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
            timeout=10
        )
        login_resp.raise_for_status()
        
        try:
            login_json = login_resp.json()
        except ValueError:
            _LOGGER.error("API did not return valid JSON")
            return {"timetable": [], "homework": {}}

        # Guard against the 'list' object error
        if not isinstance(login_json, dict):
            _LOGGER.error("Login failed: Expected a dictionary, but got a %s", type(login_json))
            return {"timetable": [], "homework": {}}

        # Safe extraction of the token
        meta = login_json.get("meta", {})
        token = meta.get("session_id") if isinstance(meta, dict) else None

        if not token:
            _LOGGER.error("Login failed: No session_id found.")
            return {"timetable": [], "homework": {}}

        # 2. Fetch Timetable
        full_schedule = {}
        auth_headers = {"Authorization": f"Basic {token}"}
        
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
                if isinstance(day_data, dict):
                    lessons = day_data.get("data", [])
                    full_schedule[date_str] = [
                        _normalize_lesson(lesson) for lesson in lessons
                    ] if isinstance(lessons, list) else []

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
        
        homework_data = {}
        if hw_resp.status_code == 200:
            homework_data = hw_resp.json()

        # Extract today's list for the sensors
        today_str = datetime.date.today().strftime("%Y-%m-%d")

        return {
            "timetable": full_schedule.get(today_str, []),
            "homework": homework_data,
            "full_schedule": full_schedule 
        }

    except Exception:
        _LOGGER.exception("Unexpected error during Class Charts sync")
        return {"timetable": [], "homework": {}}
    finally:
        session.close()

class ClassChartsCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Class Charts data."""
    def __init__(self, hass, entry):
        self.refresh_interval = entry.options.get(CONF_REFRESH_INTERVAL) or entry.data.get(CONF_REFRESH_INTERVAL, 24)
        self.days_to_fetch = entry.options.get(CONF_DAYS_TO_FETCH) or entry.data.get(CONF_DAYS_TO_FETCH, 7)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=self.refresh_interval),
        )
        self.entry = entry

    async def _async_update_data(self):
        """Fetch data from API."""
        result = await self.hass.async_add_executor_job(
            sync_get_classcharts_data,
            self.entry.data[CONF_EMAIL],
            self.entry.data[CONF_PASSWORD],
            self.entry.data[CONF_PUPIL_ID],
            self.days_to_fetch
        )
        
        if result is None:
            raise UpdateFailed("Error communicating with ClassCharts API")
            
        return result

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Class Charts from a config entry."""
    coordinator = ClassChartsCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "calendar"])
    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "calendar"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
