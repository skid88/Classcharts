from datetime import datetime, timedelta
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Class Charts calendar platform."""
    # We retrieve the 'coordinator' which holds our logged-in session and data
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([ClassChartsCalendar(coordinator)])

class ClassChartsCalendar(CalendarEntity):
    """Representation of a Class Charts Timetable as a calendar."""

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_name = "Class Charts Timetable"
        self._attr_unique_id = f"{coordinator.pupil_id}_timetable"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        # This shows the 'active' lesson on your dashboard
        now = datetime.now()
        events = self._get_all_events()
        upcoming = [e for e in events if e.end > now]
        return upcoming[0] if upcoming else None

    def _get_all_events(self):
        """Helper to transform raw API data into HA CalendarEvents."""
        events = []
        # 'data' here is the multi-day dictionary we built in the previous step
        data = self.coordinator.data 

        for date_str, lessons in data.items():
            for lesson in lessons:
                # Class Charts uses HH:MM:SS, HA needs a datetime object
                start_dt = datetime.strptime(f"{date_str} {lesson['start_time']}", "%Y-%m-%d %H:%M:%S")
                end_dt = datetime.strptime(f"{date_str} {lesson['end_time']}", "%Y-%m-%d %H:%M:%S")

                events.append(
                    CalendarEvent(
                        summary=lesson.get("subject_name", "Lesson"),
                        start=start_dt,
                        end=end_dt,
                        location=lesson.get("room_name"),
                        description=f"Teacher: {lesson.get('teacher_name')}",
                    )
                )
        return sorted(events, key=lambda x: x.start)

    async def async_get_events(self, hass, start_date, end_date) -> list[CalendarEvent]:
        """Return calendar events within a specific datetime range."""
        all_events = self._get_all_events()
        # Filter events so we only show what the calendar card is asking for
        return [
            event for event in all_events 
            if event.start >= start_date and event.end <= end_date
        ]
