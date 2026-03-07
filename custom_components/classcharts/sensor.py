import logging
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up all 6 Class Charts sensors with safety checks."""
    coordinator = hass.data["classcharts"][entry.entry_id]
    
    async_add_entities([
        CCHomeworkOutstanding(coordinator, entry.entry_id),
        CCHomeworkCompleted(coordinator, entry.entry_id),
        CCHomeworkTotal(coordinator, entry.entry_id),
        CCTimetableMain(coordinator, entry.entry_id),
        CCCurrentLesson(coordinator, entry.entry_id),
        CCNextLesson(coordinator, entry.entry_id)
    ], True)

# --- 1. OUTSTANDING ---
class CCHomeworkOutstanding(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Homework Outstanding"
        self._attr_unique_id = f"{entry_id}_outstanding_v12"
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
                    if due_date <= end_of_week:
                        count += 1
                except: continue
        return count

# --- 2. COMPLETED ---
class CCHomeworkCompleted(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Homework Completed"
        self._attr_unique_id = f"{entry_id}_completed_v12"
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
                    if due_date <= end_of_week:
                        count += 1
                except: continue
        return count

# --- 3. TOTAL DUE ---
class CCHomeworkTotal(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Homework Total Due"
        self._attr_unique_id = f"{entry_id}_total_due_v12"
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
                if due_date <= end_of_week:
                    count += 1
            except: continue
        return count

# --- 4. TIMETABLE ---
class CCTimetableMain(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Timetable"
        self._attr_unique_id = f"{entry_id}_timetable_v12"
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self):
        return len(self.coordinator.data.get("timetable", []))

# --- 5. CURRENT LESSON (CRASH FIX) ---
class CCCurrentLesson(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Current Lesson"
        self._attr_unique_id = f"{entry_id}_current_v12"
        self._attr_icon = "mdi:school-outline"

    @property
    def native_value(self):
        lessons = self.coordinator.data.get("timetable", [])
        # FIX: Check if the list is empty before accessing index 0
        if not lessons or not isinstance(lessons, list) or len(lessons) == 0:
            return "No Lessons Today"
        return lessons[0].get("subject", {}).get("name", "Unknown")

# --- 6. NEXT LESSON (CRASH FIX) ---
class CCNextLesson(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Next Lesson"
        self._attr_unique_id = f"{entry_id}_next_v12"
        self._attr_icon = "mdi:school"

    @property
    def native_value(self):
        lessons = self.coordinator.data.get("timetable", [])
        # FIX: Check if there is a second lesson before accessing index 1
        if not lessons or not isinstance(lessons, list) or len(lessons) < 2:
            return "No More Lessons"
        return lessons[1].get("subject", {}).get("name", "Unknown")
