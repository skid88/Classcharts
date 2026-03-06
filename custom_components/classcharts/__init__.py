import logging
import datetime
from datetime import timedelta
import requests

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

# Ensure HOMEWORK_URL is added to your .const file or defined here
# HOMEWORK_URL = "https://www.classcharts.com/apiv2parent/homeworks"

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

    await hass.config_entries.async_forward_entry_setups(entry, ["calendar", "sensor"])
    
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)

def sync_get_classcharts_data(email, password, pupil_id, days_to_fetch):
    """Fetch both Timetable and Homework data."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 HA-Integration",
        "Content-Type": "application/x-www-form-urlencoded"
    })
    
    try:
        # 1. Login
        login_resp = session.post(
            LOGIN_URL, 
            data={"email": email, "password": password, "remember": "true"},
            timeout=10
        )
        login_resp.raise_for_status()
        login_json = login_resp.json()
        token = login_json.get("meta", {}).get("session_id")

        if not token:
            _LOGGER.error("Login failed: No session_id found.")
            return {}

        # 2. Fetch Timetable
        full_schedule = {}
        for i in range(days_to_fetch):
            target_date = datetime.date.today() + datetime.timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")

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

        # 3. Fetch Homework
        # We'll fetch from 1 day ago to 30 days in the future to catch everything
        hw_from = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        hw_to = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        
        # Note: You may need to add HOMEWORK_URL to your const.py
        # It is usually: https://www.classcharts.com/apiv2parent/homeworks
        hw_url = f"https://www.classcharts.com/apiv2parent/homeworks/{pupil_id}?display_date=due_date&from={hw_from}&to={hw_to}"
        
        hw_resp = session.get(
            hw_url,
            headers={"Authorization": f"Basic {token}"},
            timeout=10
        )
        homework_data = hw_resp.json()

        # Return combined data
        return {
            "timetable": full_schedule,
            "homework": homework_data
        }

    except Exception as err:
        _LOGGER.error("Class Charts Sync Error: %s", err)
        return {}
    finally:
        session.close()

class ClassChartsCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
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
        return await self.hass.async_add_executor_job(
            sync_get_classcharts_data,
            self.entry.data[CONF_EMAIL],
            self.entry.data[CONF_PASSWORD],
            self.entry.data[CONF_PUPIL_ID],
            self.days_to_fetch
        )
