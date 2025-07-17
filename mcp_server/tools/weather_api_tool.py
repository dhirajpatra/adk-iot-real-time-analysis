# mcp_server/tools/weather_api_tool.py
import httpx
import os
import time # Needed for unix timestamp

class WeatherAPITool:
    """
    A tool to fetch weather data using the OpenWeatherMap API,
    supporting Geocoding, Current Weather (2.5), and One Call API 3.0 (Timemachine).
    Requires an API key.
    """
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("OpenWeatherMap API Key is required for WeatherAPITool. Please set OPENWEATHER_API_KEY environment variable.")
        self._api_key = api_key
        self._geocoding_base_url = "http://api.openweathermap.org/geo/1.0/direct"
        self._current_weather_base_url = "http://api.openweathermap.org/data/2.5/weather" # <<< USING 2.5 FOR CURRENT
        self._timemachine_base_url = "https://api.openweathermap.org/data/3.0/onecall/timemachine" # Still for historical

        self._client = httpx.AsyncClient()
        print(f"WeatherAPITool initialized. (API Key: {self._api_key[:5]}*****)")

    async def _get_coords_from_city(self, city_name: str) -> tuple or None:
        """
        Converts a city name to latitude and longitude using the Geocoding API.
        Returns (lat, lon) or None if not found.
        """
        params = {
            "q": city_name,
            "limit": 1, # Get only the top result
            "appid": self._api_key,
        }
        try:
            print(f"WeatherAPITool: Geocoding coordinates for {city_name}.")
            response = await self._client.get(self._geocoding_base_url, params=params, timeout=5.0)
            response.raise_for_status()
            data = response.json()

            if data and isinstance(data, list) and len(data) > 0:
                coords = data[0]
                lat = coords.get("lat")
                lon = coords.get("lon")
                if lat is not None and lon is not None:
                    print(f"WeatherAPITool: Found coordinates for {city_name}: ({lat}, {lon})")
                    return (lat, lon)
            print(f"WeatherAPITool: No coordinates found for {city_name}.")
            return None
        except httpx.RequestError as exc:
            print(f"WeatherAPITool: Network error geocoding {city_name}: {exc}")
            return None
        except httpx.HTTPStatusError as exc:
            print(f"WeatherAPITool: HTTP error geocoding {city_name}: {exc.response.status_code} - {exc.response.text}")
            return None
        except Exception as e:
            print(f"WeatherAPITool: Unexpected error geocoding {city_name}: {e}")
            return None

    async def get_current_weather_2_5(self, city_name: str) -> dict or None:
        """
        Fetches current weather data for a given city using OpenWeatherMap Current Weather Data 2.5.
        First gets coordinates, then queries the 2.5 API.
        """
        coords = await self._get_coords_from_city(city_name)
        if not coords:
            print(f"WeatherAPITool: Could not get coordinates for {city_name} for current weather.")
            return None

        lat, lon = coords
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self._api_key,
            "units": "metric" # For Celsius
        }
        try:
            print(f"WeatherAPITool: Fetching current weather for ({lat}, {lon}) from 2.5 API.")
            response = await self._client.get(self._current_weather_base_url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            if data and data.get("cod") == 200: # 2.5 API returns 'cod: 200' on success
                print(f"WeatherAPITool: Successfully retrieved current weather for {city_name}.")
                return data # Return the entire 2.5 API response
            else:
                message = data.get('message', 'Unknown error or no data from 2.5 API')
                print(f"WeatherAPITool: API error for current weather ({city_name}): {message}. Full response: {data}")
                return None
        except httpx.RequestError as exc:
            print(f"WeatherAPITool: Network error fetching current weather (2.5 API): {exc}")
            return None
        except httpx.HTTPStatusError as exc:
            print(f"WeatherAPITool: HTTP error from 2.5 API (current): {exc.response.status_code} - {exc.response.text}")
            return None
        except Exception as e:
            print(f"WeatherAPITool: Unexpected error fetching current weather (2.5 API): {e}")
            return None

    async def get_historical_weather_one_call_3_0(self, city_name: str, dt: int) -> dict or None:
        """
        Fetches historical weather data for a given city and Unix timestamp
        using the OpenWeatherMap One Call API 3.0 (Timemachine).
        First gets coordinates, then queries the Timemachine API.
        """
        coords = await self._get_coords_from_city(city_name)
        if not coords:
            print(f"WeatherAPITool: Could not get coordinates for {city_name} for historical weather.")
            return None

        lat, lon = coords
        params = {
            "lat": lat,
            "lon": lon,
            "dt": dt,
            "appid": self._api_key,
            "units": "metric" # For Celsius
        }
        try:
            print(f"WeatherAPITool: Fetching historical weather for ({lat}, {lon}) at {dt} from One Call API 3.0 Timemachine.")
            response = await self._client.get(self._timemachine_base_url, params=params, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            if data and "data" in data and len(data["data"]) > 0:
                print(f"WeatherAPITool: Successfully retrieved historical weather for {city_name}.")
                return data # Return the entire response containing the 'data' array
            else:
                message = data.get('message', 'Unknown error or no historical data from One Call API 3.0 Timemachine')
                print(f"WeatherAPITool: API error for historical weather ({city_name}, {dt}): {message}. Full response: {data}")
                return None
        except httpx.RequestError as exc:
            print(f"WeatherAPITool: Network error fetching historical weather: {exc}")
            return None
        except httpx.HTTPStatusError as exc:
            print(f"WeatherAPITool: HTTP error from One Call API 3.0 Timemachine: {exc.response.status_code} - {exc.response.text}")
            return None
        except Exception as e:
            print(f"WeatherAPITool: Unexpected error fetching historical weather: {e}")
            return None