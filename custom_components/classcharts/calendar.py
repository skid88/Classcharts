import logging
from datetime import datetime, timedelta  # <-- Add timedelta here
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from .const import DOMAIN, CONF_PUPIL_ID

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Class Charts calendar platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # We pass the pupil_id from the config entry directly
    pupil_id = config_entry.data.get(CONF_PUPIL_ID)
    
    _LOGGER.debug("Setting up Class Charts calendar for pupil: %s", pupil_id)
    async_add_entities([ClassChartsCalendar(coordinator, pupil_id)])

class ClassChartsCalendar(CalendarEntity):
    """Representation of a Class Charts Timetable."""

    def __init__(self, coordinator, pupil_id):
        self.coordinator = coordinator
        self._pupil_id = pupil_id
        self._attr_name = f"Class Charts ({pupil_id})"
        self._attr_unique_id = f"{pupil_id}_timetable"

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success

    def _get_events_from_data(self):
        """Helper to parse the coordinator data."""
        events = []
        data = self.coordinator.data
        
        # 1. Add a Test Event so you can see if the calendar entity is alive
        events.append(
            CalendarEvent(
                summary="API Connection Test",
                start=datetime.now(),
                end=datetime.now() + timedelta(hours=1),
                description="If you see this, the calendar works! Check logs for API data."
            )
        )

        if not data:
            _LOGGER.debug("No data found in coordinator")
            return events

        # 2. Loop through the actual data
        for date_str, lessons in data.items():
            for lesson in lessons:
                try:
                    # Handle HH:MM vs HH:MM:SS
                    start_t = lesson['start_time'] if len(lesson['start_time'].split(':')) == 3 else f"{lesson['start_time']}:00"
                    end_t = lesson['end_time'] if len(lesson['end_time'].split(':')) == 3 else f"{lesson['end_time']}:00"

                    start_dt = datetime.strptime(f"{date_str} {start_t}", "%Y-%m-%d %H:%M:%S")
                    end_dt = datetime.strptime(f"{date_str} {end_t}", "%Y-%m-%d %H:%M:%S")

                    events.append(
                        CalendarEvent(
                            summary=lesson.get("subject_name", "Lesson"),
                            start=start_dt,
                            end=end_dt,
                            location=lesson.get("room_name", ""),
                            description=f"Teacher: {lesson.get('teacher_name', 'Unknown')}",
                        )
                    )
                except Exception as err:
                    _LOGGER.error("Failed to parse lesson on %s: %s", date_str, err)
        
        return events

    async def async_get_events(self, hass, start_date, end_date):
        """Return calendar events."""
        events = self._get_events_from_data()
        return [
            event for event in events 
            if event.start >= start_date and event.end <= end_date
        ]

    @property
    def event(self):
        """Return the next upcoming event."""
        all_events = sorted(self._get_events_from_data(), key=lambda x: x.start)
        now = datetime.now()
        return next((e for e in all_events if e.end > now), None)
