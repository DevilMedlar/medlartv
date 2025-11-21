"""
Real-time lookup for current time by location
Uses WorldTimeAPI (free, no key required)
"""

import requests
from datetime import datetime
import re

def get_current_time(location: str) -> str:
    """
    Get current time for a location.
    
    Args:
        location: City name or timezone (e.g., "Manila", "Philippines", "Asia/Manila")
    
    Returns:
        Formatted time string or error message
    """
    print(f"[DEBUG time_lookup] get_current_time() called with location={location!r}")

    # Map common locations to timezones
    timezone_map = {
        "philippines": "Asia/Manila",
        "manila": "Asia/Manila",
        "japan": "Asia/Tokyo",
        "tokyo": "Asia/Tokyo",
        "uk": "Europe/London",
        "london": "Europe/London",
        "usa": "America/New_York",
        "new york": "America/New_York",
        "california": "America/Los_Angeles",
        "los angeles": "America/Los_Angeles",
        "china": "Asia/Shanghai",
        "canada": "America/Toronto",
        "russia": "Europe/Moscow",
    }

    print("[DEBUG time_lookup] Normalizing location...")
    location_lower = location.lower().strip()
    print(f"[DEBUG time_lookup] location_lower={location_lower!r}")

    print("[DEBUG time_lookup] Resolving timezone...")
    timezone = timezone_map.get(location_lower)
    print(f"[DEBUG time_lookup] Using timezone={timezone!r}")

    try:
        if not timezone:
            print("[DEBUG time_lookup] No direct timezone mapping, returning None")
            return None
        url = f"http://worldtimeapi.org/api/timezone/{timezone}"
        print(f"[DEBUG time_lookup] Requesting URL: {url}")
        response = requests.get(url, timeout=3)
        print(f"[DEBUG time_lookup] response.status_code={response.status_code}")

        if response.status_code == 200:
            print("[DEBUG time_lookup] 200 OK, parsing JSON...")
            data = response.json()
            datetime_str = data.get("datetime")
            print(f"[DEBUG time_lookup] datetime_raw={datetime_str!r}")

            if datetime_str:
                print("[DEBUG time_lookup] Converting ISO datetime...")
                dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                formatted_time = dt.strftime("%I:%M %p")
                formatted_date = dt.strftime("%B %d, %Y")

                print(f"[DEBUG time_lookup] formatted_time={formatted_time!r}")
                print(f"[DEBUG time_lookup] formatted_date={formatted_date!r}")

                return f"Current time in {location}: {formatted_time} on {formatted_date}"

        # If specific timezone fails, try generic search
        print("[DEBUG time_lookup] Non-200 or missing datetime, checking fallback logic...")
        if "Asia/" in timezone:
            print(f"[DEBUG time_lookup] Returning fallback timezone message for {location!r}")
            return f"Unable to get exact time for {location}. Timezone: {timezone}"

        print("[DEBUG time_lookup] Returning None (lookup failed)")
        return None

    except Exception as e:
        print(f"[DEBUG time_lookup] ERROR inside get_current_time(): {e}")
        return None


def should_lookup_time(message: str) -> tuple[bool, str]:
    """
    Check if message is asking for current time.
    
    Returns:
        (should_lookup, location)
    """
    print(f"[DEBUG time_lookup] should_lookup_time() called message={message!r}")
    message_lower = message.lower()
    print(f"[DEBUG time_lookup] message_lower={message_lower!r}")

    # Time indicators
    time_indicators = [
        "what time is it",
        "current time",
        "time now",
        "what's the time",
        "whats the time"
    ]

    print("[DEBUG time_lookup] Checking time indicators...")
    indicator_match = any(indicator in message_lower for indicator in time_indicators)
    print(f"[DEBUG time_lookup] indicator_match={indicator_match}")

    if not indicator_match:
        print("[DEBUG time_lookup] No time indicators found, returning (False, None)")
        return False, None

    print("[DEBUG time_lookup] Extracting location via pattern 'in <...>'...")
    m = re.search(r"\bin\s+([a-zA-Z/_\-\s]+)", message_lower)
    if m:
        loc = m.group(1).strip().strip("?.! ")
        if loc.startswith("the "):
            loc = loc[4:]
        print(f"[DEBUG time_lookup] Extracted location={loc!r}")
        return True, loc
    print("[DEBUG time_lookup] No location phrase found, returning (True, None) for local default")
    return True, None


