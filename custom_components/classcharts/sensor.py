from __future__ import annotations
from datetime import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.util import dt as dt_util
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        CCHomeworkSensor(coordinator, entry, "outstanding", "this_week_outstanding_count"),
        CCLessonSensor(coordinator, entry, "current"),
        CCLessonSensor(coordinator, entry, "next")
    ])

class CCLessonSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry, type):
        super().__init__(coordinator)
        self._type = type
        self._attr_name = f"Class Charts {type.capitalize()} Lesson"
        self._attr_unique_id = f"{entry.entry_id}_lesson_{type}"

    @property
    def native_value(self):
        # FIX: Use dt_util.now() instead of datetime.now()
        now = dt_util.now() 
        today_str = now.strftime("%Y-%m-%d")
        today_lessons = self.coordinator.data.get("timetable", {}).get(today_str, [])
        
        parsed = []
        for l in today_lessons:
            try:
                # FIX: Ensure these are converted to local/aware datetimes
                start_naive = datetime.fromisoformat(l["start_time"])
                end_naive = datetime.fromisoformat(l["end_time"])
                
                l["dt_start"] = dt_util.as_local(start_naive)
                l["dt_end"] = dt_util.as_local(end_naive)
                parsed.append(l)
            except (KeyError, ValueError, TypeError):
                continue
        
        parsed.sort(key=lambda x: x["dt_start"])
        
        if self._type == "current":
            for l in parsed:
                # Now both sides of the '<=' have timezones, so they can be compared!
                if l["dt_start"] <= now <= l["dt_end"]:
                    return l["subject_name"]
        else: # next
            for l in parsed:
                if l["dt_start"] > now:
                    return l["subject_name"]
                    
        return "Free"
