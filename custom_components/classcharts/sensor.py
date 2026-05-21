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
        CCLessonSensor(coordinator, entry, "next")
    ])

class CCHomeworkSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Homework stats with attribute list for Markdown."""
    
    # Force Home Assistant to handle clean dynamic entity ID names automatically
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, name, key):
        super().__init__(coordinator)
        self._key = key
        
        # 1. Grab the dynamic student name from your new config flow
        student_label = entry.data.get("student_name") or entry.data.get("pupil_id")
        
        # 2. Dynamic Friendly Name for the UI
        self._attr_name = f"{student_label} {name}"
        
        # 3. Unique system ID to guarantee zero database collisions
        self._attr_unique_id = f"{entry.entry_id}_hw_{key}"
        
        # 4. Brand the Device Card uniquely after the student
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
        
        # 1. Grab the dynamic student name from your new config flow
        student_label = entry.data.get("student_name") or entry.data.get("pupil_id")
        
        # 2. Dynamic Friendly Name for the UI
        self._attr_name = f"{student_label} {type.capitalize()} Lesson"
        self._attr_unique_id = f"{entry.entry_id}_lesson_{type}"
        
        # 3. Brand the Device Card uniquely after the student
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
