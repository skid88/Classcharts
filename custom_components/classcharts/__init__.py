import logging
import datetime
from datetime import timedelta
import requests

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
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
    """Fetch data using a Session with enhanced headers."""
    session = requests.Session()
    # 1. Pretend to be a real browser
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
    })
    
    try:
        # 2. Login
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
            _LOGGER.error("Login successful but no token found")
            return {}

        # 3. Add Token AND Pupil-ID to headers (some schools require this)
        session.headers.update({
            "Authorization": f"Bearer {token}",
            "X-Pupil-Id": str(pupil_id)
        })

        # 4. Fetch 7 days of lessons
        full_schedule = {}
        for i in range(7):
            target_date = datetime.date.today() + datetime.timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")
            
            # Use the session to maintain cookies
            resp = session.get(
                f"{TIMETABLE_URL}/{pupil_id}?date={date_str}",
                timeout=15
            )
            
            day_data = resp.json()
            
            # If we get an error, log it but keep going for other days
            if day_data.get("success") == 0 or "error" in day_data:
                _LOGGER.warning("Day %s failed: %s", date_str, day_data.get("error"))
                continue

            full_schedule[date_str] = day_data.get("data", [])
            _LOGGER.debug("Successfully fetched %s lessons for %s", len(full_schedule[date_str]), date_str)
            
        return full_schedule

    except Exception as err:
        _LOGGER.error("Class Charts Session Error: %s", err)
        return {}
    finally:
        session.close()

class ClassChartsCoordinator(DataUpdateCoordinator):
    """Coordinator to handle the sync."""

    def __init__(self, hass, entry):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=24),
        )
        self.entry = entry

    async def _async_update_data(self):
        """Fetch data from API."""
        return await self.hass.async_add_executor_job(
            sync_get_classcharts_data,
            self.entry.data[CONF_EMAIL],
            self.entry.data[CONF_PASSWORD],
            self.entry.data[CONF_PUPIL_ID]
        )
