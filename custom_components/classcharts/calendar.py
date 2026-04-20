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
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Timetable"
        self._attr_unique_id = f"{entry.entry_id}_timetable"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Class Charts",
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

    # Fixed Indentation: Now correctly inside the ClassChartsTimetableCalendar class
    async def async_get_events(self, hass, start_date, end_date) -> list[CalendarEvent]:
        """Return events for the UI, including 'No School' for empty weekdays."""
        _LOGGER.debug("Calendar requested events between %s and %s", start_date, end_date)
        
        all_events = self._get_events()
        _LOGGER.warning("--- CALENDAR DEBUG START ---")
        _LOGGER.warning("Request Range: %s to %s", start_date.date(), end_date.date())
        _LOGGER.warning("Total lessons found in memory: %s", len(all_events))
        
        # 1. FIX: Filter real lessons that land WITHIN the view range
        # We want lessons where the date is >= start AND <= end.
        filtered_events = [
            e for e in all_events 
            if start_date.date() <= e.start.date() <= end_date.date()
        ]

        # 2. Check the "No School" toggle from options
        show_no_school = self.coordinator.config_entry.options.get(CONF_SHOW_NO_SCHOOL, True)

        if show_no_school:
            # 3. Get the fetch limit from settings 
            from .const import CONF_DAYS_TO_FETCH
            days_to_fetch = self.coordinator.config_entry.options.get(CONF_DAYS_TO_FETCH, 7)
            
            today = dt_util.now().date()
            max_data_date = today + timedelta(days=(days_to_fetch - 1))
            
            current_day = start_date.date()
            finish_day = min(end_date.date(), max_data_date)
            
            while current_day <= finish_day:
                # Logic: Weekday AND Today/Future AND Within Data Window
                if current_day.weekday() < 5 and current_day >= today:
                    
                    # Check ALL_EVENTS so we don't get fooled by UI filters
                    day_has_lesson = any(e.start.date() == current_day for e in all_events)
                    
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
                                description="No lessons scheduled for this school day.",
                                location="Home",
                            )
                        )
                current_day += timedelta(days=1)

        return sorted(filtered_events, key=lambda x: x.start)
        
class ClassChartsHomeworkCalendar(CoordinatorEntity, CalendarEntity):
    """Calendar for homework due dates."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Homework"
        self._attr_unique_id = f"{entry.entry_id}_homework"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Class Charts",
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
