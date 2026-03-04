import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGIN_URL, TIMETABLE_URL
import requests
import datetime

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Class Charts from a config entry."""
    
    # Create the coordinator
    coordinator = ClassChartsCoordinator(hass, entry)
    
    # Fetch initial data so we have something on startup
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator for platforms (calendar.py) to use
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward the setup to the calendar platform
    await hass.config_entries.async_forward_entry_setups(entry, ["calendar"])
    return True

class ClassChartsCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Class Charts data once a day."""

    def __init__(self, hass, entry):
        """Initialize."""
        self.entry = entry
        # Update every 24 hours
        super().__init__(
            hass, 
            _LOGGER, 
            name=DOMAIN, 
            update_interval=timedelta(hours=24)
        )

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            # 1. Login Logic
            session = requests.post(LOGIN_URL, data={
                "email": self.entry.data["email"],
                "password": self.entry.data["password"],
                "remember": "true"
            })
            token = session.json().get("token")
            pupil_id = self.entry.data["pupil_id"]

            # 2. Multi-day Fetch Logic
            full_schedule = {}
            for i in range(7):  # Get a full week
                date = (datetime.date.today() + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
                resp = requests.get(
                    f"{TIMETABLE_URL}/{pupil_id}?date={date}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                full_schedule[date] = resp.json().get("data", [])

            return full_schedule

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
