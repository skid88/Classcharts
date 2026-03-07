import logging
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up all 6 Class Charts sensors via a dynamic list."""
    coordinator = hass.data["classcharts"][entry.entry_id]
    
    # We define the sensors here with distinct 'type' tags
    sensors = [
        ("outstanding", "Homework Outstanding This Week", "mdi:alert-circle-outline"),
        ("completed", "Homework Completed This Week", "mdi:check-circle-outline"),
        ("due_total", "Homework Total Due This Week", "mdi:book-open-variant"),
        ("timetable", "Class Charts Timetable", "mdi:calendar-clock"),
        ("current", "Class Charts Current Lesson", "mdi:school-outline"),
        ("next", "Class Charts Next Lesson", "mdi:school"),
    ]
    
    # We pass the entry.entry_id as a backup unique ID
    async_add_entities(
        [ClassChartsMultiSensor(coordinator, entry.entry_id, s[0], s[1], s[2]) for s in sensors], 
        True
    )

class ClassChartsMultiSensor(CoordinatorEntity, SensorEntity):
    """A generic sensor class that branches into 6 different types."""

    def __init__(self, coordinator, entry_id, sensor_type, name, icon):
        super().__init__(coordinator)
        self._type = sensor_type
        self._attr_name = name
        self._attr_icon = icon
        
        # FIX: We use entry_id instead of pupil_id to prevent the 'AttributeError'
        self._attr_unique_id = f"{entry_id}_{sensor_type}_v6"
        
        # Set units only for homework sensors
        if "Homework" in name:
            self._attr_native_unit_of_measurement = "Tasks"

    @property
    def native_value(self):
        """The core logic for all 6 sensors."""
        data = self.coordinator.data
        if not data:
            return None

        # --- HOMEWORK LOGIC ---
        if self._type in ["outstanding", "completed", "due_total"]:
            # Check if homework is nested or direct
            hw_root = data.get("homework", data)
            hw_items = hw_root.get("data", []) if isinstance(hw_root, dict) else []
            
            now = datetime.now()
            end_of_week = (now + timedelta(days=6 - now.weekday())).replace(hour=23, minute=59, second=59)
            
            total = 0
            done = 0
            todo = 0
            
            for hw in hw_items:
                try:
                    due = datetime.strptime(hw.get("due_date"), "%Y-%m-%d")
                    if due <= end_of_week:
                        total += 1
                        if hw.get("status", {}).get("ticked") == "yes":
                            done += 1
                        else:
                            todo += 1
                except: continue
                
            if self._type == "outstanding": return todo
            if self._type == "completed": return done
            return total

        # --- TIMETABLE LOGIC ---
        timetable = data.get("timetable", [])
        if self._type == "timetable":
            return len(timetable)
            
        if not timetable: return "No Lessons Today"
        
        if self._type == "current":
            first_lesson = timetable[0]
            return first_lesson.get("subject", {}).get("name", "Unknown")
        
        if self._type == "next":
            if len(timetable) > 1:
                return timetable[1].get("subject", {}).get("name", "Unknown")
            return "No More Lessons"

        return None
