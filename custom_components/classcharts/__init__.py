"""The Class Charts integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import ClassChartsCoordinator

_LOGGER = logging.getLogger(__name__)

# This list tells HA which files (sensor.py, calendar.py) to load
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Class Charts from a config entry."""
    
    # 1. Initialize the coordinator logic
    coordinator = ClassChartsCoordinator(hass, entry)
    
    # 2. Get the first batch of data before finishing setup
    await coordinator.async_config_entry_first_refresh()

    # 3. Store the coordinator so sensors/calendars can use it
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # 4. Fire up the sensor.py and calendar.py platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
