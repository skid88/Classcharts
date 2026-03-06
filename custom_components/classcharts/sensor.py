import logging
from datetime import datetime
import homeassistant.util.dt as dt_util
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Class Charts sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    _LOGGER.debug("Registering Class Charts sensors for entry: %s", entry.entry_id)
    
    # We add them as a list. Note the commas at the end of each line.
    async_add_entities([
        ClassChartsLessonSensor(coordinator, "Current Lesson", "current"),
        ClassChartsLessonSensor(coordinator, "Next Lesson", "next"),
        ClassChartsHomeworkSensor(coordinator)
    ])

class ClassChartsLessonSensor(CoordinatorEntity, SensorEntity):
    """Sensor for current/next lessons."""

    def __init__(self, coordinator, name, sensor_type):
        super().__init__(coordinator)
        self._attr_name = name
        # We add 'lesson' to the ID to ensure it never clashes with the homework sensor
        self._attr_unique_id = f"{coordinator.entry.entry_id}_lesson_{sensor_type}"
        self.sensor_type = sensor_type

    @property
    def state(self):
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return "No Data"

        # Dig into the 'timetable' key we created in __init__.py
        timetable = self.coordinator.data.get("timetable", {})
        now = dt_util.now()
        lessons = []

        for date_str, day_lessons in timetable.items():
            if not isinstance(day_lessons, list):
                continue
            for lesson in day_lessons:
                try:
                    st_raw = lesson.get("start_time")
                    et_raw = lesson.get("end_time")
                    if not st_raw or not et_raw: continue

                    # Flexible time parsing
                    try:
                        st = datetime.fromisoformat(st_raw)
                        et = datetime.fromisoformat(et_raw)
                    except ValueError:
                        st = datetime.strptime(f"{date_str} {st_raw}", "%Y-%m-%d %H:%M:%S")
                        et = datetime.strptime(f"{date_str} {et_raw}", "%Y-%m-%d %H:%M:%S")

                    lessons.append({
                        "name": lesson.get("subject_name", "Unknown"),
                        "room": lesson.get("room_name", "N/A"),
                        "start": dt_util.as_local(st),
                        "end": dt_util.as_local(et)
                    })
                except Exception:
                    continue

        if not lessons:
            return "No Lessons Found"

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
            return "No More Lessons Today"

class ClassChartsHomeworkSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Homework count."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Homework To-Do"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_homework_stat"
        self._attr_icon = "mdi:book-open-variant"

    @property
    def native_value(self):
        """Return the count from the 'homework' -> 'meta' path."""
        if not self.coordinator.data: return 0
        return self.coordinator.data.get("homework", {}).get("meta", {}).get("this_week_outstanding_count", 0)

    @property
    def extra_state_attributes(self):
        """List individual tasks in the attributes."""
        hw_data = self.coordinator.data.get("homework", {}).get("data", [])
        return {"tasks": [
            {"title": i.get("title"), "due": i.get("due_date")} 
            for i in hw_data if i.get("status", {}).get("state") != "completed"
        ]}
