import logging
import datetime
from datetime import timedelta
import requests

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from .const import DOMAIN, LOGIN_URL, PING_URL, TIMETABLE_URL, CONF_PUPIL_ID

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Class Charts from a config entry."""
    coordinator = ClassChartsCoordinator(hass, entry)
    
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["calendar"])
    return True

def sync_get_classcharts_data(email, password, pupil_id):
    """Fetch data with robust type checking for lists vs dicts."""
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 HA-Integration"})
    
    try:
        # 1. Login
        login_resp = session.post(LOGIN_URL, data={"email": email, "password": password, "remember": "true"}, timeout=10)
        login_resp.raise_for_status()
        login_data = login_resp.json()

        # Extract token safely from dict
        if isinstance(login_data, dict):
            token = login_data.get("data") or login_data.get("token")
        else:
            _LOGGER.error("Login failed: Expected dict but got %s", type(login_data))
            return {}

        if not token:
            _LOGGER.error("Login failed: No token found in response")
            return {}

        full_schedule = {}
        for i in range(7):
            date_str = (datetime.date.today() + datetime.timedelta(days=i)).strftime("%Y-%m-%d")

            # --- Ping to keep session alive ---
            ping_resp = session.post(PING_URL, headers={"Authorization": f"Basic {token}"}, data={"include_data": "true"}, timeout=10)
            if ping_resp.status_code == 200:
                ping_json = ping_resp.json()
                if isinstance(ping_json, dict):
                    token = ping_json.get("meta", {}).get("session_id") or token

            # --- Fetch Timetable ---
            resp = session.get(f"{TIMETABLE_URL}/{pupil_id}?date={date_str}", headers={"Authorization": f"Basic {token}"}, timeout=10)
            day_data = resp.json()

            # --- THE FIX: Handle both List and Dict responses ---
            if isinstance(day_data, list):
                # The API returned the lessons directly as a list
                full_schedule[date_str] = day_data
                _LOGGER.debug("Loaded %s lessons from LIST for %s", len(day_data), date_str)
            
            elif isinstance(day_data, dict):
                # The API returned a dict, try to find the list inside 'data'
                lessons = day_data.get("data", [])
                full_schedule[date_str] = lessons if isinstance(lessons, list) else []
                _LOGGER.debug("Loaded %s lessons from DICT for %s", len(full_schedule[date_str]), date_str)
            
            else:
                _LOGGER.warning("Unexpected data type for %s: %s", date_str, type(day_data))
            
        return full_schedule

    except Exception as err:
        _LOGGER.error("Class Charts Sync Error: %s", err)
        return {}
    finally:
        session.close()

class ClassChartsCoordinator(DataUpdateCoordinator):
    """Coordinator to manage daily updates."""
    def __init__(self, hass, entry):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=24),
        )
        self.entry = entry

    async def _async_update_data(self):
        """Executor job to run synchronous requests."""
        return await self.hass.async_add_executor_job(
            sync_get_classcharts_data,
            self.entry.data[CONF_EMAIL],
            self.entry.data[CONF_PASSWORD],
            self.entry.data[CONF_PUPIL_ID]
        )
