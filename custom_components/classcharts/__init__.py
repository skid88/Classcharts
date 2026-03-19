"""The Class Charts integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import ClassChartsCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Class Charts from a config entry."""
    
    # 1. Initialize the coordinator
    coordinator = ClassChartsCoordinator(hass, entry)
    
    # 2. Get initial data
    await coordinator.async_config_entry_first_refresh()

    # 3. Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # 4. Register the listener for Option Flow changes (Days to Fetch / Interval)
    # This ensures that when you hit "Submit" in the settings, the integration reloads.
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    # 5. Load platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    # This forces a reload of the integration with the new settings
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
