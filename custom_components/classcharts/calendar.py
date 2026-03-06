import logging
from datetime import datetime
import homeassistant.util.dt as dt_util
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from .const import DOMAIN, CONF_PUPIL_ID

_LOGGER = logging.getLogger(__name__)

# THIS IS THE MISSING FUNCTION
async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Class Charts calendar platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    pupil_id = config_entry.data.get(CONF_PUPIL_ID)
    async_add_entities([ClassChartsCalendar(coordinator, pupil_id)])

class ClassChartsCalendar(CalendarEntity):
    """Representation of a Class Charts Timetable."""

    def __init__(self, coordinator, pupil_id):
        self.coordinator = coordinator
        self._pupil_id = pupil_id
        self._attr_name = "Class Charts Timetable"
        self._attr_unique_id = f"{pupil_id}_timetable_cal"

    @property
    def available(self):
        return self.coordinator.last_update_success

    def _get_events_from_data(self):
        events = []
        # Use the 'timetable' key we added to the coordinator
        data = self.coordinator.data.get("timetable", {})
        
        for date_str, lessons in data.items():
            for lesson in lessons:
                try:
                    st_raw = lesson.get('start_time')
                    et_raw = lesson.get('end_time')
                    
                    # Time parsing logic
                    try:
                        start_dt = datetime.fromisoformat(st_raw)
                        end_dt = datetime.fromisoformat(et_raw)
                    except (ValueError, TypeError):
                        start_dt = datetime.strptime(f"{date_str} {st_raw}", "%Y-%m-%d %H:%M:%S")
                        end_dt = datetime.strptime(f"{date_str} {et_raw}", "%Y-%m-%d %H:%M:%S")

                    events.append(
                        CalendarEvent(
                            summary=lesson.get("subject_name", "Lesson"),
                            start=dt_util.as_local(start_dt),
                            end=dt_util.as_local(end_dt),
                            location=lesson.get("room_name", ""),
                            description=f"Teacher: {lesson.get('teacher_name', 'Unknown')}",
                        )
                    )
                except Exception as err:
                    _LOGGER.error("Calendar parse error: %s", err)
        return events

    async def async_get_events(self, hass, start_date, end_date):
        events = self._get_events_from_data()
        return [
            event for event in events 
            if event.start >= start_date and event.end <= end_date
        ]

    @property
    def event(self):
        all_events = sorted(self._get_events_from_data(), key=lambda x: x.start)
        now = dt_util.now()
        return next((e for e in all_events if e.end > now), None)
