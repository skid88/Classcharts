from __future__ import annotations
import logging
from datetime import datetime, date

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Class Charts sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities([
        CCHomeworkSensor(coordinator, entry, "Outstanding Homework", "this_week_outstanding_count"),
        CCHomeworkSensor(coordinator, entry, "Homework Due", "this_week_due_count"),
        CCHomeworkSensor(coordinator, entry, "Completed Homework", "this_week_completed_count"),
        CCLessonSensor(coordinator, entry, "current"),
        CCLessonSensor(coordinator, entry, "next"),
        # New split sensors
        CCBehaviourSensor(coordinator, entry, "Behaviour Balance", "balance"),
        CCBehaviourSensor(coordinator, entry, "Behaviour Points", "breakdown"),
    ])

# ... [Keep CCHomeworkSensor and CCLessonSensor as they were] ...

class CCBehaviourSensor(CoordinatorEntity, SensorEntity):
    """Sensor tracking behaviour points from separate activity/behaviour endpoints."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:star-circle"

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

    @property
    def native_value(self):
        """Calculate total positive points from the /behaviour timeline."""
        # The coordinator now holds 'behaviour_data' (from /behaviour)
        data = self.coordinator.data.get("behaviour_data", {}).get("data", {})
        timeline = data.get("timeline", [])
        
        total_pos = sum(item.get("positive", 0) for item in timeline)
        total_neg = sum(item.get("negative", 0) for item in timeline)
        
        return (total_pos - total_neg) if self._sensor_type == "balance" else total_pos

    @property
    def extra_state_attributes(self) -> dict:
        """Map detailed activity and reasons to attributes."""
        # The coordinator now holds 'activity_data' (from /activity)
        activity_list = self.coordinator.data.get("activity_data", {}).get("data", [])
        behaviour_data = self.coordinator.data.get("behaviour_data", {}).get("data", {})

        # Slim down the activity list for display
        slimmed_history = [
            {
                "reason": item.get("reason"),
                "points": item.get("score"),
                "teacher": item.get("teacher_name"),
                "timestamp": item.get("timestamp")
            } for item in activity_list[:5]
        ]

        return {
            "points_history": slimmed_history,
            "positive_reasons": behaviour_data.get("positive_reasons", {}),
            "last_updated": datetime.now().isoformat()
        }
