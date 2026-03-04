import logging
from datetime import timedelta
import datetime
import requests

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from .const import DOMAIN, LOGIN_URL, TIMETABLE_URL, CONF_PUPIL_ID

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Class Charts from a config entry."""
    coordinator = ClassChartsCoordinator(hass, entry)
    
    # Perform initial setup
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["calendar"])
    return True

def sync_get_classcharts_data(email, password, pupil_id):
    """Fetch data from Class Charts."""
    try:
        # 1. Login
        session_resp = requests.post(
            LOGIN_URL, 
            data={"email": email, "password": password, "remember": "true"},
            timeout=10
        )
        session_resp.raise_for_status()
        
        json_resp = session_resp.json()
        token = json_resp.get("data") or json_resp.get("token")
        
        if not token:
            _LOGGER.error("Login successful but no token found: %s", json_resp)
            return {}

        # 2. Fetch 7 days of lessons
        full_schedule = {}
        for i in range(7):
            date_str = (datetime.date.today() + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            
            _LOGGER.debug("Fetching timetable for date: %s", date_str)
            resp = requests.get(
                f"{TIMETABLE_URL}/{pupil_id}?date={date_str}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            resp.raise_for_status()
            
            # We call .json() once and save it to a variable
            day_data = resp.json()
            _LOGGER.debug("Raw data for %s: %s", date_str, day_data)
            
            # Extract the actual list of lessons
            full_schedule[date_str] = day_data.get("data", [])
            
        return full_schedule

    except Exception as err:
        _LOGGER.error("Failed to fetch Class Charts data: %s", err)
        raise err

class ClassChartsCoordinator(DataUpdateCoordinator):
    """Coordinator to handle the once-a-day sync."""

    def __init__(self, hass, entry):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=24), # As requested
        )
        self.entry = entry

    async def _async_update_data(self):
        """Fetch data from API using the executor."""
        # This is the magic line that fixes your error:
        return await self.hass.async_add_executor_job(
            sync_get_classcharts_data,
            self.entry.data[CONF_EMAIL],
            self.entry.data[CONF_PASSWORD],
            self.entry.data[CONF_PUPIL_ID]
        )
