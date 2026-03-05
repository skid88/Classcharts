import logging
from datetime import datetime
import homeassistant.util.dt as dt_util
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Class Charts sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ClassChartsLessonSensor(coordinator, "Current Lesson", "current"),
        ClassChartsLessonSensor(coordinator, "Next Lesson", "next")
    ])

class ClassChartsLessonSensor(CoordinatorEntity, SensorEntity):
    """Sensor that displays the current or next lesson."""

    def __init__(self, coordinator, name, sensor_type):
        super().__init__(coordinator)
        self._attr_name = f"Class Charts {name}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{sensor_type}"
        self.sensor_type = sensor_type

    @property
    def state(self):
        """Return the state of the sensor."""
        now = dt_util.now()
        lessons = []
        
        # Flatten all fetched days into one list of lessons
        for date_str, day_lessons in self.coordinator.data.items():
            for lesson in day_lessons:
                try:
                    st = datetime.fromisoformat(lesson["start_time"])
                    et = datetime.fromisoformat(lesson["end_time"])
                    lessons.append({
                        "name": lesson.get("subject_name", "Unknown"),
                        "room": lesson.get("room_name", "N/A"),
                        "teacher": lesson.get("teacher_name", "Unknown"),
                        "start": dt_util.as_local(st),
                        "end": dt_util.as_local(et)
                    })
                except (KeyError, ValueError):
                    continue

        # Sort by start time
        lessons.sort(key=lambda x: x["start"])

        if self.sensor_type == "current":
            for l in lessons:
                if l["start"] <= now <= l["end"]:
                    return f"{l['name']} ({l['room']})"
            return "No Lesson"

        if self.sensor_type == "next":
            for l in lessons:
                if l["start"] > now:
                    return f"{l['name']} at {l['start'].strftime('%H:%M')}"
            return "No More Lessons"

        return None

    @property
    def extra_state_attributes(self):
        """Add extra details like teacher and room as attributes."""
        # You can expand this to show more data in the 'more-info' dialog
        return {"pupil_id": self.coordinator.entry.data.get("pupil_id")}
