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
    """Fetch data with a bulletproof 'safe_get' to prevent list attribute errors."""
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 HA-Integration"})
    
    def safe_get(data, key, default=None):
        """Helper to safely get a key whether data is a list or dict."""
        if isinstance(data, dict):
            return data.get(key, default)
        return default

    try:
        # 1. Login
        login_resp = session.post(LOGIN_URL, data={"email": email, "password": password, "remember": "true"}, timeout=10)
        login_resp.raise_for_status()
        login_json = login_resp.json()

        # Safely extract token
        token = safe_get(login_json, "data") or safe_get(login_json, "token")
        
        if not token:
            _LOGGER.error("Login failed: No token found. Response type: %s", type(login_json))
            return {}

        full_schedule = {}
        for i in range(7):
            date_str = (datetime.date.today() + datetime.timedelta(days=i)).strftime("%Y-%m-%d")

            # 2. Ping Revalidation
            ping_resp = session.post(PING_URL, headers={"Authorization": f"Basic {token}"}, data={"include_data": "true"}, timeout=10)
            if ping_resp.status_code == 200:
                ping_json = ping_resp.json()
                # Safely drill down into meta -> session_id
                meta = safe_get(ping_json, "meta", {})
                token = safe_get(meta, "session_id") or token

            # 3. Timetable Fetch
            resp = session.get(f"{TIMETABLE_URL}/{pupil_id}?date={date_str}", headers={"Authorization": f"Basic {token}"}, timeout=10)
            day_data = resp.json()

            # 4. Extract Lessons Safely
            if isinstance(day_data, list):
                full_schedule[date_str] = day_data
            else:
                full_schedule[date_str] = safe_get(day_data, "data", [])
            
            _LOGGER.debug("Day %s: Found %s lessons", date_str, len(full_schedule[date_str]))
            
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
