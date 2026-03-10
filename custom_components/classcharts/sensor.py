import logging
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Class Charts sensors. Outstanding is now first for priority."""
    coordinator = hass.data["classcharts"][entry.entry_id]
    
    # We define the list first to ensure all are included
    entities = [
        CCHomeworkOutstanding(coordinator, entry.entry_id),
        CCHomeworkCompleted(coordinator, entry.entry_id),
        CCHomeworkTotal(coordinator, entry.entry_id),
        CCTimetableMain(coordinator, entry.entry_id),
        CCCurrentLesson(coordinator, entry.entry_id),
        CCNextLesson(coordinator, entry.entry_id)
    ]
    
    async_add_entities(entities, True)

# --- 1. OUTSTANDING HOMEWORK (Meta Map) ---
class CCHomeworkOutstanding(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Homework Outstanding"
        self._attr_unique_id = f"{entry_id}_hw_combined_v34"
        self._attr_icon = "mdi:clipboard-list"
        self._attr_native_unit_of_measurement = "Tasks"

    @property
    def native_value(self):
        """The main number shown on your dashboard."""
        try:
            hw_data = self.coordinator.data.get("homework", {})
            return hw_data.get("meta", {}).get("this_week_outstanding_count", 0)
        except:
            return 0

    @property
    def extra_state_attributes(self):
        """The 'Ultimate List' data stored inside this same sensor."""
        try:
            hw_items = self.coordinator.data.get("homework", {}).get("data", [])
            tasks = []
            for hw in hw_items:
                # We filter to only include Outstanding tasks in this specific list
                if hw.get("status", {}).get("ticked") != "yes":
                    tasks.append({
                        "subject": hw.get("subject", {}).get("name", "Unknown"),
                        "title": hw.get("title", "No Title"),
                        "due_date": hw.get("due_date", "")[:10],
                        "teacher": hw.get("teacher", {}).get("name", "Unknown"),
                        "lesson": hw.get("lesson", "N/A")
                    })
            
            # Sort by due date
            tasks.sort(key=lambda x: x["due_date"])
            return {"tasks_list": tasks}
        except Exception:
            return {"tasks_list": []}

# --- 2. COMPLETED HOMEWORK (Meta Map) ---
class CCHomeworkCompleted(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Homework Completed"
        self._attr_unique_id = f"{entry_id}_completed_v30"
        self._attr_icon = "mdi:check-circle-outline"
        self._attr_native_unit_of_measurement = "Tasks"

    @property
    def native_value(self):
        try:
            # Drills into homework -> meta -> this_week_completed_count
            hw_data = self.coordinator.data.get("homework", {})
            meta = hw_data.get("meta", {})
            return meta.get("this_week_completed_count", 0)
        except Exception:
            return 0

# --- 3. TOTAL HOMEWORK (Meta Map) ---
class CCHomeworkTotal(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Homework Total Due"
        self._attr_unique_id = f"{entry_id}_total_due_v30"
        self._attr_icon = "mdi:book-open-page-variant"
        self._attr_native_unit_of_measurement = "Tasks"

    @property
    def native_value(self):
        try:
            # Drills into homework -> meta -> this_week_due_count
            hw_data = self.coordinator.data.get("homework", {})
            meta = hw_data.get("meta", {})
            return meta.get("this_week_due_count", 0)
        except Exception:
            return 0
# --- 4. TIMETABLE COUNT ---
class CCTimetableMain(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Timetable"
        self._attr_unique_id = f"{entry_id}_timetable_v25"
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self):
        try:
            return len(self.coordinator.data.get("timetable", []))
        except: return 0

# --- 5. CURRENT LESSON ---
class CCCurrentLesson(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Current Lesson"
        self._attr_unique_id = f"{entry_id}_current_v25"
        self._attr_icon = "mdi:school-outline"

    @property
    def native_value(self):
        try:
            lessons = self.coordinator.data.get("timetable", [])
            # Explicit length check to prevent KeyError: 0
            if lessons and len(lessons) > 0:
                return lessons[0].get("subject", {}).get("name", "Unknown")
            return "No Lessons Today"
        except: return "No Lessons Today"

# --- 6. NEXT LESSON ---
class CCNextLesson(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Next Lesson"
        self._attr_unique_id = f"{entry_id}_next_v25"
        self._attr_icon = "mdi:school"

    @property
    def native_value(self):
        try:
            lessons = self.coordinator.data.get("timetable", [])
            # Explicit length check to prevent KeyError: 1
            if lessons and len(lessons) > 1:
                return lessons[1].get("subject", {}).get("name", "Unknown")
            return "No More Lessons"
        except: return "No More Lessons"
