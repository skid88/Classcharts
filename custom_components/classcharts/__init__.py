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
    """Fetch data from Class Charts with improved token detection."""
    try:
        _LOGGER.debug("Attempting login for %s", email)
        session_resp = requests.post(
            LOGIN_URL, 
            data={"email": email, "password": password, "remember": "true"},
            timeout=10
        )
        session_resp.raise_for_status()
        
        json_resp = session_resp.json()
        # This will check 'token', 'data', and 'access_token' automatically
        token = json_resp.get("token") or json_resp.get("data") or json_resp.get("access_token")
        
        if not token:
            _LOGGER.error("Login successful but no token found. Keys found: %s", list(json_resp.keys()))
            return {}

        _LOGGER.debug("Login successful, token acquired.")

        full_schedule = {}
        for i in range(7):
            # Using a safer date calculation
            target_date = datetime.date.today() + datetime.timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")
            
            _LOGGER.debug("Requesting timetable for: %s", date_str)
            resp = requests.get(
                f"{TIMETABLE_URL}/{pupil_id}?date={date_str}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            
            if resp.status_code == 200:
                day_data = resp.json()
                # Some APIs return the list directly, some wrap it in 'data'
                lessons = day_data.get("data") if isinstance(day_data.get("data"), list) else day_data
                full_schedule[date_str] = lessons
                _LOGGER.debug("Saved %s lessons for %s", len(lessons), date_str)
            else:
                _LOGGER.warning("Failed to get data for %s: %s", date_str, resp.status_code)
            
        return full_schedule

    except Exception as err:
        _LOGGER.error("Class Charts Sync Error: %s", err)
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
