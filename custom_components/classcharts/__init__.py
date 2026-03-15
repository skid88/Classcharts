def sync_get_classcharts_data(email, password, pupil_id, days_to_fetch):
    """Fetch both Timetable and Homework data."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 HA-Integration",
        "Content-Type": "application/x-www-form-urlencoded"
    })
    
    try:
        # 1. Login
        login_resp = session.post(
            LOGIN_URL, 
            data={"email": email, "password": password, "remember": "true"},
            timeout=10
        )
        login_resp.raise_for_status()
        
        try:
            login_json = login_resp.json()
        except ValueError:
            _LOGGER.error("API did not return valid JSON")
            return {"timetable": [], "homework": {}}

        # Guard against the 'list' object error you saw earlier
        if not isinstance(login_json, dict):
            _LOGGER.error("Login failed: Expected a dictionary, but got a %s", type(login_json))
            return {"timetable": [], "homework": {}}

        # Safe extraction of the token
        meta = login_json.get("meta", {})
        token = meta.get("session_id") if isinstance(meta, dict) else None

        if not token:
            _LOGGER.error("Login failed: No session_id found.")
            return {"timetable": [], "homework": {}}

        # 2. Fetch Timetable
        full_schedule = {}
        auth_headers = {"Authorization": f"Basic {token}"}
        
        for i in range(days_to_fetch):
            target_date = datetime.date.today() + datetime.timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")

            resp = session.get(
                f"{TIMETABLE_URL}/{pupil_id}?date={date_str}",
                headers=auth_headers,
                timeout=10
            )
            
            if resp.status_code == 200:
                day_data = resp.json()
                if isinstance(day_data, dict):
                    lessons = day_data.get("data", [])
                    full_schedule[date_str] = [
                        _normalize_lesson(lesson) for lesson in lessons
                    ] if isinstance(lessons, list) else []

        # 3. Fetch Homework
        hw_from = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        hw_to = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        hw_url = f"https://www.classcharts.com/apiv2parent/homeworks/{pupil_id}"
        
        hw_resp = session.get(
            hw_url,
            params={"display_date": "due_date", "from": hw_from, "to": hw_to},
            headers=auth_headers,
            timeout=10
        )
        
        homework_data = {}
        if hw_resp.status_code == 200:
            homework_data = hw_resp.json()

        # --- THE FIX FOR THE SENSORS ---
        # Get today's date string to pull out just today's list for the sensors
        today_str = datetime.date.today().strftime("%Y-%m-%d")

        return {
            "timetable": full_schedule.get(today_str, []), # Pass list, not dict
            "homework": homework_data,
            "full_schedule": full_schedule # Keep this for the calendar platform
        }

    except Exception:
        _LOGGER.exception("Unexpected error during Class Charts sync")
        return {"timetable": [], "homework": {}}
    finally:
        session.close()
