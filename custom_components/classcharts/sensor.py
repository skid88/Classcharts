import logging
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up all Class Charts sensors (Homework, Timetable, Lessons)."""
    coordinator = hass.data["classcharts"][entry.entry_id]
    
    entities = [
        # The 3 Homework Sensors we built
        ClassChartsHomeworkSensor(coordinator, "outstanding"),
        ClassChartsHomeworkSensor(coordinator, "completed"),
        ClassChartsHomeworkSensor(coordinator, "due_total"),
        # The Timetable and Lesson Sensors
        ClassChartsTimetableSensor(coordinator),
        ClassChartsLessonSensor(coordinator)
    ]
    
    async_add_entities(entities, True)

# --- HOMEWORK SENSOR CLASS ---
class ClassChartsHomeworkSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Homework metrics."""
    def __init__(self, coordinator, sensor_type):
        super().__init__(coordinator)
        self.sensor_type = sensor_type
        self.pupil_id = coordinator.pupil_id
        
        names = {
            "outstanding": "Homework Outstanding This Week",
            "completed": "Homework Completed This Week",
            "due_total": "Homework Total Due This Week"
        }
        
        self._attr_name = names.get(sensor_type)
        self._attr_unique_id = f"{self.pupil_id}_homework_{sensor_type}"
        self._attr_native_unit_of_measurement = "Tasks"
        self._attr_icon = "mdi:book-open-variant"

    @property
    def native_value(self):
        data = self.coordinator.data.get("homework", {}).get("data", [])
        now = datetime.now()
        end_of_week = (now + timedelta(days=6 - now.weekday())).replace(hour=23, minute=59, second=59)

        outstanding = 0
        completed = 0
        total = 0

        for hw in data:
            is_ticked = hw.get("status", {}).get("ticked") == "yes"
            try:
                due_date = datetime.strptime(hw.get("due_date"), "%Y-%m-%d")
            except: continue

            if due_date <= end_of_week:
                total += 1
                if is_ticked: completed += 1
                else: outstanding += 1

        if self.sensor_type == "outstanding": return outstanding
        if self.sensor_type == "completed": return completed
        return total

# --- TIMETABLE SENSOR CLASS ---
class ClassChartsTimetableSensor(CoordinatorEntity, SensorEntity):
    """Sensor for the Daily Timetable."""
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Timetable"
        self._attr_unique_id = f"{coordinator.pupil_id}_timetable"
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self):
        # Returns the number of lessons today
        timetable = self.coordinator.data.get("timetable", [])
        return len(timetable)

    @property
    def extra_state_attributes(self):
        return {"lessons": self.coordinator.data.get("timetable", [])}

# --- LESSON SENSOR CLASS ---
class ClassChartsLessonSensor(CoordinatorEntity, SensorEntity):
    """Sensor for the Next/Current Lesson."""
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Next Lesson"
        self._attr_unique_id = f"{coordinator.pupil_id}_next_lesson"
        self._attr_icon = "mdi:school"

    @property
    def native_value(self):
        # Logic to find the current/next lesson from timetable data
        lessons = self.coordinator.data.get("timetable", [])
        if not lessons: return "No Lessons"
        return lessons[0].get("subject", {}).get("name", "Unknown")
