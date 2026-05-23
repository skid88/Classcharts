from __future__ import annotations
import logging
from datetime import datetime, date

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class CCHomeworkSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, name, key):
        super().__init__(coordinator)
        self._key = key
        student_label = entry.data.get("student_name") or entry.data.get("pupil_id")
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_hw_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)}, 
            "name": f"Class Charts ({student_label})"
        }

    @property
    def native_value(self):
        if not self.coordinator.data or not isinstance(self.coordinator.data, dict):
            return 0
        homework = self.coordinator.data.get("homework", {})
        meta = homework.get("meta", {})
        return meta.get(self._key, 0)  
        
    @property
    def extra_state_attributes(self):
        """This provides the data for your Markdown card."""
        hw = self.coordinator.data.get("homework", {})
        return {"homework_list": hw.get("data", [])}    

class CCLessonSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, type):
        super().__init__(coordinator)
        self._type = type
        student_label = entry.data.get("student_name") or entry.data.get("pupil_id")
        self._attr_name = f"{type.capitalize()} Lesson"
        self._attr_unique_id = f"{entry.entry_id}_lesson_{type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)}, 
            "name": f"Class Charts ({student_label})"
        }

    @property
    def native_value(self):
        return "Unknown"

class CCBehaviourSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, name, sensor_type) -> None:
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        student_label = entry.data.get("student_name") or entry.data.get("pupil_id")
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_behaviour_{sensor_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)}, 
            "name": f"Class Charts ({student_label})"
        }
        self._attr_native_unit_of_measurement = "pts"
        self._attr_state_class = "measurement"

        # Dynamically set icons based on the type
        if sensor_type == "positive":
            self._attr_icon = "mdi:thumb-up"
        elif sensor_type == "negative":
            self._attr_icon = "mdi:thumb-down"
        else:
            self._attr_icon = "mdi:star-circle"

    @property
    def native_value(self):
        """Calculates values based on the /behaviour endpoint data structures."""
        if not self.coordinator.data or not isinstance(self.coordinator.data, dict):
            return 0

        data = self.coordinator.data.get("behaviour_data", {}).get("data", {})
        timeline = data.get("timeline", [])
        
        total_pos = sum(item.get("positive", 0) for item in timeline)
        total_neg = sum(item.get("negative", 0) for item in timeline)
        
        if self._sensor_type == "balance":
            return (total_pos - total_neg)
        elif self._sensor_type == "positive":
            return total_pos
        elif self._sensor_type == "negative":
            return total_neg
        else:
            return total_pos # fallback breakdown default

    @property
    def extra_state_attributes(self) -> dict:
        """Pulls detailed logs from /activity and summary reasons."""
        if not self.coordinator.data or not isinstance(self.coordinator.data, dict):
            return {}

        activity_list = self.coordinator.data.get("activity_data", {}).get("data", [])
        behaviour_data = self.coordinator.data.get("behaviour_data", {}).get("data", {})

        # Create a list of the 5 most recent events
        recent_log = [
            {
                "reason": item.get("reason"),
                "points": item.get("score"),
                "teacher": item.get("teacher_name"),
                "date": item.get("timestamp")
            } for item in activity_list[:5]
        ]

        return {
            "recent_activity": recent_log,
            "positive_reasons": behaviour_data.get("positive_reasons", {}),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M")
        }


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Class Charts sensors cleanly using the unified CC class."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities([
        CCHomeworkSensor(coordinator, entry, "Outstanding Homework", "this_week_outstanding_count"),
        CCHomeworkSensor(coordinator, entry, "Homework Due", "this_week_due_count"),
        CCHomeworkSensor(coordinator, entry, "Completed Homework", "this_week_completed_count"),
        CCLessonSensor(coordinator, entry, "current"),
        CCLessonSensor(coordinator, entry, "next"),
        CCBehaviourSensor(coordinator, entry, "Behaviour Balance", "balance"),
        CCBehaviourSensor(coordinator, entry, "Behaviour Positive", "positive"),
        CCBehaviourSensor(coordinator, entry, "Behaviour Negative", "negative"),
    ], update_before_add=True)
