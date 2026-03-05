import logging
import datetime
from datetime import timedelta
import requests

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

# Import everything from your constants file
from .const import (
    DOMAIN, 
    LOGIN_URL, 
    PING_URL, 
    TIMETABLE_URL, 
    CONF_PUPIL_ID,
    CONF_REFRESH_INTERVAL,
    CONF_DAYS_TO_FETCH
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Class Charts from a config entry."""
    coordinator = ClassChartsCoordinator(hass, entry)
    
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["calendar"])
    
    # Listen for option updates (when user clicks 'Configure' and saves)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update - reloads the integration to apply new intervals."""
    await hass.config_entries.async_reload(entry.entry_id)

def sync_get_classcharts_data(email, password, pupil_id, days_to_fetch):
    """Fetch data using the exact meta -> session_id structure provided."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 HA-Integration",
        "Content-Type": "application/x-www-form-urlencoded"
    })
    
    try:
        # 1. Login
        _LOGGER.debug("Logging in to Class Charts...")
        login_resp = session.post(
            LOGIN_URL, 
            data={"email": email, "password": password, "remember": "true"},
            timeout=10
        )
        login_resp.raise_for_status()
        login_json = login_resp.json()

        token = login_json.get("meta", {}).get("session_id")

        if not token:
            _LOGGER.error("Login failed: Could not find 'session_id' inside 'meta'.")
            return {}

        _LOGGER.debug("Login successful. Token acquired.")

        full_schedule = {}
        for i in range(days_to_fetch):
            target_date = datetime.date.today() + datetime.timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")

            # 2. Ping Revalidation
            ping_resp = session.post(
                PING_URL,
                headers={"Authorization": f"Basic {token}"},
                data={"include_data": "true"},
                timeout=10
            )
            
            if ping_resp.status_code == 200:
                ping_json = ping_resp.json()
                token = ping_json.get("meta", {}).get("session_id") or token

            # 3. Timetable Fetch
            _LOGGER.debug("Fetching lessons for %s", date_str)
            resp = session.get(
                f"{TIMETABLE_URL}/{pupil_id}?date={date_str}",
                headers={"Authorization": f"Basic {token}"},
                timeout=10
            )
            
            day_data = resp.json()
            
            if isinstance(day_data, dict):
                lessons = day_data.get("data", [])
                full_schedule[date_str] = lessons if isinstance(lessons, list) else []
            elif isinstance(day_data, list):
                full_schedule[date_str] = day_data
            
        return full_schedule

    except Exception as err:
        _LOGGER.error("Class Charts Sync Error: %s", err)
        return {}
    finally:
        session.close()

class ClassChartsCoordinator(DataUpdateCoordinator):
    """Coordinator to manage dynamic updates based on user options."""
    def __init__(self, hass, entry):
        # Use constants to pull values from options
        self.refresh_interval = entry.options.get(CONF_REFRESH_INTERVAL, 24)
        self.days_to_fetch = entry.options.get(CONF_DAYS_TO_FETCH, 7)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=self.refresh_interval),
        )
        self.entry = entry

    async def _async_update_data(self):
        """Executor job passing user-configured days_to_fetch."""
        return await self.hass.async_add_executor_job(
            sync_get_classcharts_data,
            self.entry.data[CONF_EMAIL],
            self.entry.data[CONF_PASSWORD],
            self.entry.data[CONF_PUPIL_ID],
            self.days_to_fetch
        )
