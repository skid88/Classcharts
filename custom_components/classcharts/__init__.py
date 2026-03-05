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

        # DRILL DOWN: Based on your provided response structure
        # meta -> session_id
        token = login_json.get("meta", {}).get("session_id")

        if not token:
            _LOGGER.error("Login failed: Could not find 'session_id' inside 'meta'. Response: %s", login_json)
            return {}

        _LOGGER.debug("Login successful. Token: %s...", token[:8])

        full_schedule = {}
        for i in range(7):
            target_date = datetime.date.today() + datetime.timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")

            # 2. Ping Revalidation (to keep token fresh)
            ping_resp = session.post(
                PING_URL,
                headers={"Authorization": f"Basic {token}"},
                data={"include_data": "true"},
                timeout=10
            )
            
            if ping_resp.status_code == 200:
                ping_json = ping_resp.json()
                # Update token from the new meta -> session_id
                token = ping_json.get("meta", {}).get("session_id") or token

            # 3. Timetable Fetch
            _LOGGER.debug("Fetching lessons for %s", date_str)
            resp = session.get(
                f"{TIMETABLE_URL}/{pupil_id}?date={date_str}",
                headers={"Authorization": f"Basic {token}"},
                timeout=10
            )
            
            day_data = resp.json()
            
            # The lessons list is typically in 'data'
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
