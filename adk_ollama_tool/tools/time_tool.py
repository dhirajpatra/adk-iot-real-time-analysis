# adk_ollama_tool/tools/time_tool.py
import datetime
from zoneinfo import ZoneInfo # Requires Python 3.9+ or 'tzdata' package for older versions

def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city.

    Args:
        city (str): The name of the city for which to retrieve the current time.

    Returns:
        dict: status and result or error msg.
    """

    # For a real application, you'd want a more comprehensive timezone lookup.
    # This is a simplified mapping for common cities.
    city_timezones = {
        "new york": "America/New_York",
        "london": "Europe/London",
        "tokyo": "Asia/Tokyo",
        "mumbai": "Asia/Kolkata", # India's timezone is Asia/Kolkata
        "delhi": "Asia/Kolkata",
        "bengaluru": "Asia/Kolkata",
        "chennai": "Asia/Kolkata",
        "kolkata": "Asia/Kolkata",
        # Add more cities as needed
    }

    tz_identifier = city_timezones.get(city.lower())

    if not tz_identifier:
        return {
            "status": "error",
            "error_message": (
                f"Sorry, I don't have timezone information for '{city}'. "
                "Try New York, London, Tokyo, or any major Indian city like Mumbai, Delhi, Bengaluru, Chennai, or Kolkata."
            ),
        }

    try:
        tz = ZoneInfo(tz_identifier)
        now = datetime.datetime.now(tz)
        report = (
            f'The current time in {city.capitalize()} is {now.strftime("%Y-%m-%d %H:%M:%S %Z%z")}'
        )
        return {"status": "success", "report": report}
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"An error occurred while getting time for {city}: {e}",
        }