from __future__ import annotations
import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

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
        CCBehaviourSensor(coordinator, entry, "Behaviour Balance", "balance"),
        CCBehaviourSensor(coordinator, entry, "Behaviour Points", "breakdown")
    ])

class CCHomeworkSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Homework stats with attribute list for Markdown."""
    
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
        """Return the state of the sensor safely, guarding against boot-up lists."""
        if not self.coordinator.data or not isinstance(self.coordinator.data, dict):
            return 0

        homework = self.coordinator.data.get("homework", {})
        if not isinstance(homework, dict):
            return 0

        meta = homework.get("meta", {})
        if not isinstance(meta, dict):
            return 0

        return meta.get(self._key, 0)

    @property
    def extra_state_attributes(self):
        """This provides the slimmed-down data for your Markdown card."""
        if not self.coordinator.data or not isinstance(self.coordinator.data, dict):
            return {"homework_list": []}

        hw = self.coordinator.data.get("homework", {})
        raw_homework_list = hw.get("data", [])
        
        if not isinstance(raw_homework_list, list):
            return {"homework_list": []}

        slimmed_homework_list = []
        for item in raw_homework_list:
            if not isinstance(item, dict):
                continue
                
            status_data = item.get("status", {})
            status_str = status_data.get("state") if isinstance(status_data, dict) else item.get("status")
            
            subject_data = item.get("subject", {})
            subject_str = subject_data.get("name") if isinstance(subject_data, dict) else item.get("subject")

            slimmed_hw = {
                "title": item.get("title"),
                "subject": subject_str,
                "teacher": item.get("teacher"),
                "due_date": item.get("due_date"),
                "status": status_str,
                "description": item.get("description", "")[:100] + "..." if item.get("description") else ""
            }
            slimmed_homework_list.append(slimmed_hw)

        return {"homework_list": slimmed_homework_list}

class CCLessonSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Lessons."""
    
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
        now = dt_util.now()
        today_str = now.strftime("%Y-%m-%d")
        timetable = self.coordinator.data.get("timetable", {})
        today_lessons = timetable.get(today_str, [])
        
        parsed = []
        for l in today_lessons:
            try:
                start_naive = datetime.fromisoformat(l["start_time"])
                end_naive = datetime.fromisoformat(l["end_time"])
                l["dt_start"] = dt_util.as_local(start_naive)
                l["dt_end"] = dt_util.as_local(end_naive)
                parsed.append(l)
            except:
                continue
        
        parsed.sort(key=lambda x: x["dt_start"])
        
        if self._type == "current":
            for l in parsed:
                if l["dt_start"] <= now <= l["dt_end"]:
                    return l["subject_name"]
        else:
            for l in parsed:
                if l["dt_start"] > now:
                    return l["subject_name"]
        return "Free"

class CCBehaviourSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Tracking Behaviour points matching the pupil_data model."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, name, sensor_type):
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        student_label = entry.data.get("student_name") or entry.data.get("pupil_id")
        
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_behaviour_{sensor_type}"
        self._attr_icon = "mdi:star-circle" if sensor_type == "balance" else "mdi:counter"
        
        # Configure units dynamically based on what the sensor state shows
        if sensor_type == "latest_date":
            self._attr_device_class = "date"
        else:
            self._attr_native_unit_of_measurement = "Points"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)}, 
            "name": f"Class Charts ({student_label})"
        }

    @property
    def pupil_data(self):
        """Helper property to safely check data structure variations."""
        if not self.coordinator.data or not isinstance(self.coordinator.data, dict):
            return None
        # Fallback helper to grab the data object handled by your custom model classes
        return self.coordinator.data.get("behaviour") or self.coordinator.data

    @property
    def native_value(self):
        """Return values matching the specific entity profiles."""
        from datetime import datetime, date
        data = self.pupil_data
        if not data:
            return 0 if self._sensor_type != "latest_date" else None

        # Fetch underlying lists safely out of your existing model architecture
        events = getattr(data, "behaviour_events", []) or []
        timeline = getattr(data, "behaviour_timeline", []) or []

        # 1. PROFILE: Latest Point Date Sensor
        if self._sensor_type == "latest_date":
            if events:
                latest = next((e for e in events if isinstance(e, dict) and e.get("timestamp")), None)
                if latest is not None:
                    try:
                        return date.fromisoformat(latest["timestamp"][:10])
                    except (ValueError, TypeError):
                        pass
            if timeline:
                for week in reversed(timeline):
                    if isinstance(week, dict) and week.get("end"):
                        try:
                            return date.fromisoformat(week["end"])
                        except (ValueError, TypeError):
                            continue
            return None

        # 2. CALCULATE MATH: Loop through items to resolve all-time point scores
        all_time_pos = 0
        all_time_neg = 0
        if isinstance(events, list):
            for item in events:
                if not isinstance(item, dict):
                    continue
                score = int(item.get("score") or item.get("points") or item.get("value") or 0)
                if score > 0:
                    all_time_pos += score
                elif score < 0:
                    all_time_neg += abs(score)

        if self._sensor_type == "balance":
            return all_time_pos - all_time_neg
        return all_time_pos

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose current week totals alongside full raw feed history listings."""
        from datetime import datetime, date
        attrs = {}
        data = self.pupil_data
        if not data:
            return attrs

        events = getattr(data, "behaviour_events", []) or []
        timeline = getattr(data, "behaviour_timeline", []) or []
        today = date.today()

        # Calculate this week's active scope totals from timeline entries
        this_week_positive = 0
        this_week_negative = 0
        for week in timeline:
            if not isinstance(week, dict):
                continue
            try:
                start = date.fromisoformat(week.get("start", ""))
                end = date.fromisoformat(week.get("end", ""))
                if start <= today <= end:
                    this_week_positive = week.get("positive", 0)
                    this_week_negative = week.get("negative", 0)
                    break
            except (ValueError, TypeError):
                continue

        attrs["this_week_positive"] = this_week_positive
        attrs["this_week_negative"] = this_week_negative

        # Build clean historical state attributes for UI components
        slimmed_history = []
        if isinstance(events, list):
            for item in events:
                if not isinstance(item, dict):
                    continue
                slimmed_history.append({
                    "reason": item.get("reason") or item.get("name") or "Unknown",
                    "points": item.get("score") or item.get("points") or 0,
                    "teacher": item.get("teacher") or item.get("teacher_name") or "Unknown",
                    "timestamp": item.get("timestamp") or item.get("date") or "Unknown"
                })

        attrs["points_history"] = slimmed_history
        return attrs
