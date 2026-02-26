"""Constants for the Class Charts integration."""

DOMAIN = "classcharts"

# API Endpoints
BASE_URL = "https://www.classcharts.com/api/v2"
LOGIN_URL = f"{BASE_URL}/parent/login"
PUPILS_URL = f"{BASE_URL}/parent/pupils"
TIMETABLE_URL = f"{BASE_URL}/parent/timetable"

# Configuration Keys
CONF_PUPIL_ID = "pupil_id"

# Attributes
ATTR_TEACHER = "teacher"
ATTR_ROOM = "room"
ATTR_SUBJECT = "subject"
