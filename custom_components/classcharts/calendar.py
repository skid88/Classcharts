import logging
from datetime import datetime
import homeassistant.util.dt as dt_util
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from .const import DOMAIN, CONF_PUPIL_ID

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Class Charts timetable platform."""
    # This pulls the coordinator we created in __init__.py
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    pupil_id = config_entry.data.get(CONF_PUPIL_ID)
    
    _LOGGER.debug("Setting up Class Charts timetable for pupil: %s", pupil_id)
    async_add_entities([ClassChartsCalendar(coordinator, pupil_id)])

class ClassChartsCalendar(CalendarEntity):
    """Representation of a Class Charts Timetable."""

    def __init__(self, coordinator, pupil_id):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._pupil_id = pupil_id
        self._attr_name = "Class Charts Timetable"
        self._attr_unique_id = f"{pupil_id}_timetable_cal"

    @property
    def available(self):
        """Return if the data update was successful."""
        return self.coordinator.last_update_success

    def _get_events_from_data(self):
        """Helper to parse the coordinator data into calendar events."""
        events = []
        # Access the 'timetable' key we defined in __init__.py
        data = self.coordinator.data.get("timetable", {})
        
        if not data:
            return events

        for date_str, lessons in data.items():
            for lesson in lessons:
                try:
                    st_raw = lesson.get('start_time')
                    et_raw = lesson.get('end_time')
                    
                    if not st_raw or not et_raw:
                        continue

                    # Try ISO format first, fallback to combining date + time
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
                            location=lesson.get("room_name", "N/A"),
                            description=f"Teacher: {lesson.get('teacher_name', 'Unknown')}",
                        )
                    )
                except Exception as err:
                    _LOGGER.error("Timetable parse error on %s: %s", date_str, err)
        
        return events

    async def async_get_events(self, hass, start_date, end_date):
        """Return calendar events within a specific timeframe."""
        events = self._get_events_from_data()
        return [
            event for event in events 
            if event.start >= start_date and event.end <= end_date
        ]

    @property
    def event(self):
        """Return the next/current upcoming event."""
        all_events = sorted(self._get_events_from_data(), key=lambda x: x.start)
        now = dt_util.now()
        return next((e for e in all_events if e.end > now), None)
