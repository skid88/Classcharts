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

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        data = self.coordinator.data
        if not data or "data" not in data:
            return {}

        homework_items = data.get("data", [])
        
        # Date Logic
        now = datetime.now()
        # Calculate the end of the current week (Sunday night)
        end_of_week = (now + timedelta(days=6 - now.weekday())).replace(hour=23, minute=59, second=59)
        
        this_week_due_count = 0
        this_week_outstanding_count = 0
        this_week_completed_count = 0
        all_outstanding_tasks = []

        for hw in homework_items:
            # 1. Status Check (Based on your API dump)
            status = hw.get("status", {})
            is_ticked = status.get("ticked") == "yes"
            
            # 2. Date Parsing
            due_date_str = hw.get("due_date")
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            except (ValueError, TypeError):
                continue

            # 3. Categorization
            # Logic: If it's due before or on the end of this Sunday
            if due_date <= end_of_week:
                this_week_due_count += 1
                if is_ticked:
                    this_week_completed_count += 1
                else:
                    this_week_outstanding_count += 1

            # 4. Build the "Active Tasks" list for the UI
            if not is_ticked:
                all_outstanding_tasks.append({
                    "title": hw.get("title"),
                    "subject": hw.get("subject"),
                    "due_date": due_date_str,
                    "teacher": hw.get("teacher")
                })

        return {
            "this_week_due_count": this_week_due_count,
            "this_week_outstanding_count": this_week_outstanding_count,
            "this_week_completed_count": this_week_completed_count,
            "tasks": all_outstanding_tasks,
            "last_synced": now.strftime("%Y-%m-%d %H:%M:%S")
        }

    @property
    def native_value(self):
        """Return the state of the sensor (Total Outstanding)."""
        # This will be the main number shown on the sensor card
        return self.extra_state_attributes.get("this_week_outstanding_count", 0)