# Integration with LLM brain
def resolve_timezones_for_query(query: str) -> list[str]:
    print(f"[DEBUG time_lookup] resolve_timezones_for_query() query={query!r}")
    q = (query or "").strip().lower()
    if not q:
        return []
    synonyms = {
        "rusia": "russia",
        "united states": "us",
        "united kingdom": "uk",
        "england": "europe/london",
        "nyc": "new york",
        "la": "los angeles",
        "eastern time": "america/new_york",
        "est": "america/new_york",
        "edt": "america/new_york",
    }
    q = synonyms.get(q, q)
    zones = list_timezones(None)
    if not zones:
        return []
    pattern_space = q.replace(" ", "_")
    matches: list[str] = []
    for z in zones:
        zl = z.lower()
        last = z.split("/")[-1].lower().replace("_", " ")
        if q in zl or pattern_space in zl or q in last:
            matches.append(z)
    # Exact timezone path
    if "/" in q:
        for z in zones:
            if z.lower() == q:
                return [z]
    # Deduplicate
    uniq = []
    seen = set()
    for z in matches:
        if z not in seen:
            uniq.append(z)
            seen.add(z)
    print(f"[DEBUG time_lookup] resolve_timezones_for_query() matched {len(uniq)} zones")
    return uniq

def get_times_for_location(location: str):
    loc = location.lower().strip()
    multi = {
        "usa": [
            ("America/New_York", "Eastern"),
            ("America/Chicago", "Central"),
            ("America/Denver", "Mountain"),
            ("America/Los_Angeles", "Pacific"),
        ],
        "america": [
            ("America/New_York", "Eastern"),
            ("America/Chicago", "Central"),
            ("America/Denver", "Mountain"),
            ("America/Los_Angeles", "Pacific"),
        ],
        "us": [
            ("America/New_York", "Eastern"),
            ("America/Chicago", "Central"),
            ("America/Denver", "Mountain"),
            ("America/Los_Angeles", "Pacific"),
        ],
        "canada": [
            ("America/Vancouver", "Pacific"),
            ("America/Edmonton", "Mountain"),
            ("America/Winnipeg", "Central"),
            ("America/Toronto", "Eastern"),
            ("America/Halifax", "Atlantic"),
            ("America/St_Johns", "Newfoundland"),
        ],
        "russia": [
            ("Europe/Moscow", "Moscow"),
            ("Asia/Yekaterinburg", "Yekaterinburg"),
            ("Asia/Novosibirsk", "Novosibirsk"),
            ("Asia/Krasnoyarsk", "Krasnoyarsk"),
            ("Asia/Irkutsk", "Irkutsk"),
            ("Asia/Yakutsk", "Yakutsk"),
            ("Asia/Vladivostok", "Vladivostok"),
            ("Asia/Magadan", "Magadan"),
            ("Asia/Kamchatka", "Kamchatka"),
        ],
        "china": [
            ("Asia/Shanghai", "China"),
        ],
    }
    if loc in multi:
        parts = []
        for tz, label in multi[loc]:
            try:
                r = requests.get(f"http://worldtimeapi.org/api/timezone/{tz}", timeout=3)
                if r.status_code == 200:
                    data = r.json()
                    ds = data.get("datetime")
                    if ds:
                        dt = datetime.fromisoformat(ds.replace('Z', '+00:00'))
                        parts.append(f"{label}: {dt.strftime('%I:%M %p')}")
            except Exception:
                continue
        if parts:
            return " | ".join(parts)
        return None
    zones = resolve_timezones_for_query(location)
    if not zones:
        return None
    if len(zones) == 1:
        try:
            r = requests.get(f"http://worldtimeapi.org/api/timezone/{zones[0]}", timeout=3)
            if r.status_code == 200:
                data = r.json()
                ds = data.get("datetime")
                if ds:
                    dt = datetime.fromisoformat(ds.replace('Z', '+00:00'))
                    return f"Current time in {location}: {dt.strftime('%I:%M %p')} on {dt.strftime('%B %d, %Y')}"
        except Exception:
            return None
        return None
    parts = []
    for tz in zones[:8]:
        try:
            r = requests.get(f"http://worldtimeapi.org/api/timezone/{tz}", timeout=3)
            if r.status_code == 200:
                data = r.json()
                ds = data.get("datetime")
                if ds:
                    dt = datetime.fromisoformat(ds.replace('Z', '+00:00'))
                    label = tz.split("/")[-1].replace("_", " ")
                    parts.append(f"{label}: {dt.strftime('%I:%M %p')}")
        except Exception:
            continue
    return " | ".join(parts) if parts else None

