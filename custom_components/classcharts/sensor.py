import logging
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up all 6 Class Charts sensors."""
    coordinator = hass.data["classcharts"][entry.entry_id]
    
    async_add_entities([
        CCHomeworkOutstanding(coordinator),
        CCHomeworkCompleted(coordinator),
        CCHomeworkTotal(coordinator),
        CCTimetableMain(coordinator),
        CCCurrentLesson(coordinator),
        CCNextLesson(coordinator)
    ], True)

# --- 1, 2, 3: HOMEWORK SENSORS ---
class CCHomeworkOutstanding(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Homework Outstanding This Week"
        self._attr_unique_id = f"{coordinator.pupil_id}_hw_outstanding_v4"
        self._attr_native_unit_of_measurement = "Tasks"
        self._attr_icon = "mdi:alert-circle-outline"

    @property
    def native_value(self):
        data = self.coordinator.data.get("homework", {}).get("data", [])
        now = datetime.now()
        end_of_week = (now + timedelta(days=6 - now.weekday())).replace(hour=23, minute=59, second=59)
        return sum(1 for hw in data if hw.get("status", {}).get("ticked") != "yes" and 
                   datetime.strptime(hw.get("due_date"), "%Y-%m-%d") <= end_of_week)

class CCHomeworkCompleted(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Homework Completed This Week"
        self._attr_unique_id = f"{coordinator.pupil_id}_hw_completed_v4"
        self._attr_native_unit_of_measurement = "Tasks"
        self._attr_icon = "mdi:check-circle-outline"

    @property
    def native_value(self):
        data = self.coordinator.data.get("homework", {}).get("data", [])
        now = datetime.now()
        end_of_week = (now + timedelta(days=6 - now.weekday())).replace(hour=23, minute=59, second=59)
        return sum(1 for hw in data if hw.get("status", {}).get("ticked") == "yes" and 
                   datetime.strptime(hw.get("due_date"), "%Y-%m-%d") <= end_of_week)

class CCHomeworkTotal(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Homework Total Due This Week"
        self._attr_unique_id = f"{coordinator.pupil_id}_hw_total_v4"
        self._attr_native_unit_of_measurement = "Tasks"
        self._attr_icon = "mdi:book-open-variant"

    @property
    def native_value(self):
        data = self.coordinator.data.get("homework", {}).get("data", [])
        now = datetime.now()
        end_of_week = (now + timedelta(days=6 - now.weekday())).replace(hour=23, minute=59, second=59)
        return sum(1 for hw in data if datetime.strptime(hw.get("due_date"), "%Y-%m-%d") <= end_of_week)

# --- 4: TIMETABLE SENSOR ---
class CCTimetableMain(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Timetable"
        self._attr_unique_id = f"{coordinator.pupil_id}_timetable_v4"
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self):
        return len(self.coordinator.data.get("timetable", []))

# --- 5: CURRENT LESSON ---
class CCCurrentLesson(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Current Lesson"
        self._attr_unique_id = f"{coordinator.pupil_id}_current_lesson_v4"
        self._attr_icon = "mdi:school-outline"

    @property
    def native_value(self):
        lessons = self.coordinator.data.get("timetable", [])
        if not lessons: return "No Lesson"
        # Usually, the first lesson in the list is the current one during school hours
        return lessons[0].get("subject", {}).get("name", "Unknown")

# --- 6: NEXT LESSON ---
class CCNextLesson(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Next Lesson"
        self._attr_unique_id = f"{coordinator.pupil_id}_next_lesson_v4"
        self._attr_icon = "mdi:school"

    @property
    def native_value(self):
        lessons = self.coordinator.data.get("timetable", [])
        # If there are 2 or more lessons, the second one (index 1) is the "next" one
        if len(lessons) < 2: return "No More Lessons"
        return lessons[1].get("subject", {}).get("name", "Unknown")
