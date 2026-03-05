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
    """Fetch data following the exact Ping revalidation schema."""
    session = requests.Session()
    # Class Charts often requires the form-encoded content type for POSTs
    session.headers.update({
        "User-Agent": "Mozilla/5.0 HA-Integration",
        "Content-Type": "application/x-www-form-urlencoded"
    })
    
    try:
        # 1. Login
        _LOGGER.debug("Attempting login...")
        login_resp = session.post(
            LOGIN_URL, 
            data={"email": email, "password": password, "remember": "true"},
            timeout=10
        )
        login_resp.raise_for_status()
        login_json = login_resp.json()

        # The initial token is in the 'data' field
        token = login_json.get("data")
        if not token or not isinstance(token, str):
            _LOGGER.error("Login failed: 'data' field did not contain a valid token string")
            return {}

        full_schedule = {}
        for i in range(7):
            date_str = (datetime.date.today() + datetime.timedelta(days=i)).strftime("%Y-%m-%d")

            # 2. Ping Revalidation (POST request as per docs)
            # This 'checks in' and gets the fresh session_id for the next fetch
            ping_resp = session.post(
                PING_URL,
                headers={"Authorization": f"Basic {token}"},
                data={"include_data": "true"},
                timeout=10
            )
            
            if ping_resp.status_code == 200:
                ping_json = ping_resp.json()
                # DOCS: Response -> meta -> session_id
                if isinstance(ping_json, dict):
                    new_token = ping_json.get("meta", {}).get("session_id")
                    if new_token:
                        token = new_token
                        _LOGGER.debug("Token rotated for date: %s", date_str)

            # 3. Timetable Fetch (GET request)
            resp = session.get(
                f"{TIMETABLE_URL}/{pupil_id}?date={date_str}",
                headers={"Authorization": f"Basic {token}"},
                timeout=10
            )
            
            day_data = resp.json()
            
            # Extract the lesson list. Documentation says it's in 'data'
            if isinstance(day_data, dict):
                full_schedule[date_str] = day_data.get("data", [])
            elif isinstance(day_data, list):
                full_schedule[date_str] = day_data
            
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