def get_default_local_time() -> str | None:
    try:
        r = requests.get("http://worldtimeapi.org/api/timezone/America/New_York", timeout=3)
        if r.status_code == 200:
            data = r.json()
            ds = data.get("datetime")
            if ds:
                dt = datetime.fromisoformat(ds.replace('Z', '+00:00'))
                return f"Eastern Time (US & Canada): {dt.strftime('%I:%M %p')} on {dt.strftime('%B %d, %Y')}"
    except Exception:
        return None
    return None

def list_timezones(filter_text: str | None = None) -> list[str]:
    try:
        r = requests.get("http://worldtimeapi.org/api/timezone", timeout=4)
        if r.status_code != 200:
            return []
        zones = r.json() or []
        zones = [str(z) for z in zones]
        if filter_text:
            ft = filter_text.lower()
            zones = [z for z in zones if ft in z.lower()]
        return zones
    except Exception:
        return []

def world_clock_summary() -> str:
    zones = [
        ("Europe/London", "London"),
        ("Europe/Berlin", "Berlin"),
        ("Europe/Moscow", "Moscow"),
        ("Africa/Johannesburg", "Johannesburg"),
        ("Asia/Dubai", "Dubai"),
        ("Asia/Kolkata", "Delhi"),
        ("Asia/Shanghai", "Shanghai"),
        ("Asia/Tokyo", "Tokyo"),
        ("Australia/Sydney", "Sydney"),
        ("Pacific/Auckland", "Auckland"),
        ("America/Sao_Paulo", "São Paulo"),
        ("America/New_York", "New York"),
        ("America/Chicago", "Chicago"),
        ("America/Denver", "Denver"),
        ("America/Los_Angeles", "Los Angeles"),
        ("America/Anchorage", "Anchorage"),
        ("Pacific/Honolulu", "Honolulu"),
    ]
    parts = []
    for tz, label in zones:
        try:
            r = requests.get(f"http://worldtimeapi.org/api/timezone/{tz}", timeout=3)
            if r.status_code == 200:
                data = r.json()
                ds = data.get("datetime")
                if ds:
                    dt = datetime.fromisoformat(ds.replace('Z', '+00:00'))
                    parts.append(f"{label}: {dt.strftime('%I:%M %p')}")
        except Exception:
            continue
    return " | ".join(parts) if parts else "World clock unavailable"

def enhance_time_query(user_message: str) -> str:
    """
    If message asks for time, get real time data.
    Returns context string to add to prompt, or empty string.
    """
    print(f"[DEBUG time_lookup] enhance_time_query() called with user_message={user_message!r}")
    should_lookup, location = should_lookup_time(user_message)
    print(f"[DEBUG time_lookup] should_lookup={should_lookup}, location={location!r}")

    if should_lookup and location:
        print("[DEBUG time_lookup] Triggering real-time lookup...")
        time_info = get_times_for_location(location)
        print(f"[DEBUG time_lookup] time_info={time_info!r}")

        if time_info:
            print("[DEBUG time_lookup] Returning enriched context block")
            return f"\n\n[REAL-TIME DATA]\n{time_info}\n[END REAL-TIME DATA]\n\n"

    print("[DEBUG time_lookup] No lookup triggered, returning empty string")
    return ""


if __name__ == "__main__":
    print("[DEBUG time_lookup] __main__ test block running...")
    print("Testing time lookup...")
    print(get_current_time("Philippines"))
    print(get_current_time("Tokyo"))
    print(get_current_time("London"))

    print("\nTesting detection...")
    tests = [
        "What time is it in the Philippines?",
        "Current time in Tokyo?",
        "Who made you?"
    ]

    for test in tests:
        print(f"[DEBUG time_lookup] Testing message: {test!r}")
        should, loc = should_lookup_time(test)
        print(f"{test} -> {should}, {loc}")
