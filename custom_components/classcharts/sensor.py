import logging
from datetime import datetime, timedelta
import homeassistant.util.dt as dt_util
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Class Charts sensors. Outstanding is now first for priority."""
    coordinator = hass.data["classcharts"][entry.entry_id]
    
    # We define the list first to ensure all are included
    entities = [
        CCHomeworkOutstanding(coordinator, entry.entry_id),
        CCHomeworkCompleted(coordinator, entry.entry_id),
        CCHomeworkTotal(coordinator, entry.entry_id),
        CCHomeworkUpcomingList(coordinator, entry.entry_id),
        CCTimetableMain(coordinator, entry.entry_id),
        CCCurrentLesson(coordinator, entry.entry_id),
        CCNextLesson(coordinator, entry.entry_id)
    ]
    
    async_add_entities(entities, True)

# --- 1. OUTSTANDING HOMEWORK (Meta Map) ---
class CCHomeworkOutstanding(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Homework Outstanding"
        self._attr_unique_id = f"{entry_id}_hw_outstanding_v30"
        self._attr_icon = "mdi:alert-circle-outline"
        self._attr_native_unit_of_measurement = "Tasks"

    @property
    def native_value(self):
        try:
            # Drills into homework -> meta -> this_week_outstanding_count
            hw_data = self.coordinator.data.get("homework", {})
            meta = hw_data.get("meta", {})
            return meta.get("this_week_outstanding_count", 0)
        except Exception:
            return 0

# --- 2. COMPLETED HOMEWORK (Meta Map) ---
class CCHomeworkCompleted(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Homework Completed"
        self._attr_unique_id = f"{entry_id}_completed_v30"
        self._attr_icon = "mdi:check-circle-outline"
        self._attr_native_unit_of_measurement = "Tasks"

    @property
    def native_value(self):
        try:
            # Drills into homework -> meta -> this_week_completed_count
            hw_data = self.coordinator.data.get("homework", {})
            meta = hw_data.get("meta", {})
            return meta.get("this_week_completed_count", 0)
        except Exception:
            return 0

# --- 3. TOTAL HOMEWORK (Meta Map) ---
class CCHomeworkTotal(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Homework Total Due"
        self._attr_unique_id = f"{entry_id}_total_due_v30"
        self._attr_icon = "mdi:book-open-page-variant"
        self._attr_native_unit_of_measurement = "Tasks"

    @property
    def native_value(self):
        try:
            # Drills into homework -> meta -> this_week_due_count
            hw_data = self.coordinator.data.get("homework", {})
            meta = hw_data.get("meta", {})
            return meta.get("this_week_due_count", 0)
        except Exception:
            return 0

# --- 4. UPCOMING HOMEWORK LIST (Next 30 days) ---
class CCHomeworkUpcomingList(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Homework Upcoming (30 Days)"
        self._attr_unique_id = f"{entry_id}_hw_upcoming_30d_v1"
        self._attr_icon = "mdi:clipboard-text-clock-outline"

    def _parse_due_date(self, value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except Exception:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except Exception:
                continue
        return None

    @property
    def native_value(self):
        return len(self._get_upcoming_items())

    @property
    def extra_state_attributes(self):
        return {
            "items": self._get_upcoming_items(),
        }

    def _get_upcoming_items(self):
        try:
            hw_data = self.coordinator.data.get("homework", {})
            items = hw_data.get("data", [])
            if not isinstance(items, list):
                return []

            now = dt_util.now()
            end = now + timedelta(days=30)
            upcoming = []

            for item in items:
                if not isinstance(item, dict):
                    continue
                due_raw = item.get("due_date") or item.get("display_date")
                due_dt = self._parse_due_date(due_raw)
                if due_dt is None:
                    continue
                due_local = dt_util.as_local(due_dt)
                if now <= due_local <= end:
                    status = None
                    status_obj = item.get("status")
                    if isinstance(status_obj, dict):
                        status = status_obj.get("state")
                    if isinstance(status, str) and status.lower() in {"completed", "done", "submitted"}:
                        continue
                    upcoming.append({
                        "title": item.get("title") or "Homework",
                        "subject": item.get("subject") or item.get("subject_name") or "Unknown",
                        "teacher": item.get("teacher") or item.get("teacher_name") or "Unknown",
                        "due": due_local.isoformat(),
                        "status": status or "unknown",
                    })

            upcoming.sort(key=lambda x: x.get("due", ""))
            return upcoming
        except Exception:
            return []
# --- 5. TIMETABLE COUNT ---
class CCTimetableMain(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Timetable"
        self._attr_unique_id = f"{entry_id}_timetable_v25"
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self):
        try:
            timetable = self.coordinator.data.get("timetable", {})
            if isinstance(timetable, dict):
                today_key = dt_util.now().date().strftime("%Y-%m-%d")
                return len(timetable.get(today_key, []))
            if isinstance(timetable, list):
                return len(timetable)
            return 0
        except Exception:
            return 0

# --- 6. CURRENT LESSON ---
class CCCurrentLesson(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Current Lesson"
        self._attr_unique_id = f"{entry_id}_current_v25"
        self._attr_icon = "mdi:school-outline"

    @property
    def native_value(self):
        try:
            timetable = self.coordinator.data.get("timetable", {})
            if isinstance(timetable, dict):
                today_key = dt_util.now().date().strftime("%Y-%m-%d")
                lessons = timetable.get(today_key, [])
            else:
                lessons = timetable if isinstance(timetable, list) else []
            if lessons and len(lessons) > 0:
                return lessons[0].get("subject_name", "Unknown")
            return "No Lessons Today"
        except Exception:
            return "No Lessons Today"

# --- 7. NEXT LESSON ---
class CCNextLesson(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_name = "Class Charts Next Lesson"
        self._attr_unique_id = f"{entry_id}_next_v25"
        self._attr_icon = "mdi:school"

    @property
    def native_value(self):
        try:
            timetable = self.coordinator.data.get("timetable", {})
            if isinstance(timetable, dict):
                today_key = dt_util.now().date().strftime("%Y-%m-%d")
                lessons = timetable.get(today_key, [])
            else:
                lessons = timetable if isinstance(timetable, list) else []
            if lessons and len(lessons) > 1:
                return lessons[1].get("subject_name", "Unknown")
            return "No More Lessons"
        except Exception:
            return "No More Lessons"
