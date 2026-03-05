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
    """Fetch data using Session, Basic Auth, and Ping revalidation."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })
    
    try:
        # 1. Login
        _LOGGER.debug("Logging in to Class Charts Parent API")
        login_resp = session.post(
            LOGIN_URL, 
            data={"email": email, "password": password, "remember": "true"},
            timeout=10
        )
        login_resp.raise_for_status()
        
        # Initial token from login
        token = login_resp.json().get("data")
        if not token:
            _LOGGER.error("Login failed: No token returned in 'data'")
            return {}

        # 2. Loop through 7 days of lessons
        full_schedule = {}
        for i in range(7):
            target_date = datetime.date.today() + datetime.timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")

            # --- THE PING (Revalidation as per Docs) ---
            # Revalidates the session and gets a potential new session_id
            ping_resp = session.post(
                PING_URL,
                headers={"Authorization": f"Basic {token}"},
                data={"include_data": "true"},
                timeout=10
            )
            
            if ping_resp.status_code == 200:
                ping_data = ping_resp.json()
                # Update token if a new session_id is provided in meta
                token = ping_data.get("meta", {}).get("session_id") or token
            
            # --- THE DATA FETCH ---
            _LOGGER.debug("Fetching lessons for %s", date_str)
            resp = session.get(
                f"{TIMETABLE_URL}/{pupil_id}?date={date_str}",
                headers={"Authorization": f"Basic {token}"},
                timeout=10
            )
            
            day_data = resp.json()
            if day_data.get("success") == 0:
                _LOGGER.warning("Day %s skipped: %s", date_str, day_data.get("error"))
                continue

            full_schedule[date_str] = day_data.get("data", [])
            _LOGGER.debug("Successfully loaded %s lessons for %s", len(full_schedule[date_str]), date_str)
            
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
