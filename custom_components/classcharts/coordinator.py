"""DataUpdateCoordinator for the Class Charts integration."""
import logging
import datetime
import requests
import json
import urllib.parse
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN, 
    CONF_PUPIL_ID,
    CONF_DAYS_TO_FETCH,
    HOMEWORK_URL,
    BEHAVIOUR_URL
)

_LOGGER = logging.getLogger(__name__)

# Direct, authenticated V2 endpoints
LOGIN_URL = "https://www.classcharts.com/parent/login"
V2_BASE_URL = "https://www.classcharts.com/apiv2parent"

def sync_get_classcharts_data(email, password, pupil_id, days_to_fetch):
    """Fetch data using the verified V2 Cookie + Auth + Handshake loop."""
    session = requests.Session()
    
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.classcharts.com",
        "Referer": "https://www.classcharts.com/",
    })
    
    try:
        session.headers.update({"Content-Type": "application/x-www-form-urlencoded"})
        login_payload = {
            "_method": "POST",
            "email": email,
            "logintype": "existing",
            "password": password,
            "recaptcha-token": "no-token-available"
        }
        encoded_login = urllib.parse.urlencode(login_payload)
        
        login_resp = session.post(
            LOGIN_URL, 
            data=encoded_login,
            allow_redirects=True,
            timeout=15
        )

        # 2. Extract Authenticated V2 Token from Session Cookies
        cookies_dict = session.cookies.get_dict()
        session_token = None
        
        raw_cookie_data = cookies_dict.get("parent_session_credentials")
        if raw_cookie_data:
            try:
                decoded_cookie_str = urllib.parse.unquote(raw_cookie_data)
                cookie_json = json.loads(decoded_cookie_str)
                session_token = cookie_json.get("session_id")
            except Exception:
                pass
                
        # Safe fallback back into the direct cc-session key
        if not session_token:
            session_token = cookies_dict.get("cc-session")
            
        if not session_token:
            raise UpdateFailed("Failed to extract operational security token from handshake cookies.")

        # Update core global headers for the modern AJAX interface
        session.headers.update({
            "Authorization": f"Basic {session_token}",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.classcharts.com/mobile/parent"
        })
        if "Content-Type" in session.headers:
            del session.headers["Content-Type"]

        # 3. Crucial V2 Ping Handshake Initialization
        ping_resp = session.post(f"{V2_BASE_URL}/ping", data="{}", timeout=10)

        if ping_resp.status_code != 200:
            raise UpdateFailed(f"V2 backend gatekeeper rejected API initialization footprint. Code: {ping_resp.status_code}")

        # Check if ping returns token errors
        try:
            ping_json = ping_resp.json()
            if ping_json.get("success") == 0 or ping_json.get("success") is False:
                raise UpdateFailed(f"V2 API authentication handshake failed: {ping_json.get('error')}")
        except ValueError:
            pass

        # 4. Fetch Updated V2 Timetable Data
        full_schedule = {}
        for i in range(days_to_fetch):
            target_date = datetime.date.today() + datetime.timedelta(days=i)
            date_str = target_date.strftime("%Y-%m-%d")

            # Updated V2 path mapping
            resp = session.get(
                f"{V2_BASE_URL}/timetable/{pupil_id}",
                params={"date": date_str},
                timeout=10
            )
            
            if resp.status_code == 200:
                try:
                    day_data = resp.json()
                    lessons = day_data.get("data", []) if isinstance(day_data, dict) else []
                    full_schedule[date_str] = lessons if isinstance(lessons, list) else []
                except Exception as parse_err:
                    _LOGGER.error("Failed parsing V2 timetable for %s: %s", date_str, parse_err)
            else:
                _LOGGER.error("V2 Timetable query failed for %s. Code: %s", date_str, resp.status_code)

        # 5. Fetch Updated V2 Homework Data
        hw_from = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        hw_to = (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        
        hw_resp = session.get(
            f"{HOMEWORK_URL}/{pupil_id}",
            params={"display_date": "due_date", "from": hw_from, "to": hw_to},
            timeout=10
        )
        
        homework_data = {"data": [], "meta": {}}
        if hw_resp.status_code == 200:
            try:
                hw_json = hw_resp.json()
                if isinstance(hw_json, list):
                    homework_data = {"data": hw_json, "meta": {}}
                elif isinstance(hw_json, dict):
                    if "data" in hw_json:
                        homework_data = hw_json
                    else:
                        homework_data = {"data": hw_json.get("homework", hw_json), "meta": hw_json.get("meta", {})}
            except Exception as parse_err:
                _LOGGER.error("Failed parsing V2 homework payload structural map: %s", parse_err)
        else:
            _LOGGER.error("V2 Homework data retrieval failed with code: %s", hw_resp.status_code)

       # 6. Fetch Updated V2 Behaviour Data (Robust Parameters)
        behaviour_from = (datetime.date.today() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
        behaviour_to = datetime.date.today().strftime("%Y-%m-%d")
        
        # We pass both common variations of the date query parameters to ensure compatibility
        query_params = {
            "from": behaviour_from,
            "to": behaviour_to,
            "date_from": behaviour_from,
            "date_to": behaviour_to
        }
        
        _LOGGER.debug("Requesting Class Charts activity data from %s to %s", behaviour_from, behaviour_to)
        
        behaviour_resp = session.get(
            f"{BEHAVIOUR_URL}/{pupil_id}",
            params=query_params,
            timeout=10
        )
        
        behaviour_data = {}
        if behaviour_resp.status_code == 200:
            try:
                behaviour_json = behaviour_resp.json()
                # Log the raw response keys to Home Assistant terminal logs for debugging
                _LOGGER.debug("Class Charts V2 activity raw response keys: %s", list(behaviour_json.keys()))
                
                # Strip out the payload cleanly regardless of structural wraps
                if isinstance(behaviour_json, dict):
                    if "data" in behaviour_json:
                        behaviour_data = behaviour_json["data"]
                    elif "timeline" in behaviour_json:
                        behaviour_data = behaviour_json
                    else:
                        behaviour_data = behaviour_json
                else:
                    behaviour_data = {"history": behaviour_json}
            except Exception as parse_err:
                _LOGGER.error("Failed parsing V2 behaviour data payload: %s", parse_err)
        else:
            _LOGGER.error("V2 Behaviour data retrieval failed with code: %s. Response: %s", behaviour_resp.status_code, behaviour_resp.text)

        # Standardized dictionary output back to the sensor platforms
        return {
            "timetable": full_schedule,
            "homework": homework_data,
            "behaviour": behaviour_data,
        }

    except Exception as err:
        _LOGGER.error("Error fetching Class Charts data payload: %s", err)
        raise UpdateFailed(f"Error communicating with V2 API: {err}")
    finally:
        session.close()
