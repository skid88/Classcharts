import logging
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

_LOGGER = logging.getLogger(__name__)

class ClassChartsHomeworkSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Class Charts Homework."""

    def __init__(self, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Class Charts Homework"
        self._attr_unique_id = f"{coordinator.pupil_id}_homework"
        self._attr_native_unit_of_measurement = "Tasks"
        self._attr_icon = "mdi:book-open-variant"
        # Initialize internal storage to prevent None errors
        self._state_data = {}

    def _update_internal_state(self):
        """Calculate all homework metrics once."""
        data = self.coordinator.data
        if not data or "data" not in data:
            return {
                "this_week_due_count": 0,
                "this_week_outstanding_count": 0,
                "this_week_completed_count": 0,
                "tasks": []
            }

        homework_items = data.get("data", [])
        now = datetime.now()
        # End of current week (Sunday night)
        end_of_week = (now + timedelta(days=6 - now.weekday())).replace(hour=23, minute=59, second=59)
        
        counts = {
            "this_week_due_count": 0,
            "this_week_outstanding_count": 0,
            "this_week_completed_count": 0,
            "tasks": [],
            "last_synced": now.strftime("%Y-%m-%d %H:%M:%S")
        }

        for hw in homework_items:
            status = hw.get("status", {})
            is_ticked = status.get("ticked") == "yes"
            
            due_date_str = hw.get("due_date")
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                continue

            # Check if due by end of Sunday
            if due_date <= end_of_week:
                counts["this_week_due_count"] += 1
                if is_ticked:
                    counts["this_week_completed_count"] += 1
                else:
                    counts["this_week_outstanding_count"] += 1

            # Keep list of everything not ticked (even future stuff)
            if not is_ticked:
                counts["tasks"].append({
                    "title": hw.get("title"),
                    "subject": hw.get("subject"),
                    "due_date": due_date_str,
                    "teacher": hw.get("teacher")
                })
        
        return counts

    @property
    def native_value(self):
        """Return the state (Outstanding tasks)."""
        self._state_data = self._update_internal_state()
        return self._state_data.get("this_week_outstanding_count", 0)

    @property
    def extra_state_attributes(self):
        """Return the attributes calculated in native_value."""
        return self._state_data
