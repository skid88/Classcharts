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
    """Fetch data using a Session to maintain login state."""
    # Create a session to handle cookies/state
    session = requests.Session()
    
    try:
        # 1. Login
        _LOGGER.debug("Attempting session login for %s", email)
        login_resp = session.post(
            LOGIN_URL, 
            data={"email": email, "password": password, "remember": "true"},
            timeout=10
        )
        login_resp.raise_for_status()
        
        json_resp = login_resp.json()
        token = json_resp.get("data") or json_resp.get("token")
        
        if not token:
            _LOGGER.error("No token found in login response")
            return {}

        # Set the header on the session so it's used for every following request
        session.headers.update({"Authorization": f"Bearer {token}"})

        # 2. Fetch 7 days of lessons
        full_schedule = {}
        for i in range(7):
            target_date = datetime.date.today() + datetime.timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")
            
            _LOGGER.debug("Fetching date %s using session", date_str)
            # Use 'session.get' instead of 'requests.get'
            resp = session.get(
                f"{TIMETABLE_URL}/{pupil_id}?date={date_str}",
                timeout=10
            )
            
            day_data = resp.json()
            
            # Check if this specific day failed due to a session timeout
            if day_data.get("success") == 0:
                _LOGGER.warning("API returned error for %s: %s", date_str, day_data.get("error"))
                continue

            full_schedule[date_str] = day_data.get("data", [])
            
        return full_schedule

    except Exception as err:
        _LOGGER.error("Class Charts Session Error: %s", err)
        raise err
    finally:
        session.close()

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
