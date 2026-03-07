import logging
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up all 6 Class Charts sensors via a dynamic list."""
    coordinator = hass.data["classcharts"][entry.entry_id]
    
    # This list defines the 6 unique sensors
    sensor_definitions = [
        ("outstanding", "Homework Outstanding", "mdi:alert-circle-outline"),
        ("completed", "Homework Completed", "mdi:check-circle-outline"),
        ("due_total", "Homework Due", "mdi:book-open-variant"),
        ("timetable_count", "Class Charts Timetable", "mdi:calendar-clock"),
        ("current_lesson", "Class Charts Current Lesson", "mdi:school-outline"),
        ("next_lesson", "Class Charts Next Lesson", "mdi:school"),
    ]
    
    entities = []
    for sensor_type, name, icon in sensor_definitions:
        entities.append(ClassChartsMultiSensor(coordinator, entry.entry_id, sensor_type, name, icon))
    
    async_add_entities(entities, True)

class ClassChartsMultiSensor(CoordinatorEntity, SensorEntity):
    """A generic sensor class for all Class Charts data types."""

    def __init__(self, coordinator, entry_id, sensor_type, name, icon):
        super().__init__(coordinator)
        self._type = sensor_type
        self._name = name
        self._icon = icon
        
        # Unique ID to force them to be separate
        self._attr_unique_id = f"cc_{entry_id}_{sensor_type}_v7"
        self._attr_icon = icon
        
        # This tells HA to use the name exactly
        self._attr_name = name
        self._attr_has_entity_name = False 

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
        if self._type == "timetable_count":
            return len(timetable)
            
        if not timetable: return "No Lessons"
        
        if self._type == "current_lesson":
            return timetable[0].get("subject", {}).get("name", "Unknown")
        
        if self._type == "next_lesson":
            return timetable[1].get("subject", {}).get("name", "Unknown") if len(timetable) > 1 else "No More Lessons"

        return None
