def _get_events_from_data(self):
        """Helper to parse the coordinator data."""
        events = []
        # We now need to pull the 'timetable' key specifically
        data = self.coordinator.data.get("timetable", {})
        
        if not data or not isinstance(data, dict):
            _LOGGER.debug("Calendar: No timetable dictionary data found")
            return events

        for date_str, lessons in data.items():
            if not isinstance(lessons, list):
                continue

            for lesson in lessons:
                if not isinstance(lesson, dict):
                    continue

                try:
                    st_raw = lesson.get('start_time')
                    et_raw = lesson.get('end_time')

                    if not st_raw or not et_raw:
                        continue

                    try:
                        start_dt = datetime.fromisoformat(st_raw)
                        end_dt = datetime.fromisoformat(et_raw)
                    except (ValueError, TypeError):
                        # Fallback for HH:MM:SS format
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
                    _LOGGER.error("Calendar parse error on %s: %s", date_str, err)
        
        return events
