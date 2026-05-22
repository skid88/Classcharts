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
        """Calculate state outputs across all fallback modes seamlessly."""
        from datetime import date
        events, timeline = self.extract_events_and_timeline

        # 1. PROFILE: Latest Update Date
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

        # 2. PROFILE: Point Metric Logic
        pos, neg = 0, 0
        
        # Fallback Mode: If events history array is missing or empty, read directly from timeline
        if not events and timeline:
            for week in timeline:
                if isinstance(week, dict):
                    pos += int(week.get("positive") or week.get("score") or 0)
                    neg += int(week.get("negative") or 0)
        else:
            # Standard Mode: Sum up itemized granular list entries
            for item in events:
                if isinstance(item, dict):
                    score = int(item.get("score") or item.get("points") or item.get("value") or 0)
                    if score > 0:
                        pos += score
                    elif score < 0:
                        neg += abs(score)

        if self._sensor_type == "balance":
            return pos - neg
            
        # Returns the total positive points aggregate value for the 'breakdown' sensor type
        return pos

class CCBehaviourSensor(CoordinatorEntity, SensorEntity):
    """Robust, multi-structure adapter for tracking behavior metrics."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, name, sensor_type):
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        student_label = entry.data.get("student_name") or entry.data.get("pupil_id")
        
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_behaviour_{sensor_type}"
        self._attr_icon = "mdi:star-circle" if sensor_type == "balance" else "mdi:counter"
        
        if sensor_type == "latest_date":
            self._attr_device_class = "date"
        else:
            self._attr_native_unit_of_measurement = "Points"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)}, 
            "name": f"Class Charts ({student_label})"
        }

    @property
    def extract_events_and_timeline(self) -> tuple[list, list]:
        """Normalize both object models and raw dict layouts into standard lists."""
        if not self.coordinator.data:
            return [], []

        # Step A: Is it a nested dictionary?
        if isinstance(self.coordinator.data, dict):
            behaviour_node = self.coordinator.data.get("behaviour", self.coordinator.data)
            
            # Extract events/history list
            events = []
            if hasattr(behaviour_node, "behaviour_events"):
                events = getattr(behaviour_node, "behaviour_events", [])
            elif isinstance(behaviour_node, dict):
                events = behaviour_node.get("history") or behaviour_node.get("timeline") or behaviour_node.get("data") or []
                if isinstance(events, dict):
                    events = events.get("history") or events.get("timeline") or []

            # Extract timeline list
            timeline = []
            if hasattr(behaviour_node, "behaviour_timeline"):
                timeline = getattr(behaviour_node, "behaviour_timeline", [])
            elif isinstance(behaviour_node, dict):
                timeline = behaviour_node.get("timeline") or behaviour_node.get("weekly") or []
                
            return events or [], timeline or []

        # Step B: Fallback if coordinator.data itself is an object
        events = getattr(self.coordinator.data, "behaviour_events", [])
        timeline = getattr(self.coordinator.data, "behaviour_timeline", [])
        return events or [], timeline or []

    @property
    def native_value(self):
        """Calculate state outputs across all fallback modes."""
        from datetime import date
        events, timeline = self.extract_events_and_timeline

        # 1. PROFILE: Latest Update Date
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

        # 2. PROFILE: Point Metric Logic
        pos, neg = 0, 0
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
        from datetime import date
        attrs = {}
        events, timeline = self.extract_events_and_timeline
        today = date.today()

        pos, neg = 0, 0
        this_week_pos, this_week_neg = 0, 0
        slimmed_history = []

        # Parse weekly data matrix out of timeline if provided natively
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

        # Extract structural items out into markdown card variables
        for item in events:
            if isinstance(item, dict):
                reason = item.get("reason") or item.get("name") or "Unknown"
                points = int(item.get("score") or item.get("points") or 0)
                teacher = item.get("teacher") or item.get("teacher_name") or "Unknown"
                timestamp = item.get("timestamp") or item.get("date") or "Unknown"

                if points > 0:
                    pos += points
                    if this_week_pos == 0:  # Fallback approximation helper
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
