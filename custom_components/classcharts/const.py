"""Constants for the Class Charts integration."""

DOMAIN = "classcharts"

# Updated for the standard Class Charts Parent API structure
BASE_URL = "https://www.classcharts.com/apiv2parent"
LOGIN_URL = f"{BASE_URL}/login"
PING_URL = f"{BASE_URL}/ping"      # <--- Added for revalidation
PUPILS_URL = f"{BASE_URL}/pupils"
TIMETABLE_URL = f"{BASE_URL}/timetable"
HOMEWORK_URL = "https://www.classcharts.com/apiv2parent/homeworks"

# Configuration Keys
CONF_PUPIL_ID = "pupil_id"

# Attributes
ATTR_TEACHER = "teacher"
ATTR_ROOM = "room"
ATTR_SUBJECT = "subject"

#Define
CONF_REFRESH_INTERVAL = "refresh_interval"
CONF_DAYS_TO_FETCH = "days_to_fetch"
