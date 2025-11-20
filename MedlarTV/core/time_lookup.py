"""
Real-time lookup for current time by location
Uses WorldTimeAPI (free, no key required)
"""

import requests
from datetime import datetime

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
        # Add more as needed
    }

    print("[DEBUG time_lookup] Normalizing location...")
    location_lower = location.lower().strip()
    print(f"[DEBUG time_lookup] location_lower={location_lower!r}")

    print("[DEBUG time_lookup] Resolving timezone...")
    timezone = timezone_map.get(location_lower, f"Asia/{location.title()}")
    print(f"[DEBUG time_lookup] Using timezone={timezone!r}")

    try:
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

    # Common location indicators
    locations = [
        "philippines", "manila",
        "japan", "tokyo",
        "uk", "london",
        "usa", "america", "new york", "california", "los angeles"
    ]

    print("[DEBUG time_lookup] Checking for location keywords...")
    for location in locations:
        if location in message_lower:
            print(f"[DEBUG time_lookup] Matched location={location!r}")
            return True, location

    print("[DEBUG time_lookup] No location keyword found, returning (False, None)")
    return False, None


# Integration with LLM brain
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
        time_info = get_current_time(location)
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
