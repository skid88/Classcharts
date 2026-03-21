from __future__ import annotations
from datetime import datetime, date, timedelta

from homeassistant.util import dt as dt_util
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

def clean_html_tags(raw_html: str) -> str:
    """Strip HTML tags and unescape HTML entities."""
    if not raw_html:
        return ""
    import re
    import html
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
        """Convert coordinator timetable data to CalendarEvents."""
        events = []
        data = self.coordinator.data.get("timetable", {})
        if not isinstance(data, dict):
            return []

        for date_str, lessons in data.items():
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
        """Return events for the UI."""
        all_events = self._get_events()
        return [
            e for e in all_events 
            if e.start >= start_date and e.end <= end_date
        ]

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
        # Get data from coordinator
        hw_raw = self.coordinator.data.get("homework", {})
        
        # Ensure we are handling the nested 'data' list from ClassCharts API
        if isinstance(hw_raw, dict):
            homework_list = hw_raw.get("data", [])
        else:
            homework_list = []
        
        if not isinstance(homework_list, list):
            return []

        for hw in homework_list:
            try:
                # ClassCharts dates are usually YYYY-MM-DD
                due_date = date.fromisoformat(hw.get("due_date"))
                
                # Clean HTML from description
                raw_desc = hw.get("description", "")
                clean_desc = clean_html_tags(raw_desc)

                events.append(
                    CalendarEvent(
                        summary=f"HW: {hw.get('subject', 'Assignment')}",
                        start=due_date,
                        end=due_date + timedelta(days=1),
                        description=clean_desc,
                    )
                )
            except (KeyError, ValueError, TypeError):
                continue
                
        return sorted(events, key=lambda x: x.start)

    async def async_get_events(self, hass, start_date, end_date) -> list[CalendarEvent]:
        """Return events for the calendar UI view."""
        all_events = self._get_events()
        return [
            e for e in all_events 
            if e.start >= start_date.date() and e.start <= end_date.date()
        ]
