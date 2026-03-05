import logging
from datetime import datetime, timedelta
import homeassistant.util.dt as dt_util  # <--- Add this
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
        
        # Keep the Test Event for now so we know the entity is alive
        events.append(
            CalendarEvent(
                summary="API Connection Test",
                start=dt_util.now(),
                end=dt_util.now() + timedelta(hours=1),
                description="If you see this, the calendar is working!"
            )
        )

        if not data or not isinstance(data, dict):
            _LOGGER.debug("No valid dictionary data found in coordinator")
            return events

        for date_str, lessons in data.items():
            # Ensure 'lessons' is actually a list we can loop through
            if not isinstance(lessons, list):
                _LOGGER.warning("Lessons for %s is not a list: %s", date_str, lessons)
                continue

            for lesson in lessons:
                # This check prevents the 'string indices' error
                if not isinstance(lesson, dict):
                    _LOGGER.warning("Expected dictionary for lesson, got %s", type(lesson))
                    continue

                try:
                    # Defensive fetching of times
                    st_raw = lesson.get('start_time')
                    et_raw = lesson.get('end_time')

                    if not st_raw or not et_raw:
                        continue

                    start_t = st_raw if len(st_raw.split(':')) == 3 else f"{st_raw}:00"
                    end_t = et_raw if len(et_raw.split(':')) == 3 else f"{et_raw}:00"

                    try:
                # Use fromisoformat to handle the 'T' and timezone offset
                start_dt = datetime.datetime.fromisoformat(lesson.get("start_time"))
                end_dt = datetime.datetime.fromisoformat(lesson.get("end_time"))
            except (ValueError, TypeError) as err:
                # Fallback: if the API sends just a time, combine it with the date
                _LOGGER.warning("Time format mismatch, attempting fallback: %s", err)
                try:
                    start_str = f"{date_str} {lesson.get('start_time')}"
                    end_str = f"{date_str} {lesson.get('end_time')}"
                    start_dt = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
                    end_dt = datetime.datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    _LOGGER.error("Internal parse error on %s: %s", date_str, lesson.get("start_time"))
                    continue

                    events.append(
                        CalendarEvent(
                            summary=lesson.get("subject_name") or lesson.get("lesson_name") or "Lesson",
                            start=dt_util.as_local(start_dt),
                            end=dt_util.as_local(end_dt),
                            location=lesson.get("room_name", ""),
                            description=f"Teacher: {lesson.get('teacher_name', 'Unknown')}",
                        )
                    )
                except Exception as err:
                    _LOGGER.error("Internal parse error on %s: %s", date_str, err)
        
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
        now = dt_util.now()
        return next((e for e in all_events if e.end > now), None)
