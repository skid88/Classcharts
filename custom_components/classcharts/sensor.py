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
    
    # Registering all three sensors at once
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
        # Unique ID prevents "Ghost" entity conflicts
        self._attr_unique_id = f"{coordinator.entry.entry_id}_lesson_{sensor_type}"
        self.sensor_type = sensor_type

    @property
    def state(self):
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return "No Data"

        # Dig into the 'timetable' key from the Coordinator dictionary
        timetable = self.coordinator.data.get("timetable", {})
        
        # If the key is missing entirely, show a specific status
        if not timetable and not isinstance(timetable, dict):
            _LOGGER.error("Class Charts: 'timetable' key missing in coordinator data")
            return "Key Error"

        now = dt_util.now()
        lessons = []

        # Parse the timetable data
        for date_str, day_lessons in timetable.items():
            if not isinstance(day_lessons, list):
                continue
            for lesson in day_lessons:
                try:
                    st_raw = lesson.get("start_time")
                    et_raw = lesson.get("end_time")
                    if not st_raw or not et_raw:
                        continue

                    # Flexible time parsing for different API formats
                    try:
                        st = datetime.fromisoformat(st_raw)
                        et = datetime.fromisoformat(et_raw)
                    except ValueError:
                        # Fallback: combine date key with HH:MM:SS
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

        # Sort all lessons by time to find current/next
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

        return None

class ClassChartsHomeworkSensor(CoordinatorEntity, SensorEntity):
    """Representation of the Homework sensor."""

    def __init__(self, coordinator, pupil_id):
        super().__init__(coordinator)
        self._attr_name = "Homework To-Do"
        self._attr_unique_id = f"{pupil_id}_homework"
        self._attr_icon = "mdi:book-open-variant"

    @property
    def native_value(self):
        """Return the count of homework tasks."""
        # This reaches into the data we fetched in __init__.py
        data = self.coordinator.data.get("homework", {})
        
        # Class Charts returns homework in a 'data' list inside the homework object
        tasks = data.get("data", [])
        
        if isinstance(tasks, list):
            return len(tasks)
        return 0

    @property
    def extra_state_attributes(self):
        """Return the detailed list of tasks as attributes."""
        data = self.coordinator.data.get("homework", {})
        tasks = data.get("data", [])
        
        homework_list = []
        for hw in tasks:
            homework_list.append({
                "title": hw.get("title"),
                "subject": hw.get("subject", {}).get("name"),
                "due": hw.get("due_date"),
                "status": hw.get("status", {}).get("state")
            })
            
        return {
            "tasks": homework_list,
            "total_completed_this_week": data.get("meta", {}).get("completed_count", 0)
        }
