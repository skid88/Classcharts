from __future__ import annotations
import re    
import html 
import logging
from datetime import datetime, date, timedelta

from homeassistant.util import dt as dt_util
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, CONF_SHOW_NO_SCHOOL 

_LOGGER = logging.getLogger(__name__)

def clean_html_tags(raw_html: str) -> str:
    """Strip HTML tags and unescape HTML entities."""
    if not raw_html:
        return ""
   
    text = html.unescape(raw_html)
    clean_text = re.sub(r'<[^>]+>', '', text)
    clean_text = re.sub(r'\n\s*\n', '\n', clean_text)
    return clean_text.strip()

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Class Charts calendars."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ClassChartsTimetableCalendar(coordinator, entry),
        ClassChartsHomeworkCalendar(coordinator, entry),
    ])

class ClassChartsTimetableCalendar(CoordinatorEntity, CalendarEntity):
    """Calendar for school lessons."""
    
    _attr_has_entity_name = True
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        
        # 1. Grab dynamic student profile name
        student_label = entry.data.get("student_name") or entry.data.get("pupil_id")
        
        # 2. Assign dynamic friendly UI names and matching safe system uniqueness IDs
        self._attr_name = f"{student_label} Timetable"
        self._attr_unique_id = f"{entry.entry_id}_timetable"
        
        # 3. Dynamic Device Association map matching your child's distinct sensor panel card
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Class Charts ({student_label})",
        }

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming lesson."""
        events = self._get_events()
        now = dt_util.now()
        upcoming = [e for e in events if e.end > now]
        return upcoming[0] if upcoming else None

    def _get_events(self) -> list[CalendarEvent]:
        """Convert coordinator data to CalendarEvents."""
        events = []
        timetable_data = self.coordinator.data.get("timetable", {})
        
        if isinstance(timetable_data, dict):
            for date_str, lessons in timetable_data.items():
                for lesson in lessons:
                    try:
                        start = dt_util.as_local(datetime.fromisoformat(lesson["start_time"]))
                        end = dt_util.as_local(datetime.fromisoformat(lesson["end_time"]))
                        events.append(CalendarEvent(
                            summary=lesson.get("subject_name", "Unknown"),
                            start=start,
                            end=end,
                            location=lesson.get("room_name"),
                            description=f"Teacher: {lesson.get('teacher_name')}"
                        ))
                    except (KeyError, ValueError, TypeError):
                        continue

        return sorted(events, key=lambda x: x.start)

    async def async_get_events(self, hass, start_date, end_date) -> list[CalendarEvent]:
        """Return events for the UI, including 'No School' for empty weekdays."""
        _LOGGER.debug("Calendar requested events between %s and %s", start_date, end_date)
        
        all_events = self._get_events()
        
        filtered_events = [
            e for e in all_events 
            if e.start.date() >= start_date.date() and e.end.date() <= end_date.date()
        ]

        show_no_school = self.coordinator.config_entry.options.get(CONF_SHOW_NO_SCHOOL, True)

        if show_no_school:
            from .const import CONF_DAYS_TO_FETCH
            days_to_fetch = self.coordinator.config_entry.options.get(CONF_DAYS_TO_FETCH, 7)
            
            today = dt_util.now().date()
            max_data_date = today + timedelta(days=days_to_fetch)
            
            current_day = start_date.date()
            finish_day = end_date.date()
            
            while current_day <= finish_day:
                if current_day.weekday() < 5 and today <= current_day <= max_data_date:
                    day_has_lesson = any(e.start.date() == current_day for e in filtered_events)
                    
                    if not day_has_lesson:
                        day_start = dt_util.as_local(
                            datetime.combine(current_day, datetime.strptime("08:30", "%H:%M").time())
                        )
                        day_end = dt_util.as_local(
                            datetime.combine(current_day, datetime.strptime("15:30", "%H:%M").time())
                        )
                        
                        filtered_events.append(
                            CalendarEvent(
                                summary="No School",
                                start=day_start,
                                end=day_end,
                                description="No lessons scheduled for this school day within the fetched range.",
                                location="Home",
                            )
                        )
                current_day += timedelta(days=1)

        return sorted(filtered_events, key=lambda x: x.start)
        
class ClassChartsHomeworkCalendar(CoordinatorEntity, CalendarEntity):
    """Calendar for homework due dates."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        
        student_label = entry.data.get("student_name") or entry.data.get("pupil_id")
        
        self._attr_name = f"{student_label} Homework"
        self._attr_unique_id = f"{entry.entry_id}_homework"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Class Charts ({student_label})",
        }

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next homework due."""
        events = self._get_events()
        now_date = dt_util.now().date()
        upcoming = [e for e in events if e.start >= now_date]
        return upcoming[0] if upcoming else None

    def _get_events(self) -> list[CalendarEvent]:
        """Convert coordinator homework list to CalendarEvents."""
        events = []
        hw_raw = self.coordinator.data.get("homework", {})
        homework_list = hw_raw.get("data", []) if isinstance(hw_raw, dict) else []
        
        for hw in homework_list:
            try:
                due_date = date.fromisoformat(hw.get("due_date"))
                is_completed = hw.get("status", {}).get("ticked") == "yes"

                event = CalendarEvent(
                    summary=f"HW: {hw.get('subject', 'Assignment')}",
                    start=due_date,
                    end=due_date + timedelta(days=1),
                    description=clean_html_tags(hw.get("description", "")),
                )
                
                event.is_completed_homework = is_completed
                events.append(event)
            except (KeyError, ValueError, TypeError):
                continue
                
        return sorted(events, key=lambda x: x.start)

    async def async_get_events(self, hass, start_date, end_date) -> list[CalendarEvent]:
        """Return events for the calendar UI view with filtering."""
        show_completed = self.coordinator.config_entry.options.get("show_completed_homework", True)
        
        all_events = self._get_events()
        return [
            e for e in all_events 
            if e.start >= start_date.date() and e.start <= end_date.date()
            and (show_completed or not getattr(e, "is_completed_homework", False))
        ]
