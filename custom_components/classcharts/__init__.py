# 1. Imports at the very top
import logging
import datetime
from datetime import timedelta
import requests
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from .const import DOMAIN, LOGIN_URL, TIMETABLE_URL, CONF_PUPIL_ID, CONF_REFRESH_INTERVAL, CONF_DAYS_TO_FETCH

_LOGGER = logging.getLogger(__name__)

# 2. Helper functions (Flush Left)
def _normalize_lesson(lesson):
    # ... your existing normalization code ...
    return { ... }

# 3. The Sync Function (Flush Left)
def sync_get_classcharts_data(email, password, pupil_id, days_to_fetch):
    # ... The code you just pasted goes here ...
    # ... Ensure the "return" is inside the "try" block ...

# 4. The Coordinator Class (Flush Left)
class ClassChartsCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        self.refresh_interval = entry.options.get(CONF_REFRESH_INTERVAL) or entry.data.get(CONF_REFRESH_INTERVAL, 24)
        self.days_to_fetch = entry.options.get(CONF_DAYS_TO_FETCH) or entry.data.get(CONF_DAYS_TO_FETCH, 7)
        super().__init__(
            hass, _LOGGER, name=DOMAIN, 
            update_interval=timedelta(hours=self.refresh_interval),
        )
        self.entry = entry

    async def _async_update_data(self):
        result = await self.hass.async_add_executor_job(
            sync_get_classcharts_data,
            self.entry.data[CONF_EMAIL],
            self.entry.data[CONF_PASSWORD],
            self.entry.data[CONF_PUPIL_ID],
            self.days_to_fetch
        )
        if result is None:
            raise UpdateFailed("Error communicating with ClassCharts API")
        return result

# 5. THE CRITICAL SETUP FUNCTIONS (Flush Left - No spaces at start of line)
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """This function MUST be here for Home Assistant to start."""
    coordinator = ClassChartsCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "calendar"])
    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "calendar"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
