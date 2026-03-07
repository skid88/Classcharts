import logging
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up all Class Charts sensors with advanced error handling."""
    coordinator = hass.data["classcharts"][entry.entry_id]
    
    async_add_entities([
        CCHomeworkOutstanding(coordinator, entry.entry_id),
        CCHomeworkCompleted(coordinator, entry.entry_id),
        CCHomeworkTotal(coordinator, entry.entry_id),
        CCTimetableMain(coordinator, entry.entry_id),
        CCCurrentLesson(coordinator, entry.entry_id),
        CCNextLesson(coordinator, entry.entry_id)
    ], True)

# --- HOMEWORK SENSORS ---
class CCHomeworkOutstanding(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Homework Outstanding"
        self._attr_unique_id = f"{entry_id}_outstanding_v13"
        self._attr_icon = "mdi:alert-circle-outline"
        self._attr_native_unit_of_measurement = "Tasks"

    @property
    def native_value(self):
        hw_root = self.coordinator.data.get("homework", {})
        items = hw_root.get("data", []) if isinstance(hw_root, dict) else []
        now = datetime.now()
        end_of_week = (now + timedelta(days=6 - now.weekday())).replace(hour=23, minute=59, second=59)
        count = 0
        for hw in items:
            if hw.get("status", {}).get("ticked") != "yes":
                try:
                    due_date = datetime.strptime(hw.get("due_date")[:10], "%Y-%m-%d")
                    if due_date <= end_of_week: count += 1
                except: continue
        return count

class CCHomeworkCompleted(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Homework Completed"
        self._attr_unique_id = f"{entry_id}_completed_v13"
        self._attr_icon = "mdi:check-circle-outline"
        self._attr_native_unit_of_measurement = "Tasks"

    @property
    def native_value(self):
        hw_root = self.coordinator.data.get("homework", {})
        items = hw_root.get("data", []) if isinstance(hw_root, dict) else []
        now = datetime.now()
        end_of_week = (now + timedelta(days=6 - now.weekday())).replace(hour=23, minute=59, second=59)
        count = 0
        for hw in items:
            if hw.get("status", {}).get("ticked") == "yes":
                try:
                    due_date = datetime.strptime(hw.get("due_date")[:10], "%Y-%m-%d")
                    if due_date <= end_of_week: count += 1
                except: continue
        return count

class CCHomeworkTotal(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Homework Total Due"
        self._attr_unique_id = f"{entry_id}_total_due_v13"
        self._attr_icon = "mdi:book-open-variant"
        self._attr_native_unit_of_measurement = "Tasks"

    @property
    def native_value(self):
        hw_root = self.coordinator.data.get("homework", {})
        items = hw_root.get("data", []) if isinstance(hw_root, dict) else []
        now = datetime.now()
        end_of_week = (now + timedelta(days=6 - now.weekday())).replace(hour=23, minute=59, second=59)
        count = 0
        for hw in items:
            try:
                due_date = datetime.strptime(hw.get("due_date")[:10], "%Y-%m-%d")
                if due_date <= end_of_week: count += 1
            except: continue
        return count

# --- TIMETABLE SENSORS ---
class CCTimetableMain(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Timetable"
        self._attr_unique_id = f"{entry_id}_timetable_v13"
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self):
        return len(self.coordinator.data.get("timetable", []))

class CCCurrentLesson(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Current Lesson"
        self._attr_unique_id = f"{entry_id}_current_v13"
        self._attr_icon = "mdi:school-outline"

    @property
    def native_value(self):
        try:
            lessons = self.coordinator.data.get("timetable", [])
            if lessons and len(lessons) > 0:
                return lessons[0].get("subject", {}).get("name", "Unknown")
        except Exception:
            pass
        return "No Lessons Today"

class CCNextLesson(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Next Lesson"
        self._attr_unique_id = f"{entry_id}_next_v13"
        self._attr_icon = "mdi:school"

    @property
    def native_value(self):
        try:
            lessons = self.coordinator.data.get("timetable", [])
            if lessons and len(lessons) > 1:
                return lessons[1].get("subject", {}).get("name", "Unknown")
        except Exception:
            pass
        return "No More Lessons"
