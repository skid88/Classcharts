from __future__ import annotations
import logging
from datetime import datetime
import re
from html import unescape

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
        """Clean and trim homework list attributes with a short text snippet."""
        if self._key != "this_week_outstanding_count":
            return {}

        if not self.coordinator.data or not isinstance(self.coordinator.data, dict):
            return {}

        hw = self.coordinator.data.get("homework", {})
        raw_list = hw.get("data", [])

        cleaned_list = []
        for item in raw_list[:15]:
            raw_desc = item.get("description", "") or ""
            clean_text = re.sub('<[^<]+?>', '', raw_desc)
            clean_text = unescape(clean_text).strip()
            clean_text = re.sub(r'\s+', ' ', clean_text)
            
            description_snippet = (clean_text[:147] + "...") if len(clean_text) > 150 else clean_text

            raw_due = item.get("due_date", "") or ""
            raw_issue = item.get("issue_date", "") or ""

            # Format helpers
            def format_date(date_str):
                try:
                    ds = str(date_str)
                    if len(ds) >= 10:
                        dt = datetime.strptime(ds[:10], "%Y-%m-%d")
                        return dt.strftime("%Y-%m-%d"), dt.strftime("%d/%m/%Y")
                except (ValueError, TypeError):
                    pass
                return date_str, date_str

            due_iso, due_disp = format_date(raw_due)
            issue_iso, issue_disp = format_date(raw_issue)

            cleaned_list.append({
                "id": item.get("id"),
                "subject": item.get("subject"),
                "title": item.get("title"),
                "teacher": item.get("teacher"),
                "homework_type": item.get("homework_type"),
                "issue_date": issue_iso,
                "issue_date_formatted": issue_disp,
                "due_date": due_iso,           # YYYY-MM-DD for your Jinja math
                "due_date_formatted": due_disp,     # DD/MM/YYYY for display
                "description_snippet": description_snippet,
            })

        return {"homework_list": cleaned_list}


class CCLessonSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, lesson_type):
        super().__init__(coordinator)
        self._lesson_type = lesson_type
        student_label = entry.data.get("student_name") or entry.data.get("pupil_id")
        self._attr_name = f"{lesson_type.capitalize()} Lesson"
        self._attr_unique_id = f"{entry.entry_id}_lesson_{lesson_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)}, 
            "name": f"Class Charts ({student_label})"
        }
        self._attr_icon = "mdi:book-education"

    def _get_target_lesson(self):
        """Helper to find current or next lesson, safely parsing various time formats."""
        if not self.coordinator.data or not isinstance(self.coordinator.data, dict):
            return None

        timetable = self.coordinator.data.get("timetable", {})
        if not timetable:
            return None

        now = datetime.now()
        current_time = now.time()
        today_str = now.strftime("%Y-%m-%d")

        def extract_time(time_val):
            """Safely pull a time object out of a string whether it's HH:MM or ISO datetime."""
            if not time_val:
                return None
            val_str = str(time_val)
            
            # If it's an ISO timestamp containing 'T' (e.g. 2026-09-21T09:00:00)
            if "T" in val_str:
                try:
                    return datetime.fromisoformat(val_str).time()
                except ValueError:
                    pass
            
            # If it's just a time string, clean it up and grab HH:MM
            try:
                # Remove any leading date if it's glued with a space
                if " " in val_str:
                    val_str = val_str.split(" ")[-1]
                return datetime.strptime(val_str[:5], "%H:%M").time()
            except (ValueError, TypeError):
                return None

        # For current lesson, we safely check today's lessons
        if self._lesson_type == "current":
            lessons = timetable.get(today_str, [])
            if not lessons or not isinstance(lessons, list):
                return None

            for lesson in lessons:
                start_val = lesson.get("start_time") or lesson.get("start")
                end_val = lesson.get("end_time") or lesson.get("end")
                
                start_time = extract_time(start_val)
                end_time = extract_time(end_val)
                
                if start_time and end_time and start_time <= current_time <= end_time:
                    return lesson
            return None

        # For next lesson, scan today's remaining lessons or look ahead to future school days
        sorted_dates = sorted([d for d in timetable.keys() if d >= today_str])
        
        for date_str in sorted_dates:
            lessons = timetable.get(date_str, [])
            if not lessons or not isinstance(lessons, list):
                continue

            for lesson in lessons:
                start_val = lesson.get("start_time") or lesson.get("start")
                start_time = extract_time(start_val)
                
                if not start_time:
                    continue

                if date_str == today_str:
                    if start_time > current_time:
                        return lesson
                elif date_str > today_str:
                    return lesson

        return None

    @property
    def native_value(self):
        target_lesson = self._get_target_lesson()
        if not target_lesson:
            return "No Lessons"

        return (
            target_lesson.get("subject_name") 
            or target_lesson.get("name") 
            or target_lesson.get("lesson_name") 
            or "Unknown Lesson"
        )

    @property
    def extra_state_attributes(self) -> dict:
        target_lesson = self._get_target_lesson()
        if not target_lesson:
            return {}

        return {
            "teacher": target_lesson.get("teacher_name") or target_lesson.get("teacher"),
            "room": target_lesson.get("room_name") or target_lesson.get("room"),
            "start_time": target_lesson.get("start_time") or target_lesson.get("start"),
            "end_time": target_lesson.get("end_time") or target_lesson.get("end"),
            "subject": target_lesson.get("subject_name") or target_lesson.get("name"),
        }


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

        if sensor_type == "positive":
            self._attr_icon = "mdi:thumb-up"
        elif sensor_type == "negative":
            self._attr_icon = "mdi:thumb-down"
        else:
            self._attr_icon = "mdi:star-circle"

    @property
    def native_value(self):
        """Sums values from the pre-scoped academic year timeline payload."""
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
            return total_pos

    @property
    def extra_state_attributes(self) -> dict:
        """Pulls detailed logs from /activity and summary reasons."""
        if not self.coordinator.data or not isinstance(self.coordinator.data, dict):
            return {}

        activity_list = self.coordinator.data.get("activity_data", {}).get("data", {})
        behaviour_data = self.coordinator.data.get("behaviour_data", {}).get("data", {})

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
