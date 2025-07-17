# adk_ollama_tool/tools/weather_api_tool.py
import httpx
import os

class WeatherAPITool:
    """
    A tool to fetch current weather data using the OpenWeatherMap API.
    Requires an API key.
    """
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("OpenWeatherMap API Key is required for WeatherAPITool. Please set OPENWEATHER_API_KEY environment variable.")
        self._api_key = api_key
        self._base_url = "http://api.openweathermap.org/data/2.5/weather"
        self._client = httpx.AsyncClient()

    async def get_current_weather(self, city_name: str) -> dict or None:
        """
        Fetches current weather data for a given city from OpenWeatherMap API.
        Returns a dictionary of weather data if successful, None otherwise.
        Temperature is in Celsius (units="metric").
        """
        params = {
            "q": city_name,
            "appid": self._api_key,
            "units": "metric"
        }
        try:
            print(f"WeatherAPITool: Fetching weather for {city_name} from OpenWeatherMap.")
            response = await self._client.get(self._base_url, params=params, timeout=10.0)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            data = response.json()

            # OpenWeatherMap returns 'cod: 200' for success
            if data and data.get("cod") == 200:
                print(f"WeatherAPITool: Successfully retrieved weather for {city_name}.")
                return data
            else:
                message = data.get('message', 'Unknown error from OpenWeatherMap API')
                print(f"WeatherAPITool: API error for {city_name}: {message}")
                return None
        except httpx.RequestError as exc:
            print(f"WeatherAPITool: An error occurred while connecting to OpenWeatherMap: {exc}")
            return None
        except httpx.HTTPStatusError as exc:
            print(f"WeatherAPITool: OpenWeatherMap responded with an HTTP error: {exc.response.status_code} - {exc.response.text}")
            return None
        except Exception as e:
            print(f"WeatherAPITool: An unexpected error occurred: {e}")
            return None