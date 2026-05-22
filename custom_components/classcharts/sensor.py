from __future__ import annotations
import logging
from datetime import datetime, date

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
        CCBehaviourSensor(coordinator, entry, "Behaviour Points", "breakdown"),
        CCBehaviourSensor(coordinator, entry, "Latest Behaviour Update", "latest_date")
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
        """Placeholder for lesson state logic."""
        return "Unknown"


class CCBehaviourSensor(CoordinatorEntity, SensorEntity):
    """Sensor tracking behaviour points balance, metrics, and timeline updates."""

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
        
        # Adjust device and state classes depending on whether it's a date tracker or counter
        if self._sensor_type == "latest_date":
            self._attr_device_class = "date"
            self._attr_native_unit_of_measurement = None
            self._attr_state_class = None
        else:
            self._attr_device_class = None
            self._attr_native_unit_of_measurement = "pts"
            self._attr_state_class = "measurement"

    @property
    def extract_events_and_timeline(self) -> tuple[list, list]:
        """Normalize both object models and raw dict layouts into standard lists."""
        # This will dump the actual structure into your logs:
        _LOGGER.warning("=== CLASSCHARTS DEBUG PAYLOAD: %s ===", self.coordinator.data)

        if not self.coordinator.data:
            return [], []

        if isinstance(self.coordinator.data, dict):
            behaviour_node = self.coordinator.data.get("behaviour")
            
            if isinstance(behaviour_node, dict) and "data" in behaviour_node:
                behaviour_node = behaviour_node["data"]

            events = []
            timeline = []

            if isinstance(behaviour_node, dict):
                events = (
                    behaviour_node.get("history") 
                    or behaviour_node.get("timeline") 
                    or behaviour_node.get("data") 
                    or []
                )
                if isinstance(events, dict):
                    events = events.get("history") or events.get("timeline") or []

                timeline = (
                    behaviour_node.get("timeline") 
                    or behaviour_node.get("weekly") 
                    or []
                )
                
                if events == timeline and isinstance(events, list):
                    if len(events) > 0 and "positive" in events[0]:
                        events = []

            return events or [], timeline or []

        events = getattr(self.coordinator.data, "behaviour_events", [])
        timeline = getattr(self.coordinator.data, "behaviour_timeline", [])
        return events or [], timeline or []

    @property
    def native_value(self):
        """Calculate state outputs across all fallback modes seamlessly."""
        events, timeline = self.extract_events_and_timeline

        # 1. Latest Update Date Tracker
        if self._sensor_type == "latest_date":
            for e in events:
                if isinstance(e, dict) and (e.get("timestamp") or e.get("date")):
                    try:
                        return date.fromisoformat((e.get("timestamp") or e.get("date"))[:10])
                    except:
                        continue
            for w in reversed(timeline):
                if isinstance(w, dict) and w.get("end"):
                    try:
                        return date.fromisoformat(w["end"])
                    except:
                        continue
            return None

        # 2. Point Metric Logic
        pos, neg = 0, 0
        
        if not events and timeline:
            for week in timeline:
                if isinstance(week, dict):
                    pos += int(week.get("positive") or week.get("score") or 0)
                    neg += int(week.get("negative") or 0)
        else:
            for item in events:
                if isinstance(item, dict):
                    score = int(item.get("score") or item.get("points") or item.get("value") or 0)
                    if score > 0:
                        pos += score
                    elif score < 0:
                        neg += abs(score)

        if self._sensor_type == "balance":
            return pos - neg
            
        return pos

    @property
    def extra_state_attributes(self) -> dict:
        """Map points history and weekly bounds cleanly to state attributes."""
        attrs = {}
        events, timeline = self.extract_events_and_timeline
        today = date.today()

        pos, neg = 0, 0
        this_week_pos, this_week_neg = 0, 0
        slimmed_history = []

        for week in timeline:
            if isinstance(week, dict):
                try:
                    start = date.fromisoformat(week.get("start", ""))
                    end = date.fromisoformat(week.get("end", ""))
                    if start <= today <= end:
                        this_week_pos = week.get("positive") or week.get("score", 0)
                        this_week_neg = week.get("negative") or 0
                        break
                except:
                    continue

        for item in events:
            if isinstance(item, dict):
                reason = item.get("reason") or item.get("name") or "Unknown"
                points = int(item.get("score") or item.get("points") or 0)
                teacher = item.get("teacher") or item.get("teacher_name") or "Unknown"
                timestamp = item.get("timestamp") or item.get("date") or "Unknown"

                if points > 0:
                    pos += points
                    if this_week_pos == 0:
                        this_week_pos += points
                elif points < 0:
                    neg += abs(points)
                    if this_week_neg == 0:
                        this_week_neg += abs(points)

                slimmed_history.append({
                    "reason": reason,
                    "points": points,
                    "teacher": teacher,
                    "timestamp": timestamp
                })

        attrs["total_positive"] = pos
        attrs["total_negative"] = neg
        attrs["this_week_positive"] = this_week_pos
        attrs["this_week_negative"] = this_week_neg
        
        if self._sensor_type == "breakdown":
            attrs["points_history"] = slimmed_history

        return attrs
