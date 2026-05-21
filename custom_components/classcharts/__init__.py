"""The Class Charts integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import ClassChartsCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Class Charts from a config entry."""
    
    
    if not entry.options:
        _LOGGER.info("First-run initialization: Migrating default setup variables to options.")
        new_options = {
            "refresh_interval": entry.data.get("refresh_interval", 24),
            "days_to_fetch": entry.data.get("days_to_fetch", 14),
            "show_no_school": entry.data.get("show_no_school", True),
            "show_completed_homework": entry.data.get("show_completed_homework", True),
        }
        hass.config_entries.async_update_entry(entry, options=new_options)
    
    # 1. Initialize the coordinator
    coordinator = ClassChartsCoordinator(hass, entry)
    
    # 2. Get initial data (with error handling)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady(f"Error communicating with Class Charts: {err}") from err

    # 3. Store coordinator for use in sensors/calendars
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # 4. Register the listener for Option Flow changes
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    # 5. Load the sensors and calendars
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update and reload integration immediately."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Clean up stored data
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok
