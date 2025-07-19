# adk_ollama_tool/agents/weather_agent.py
import httpx
from google.adk.agents.llm_agent import Agent
from google.genai.types import UserContent, ModelContent, Part
import time # Needed for Unix timestamp, if calling historical

class WeatherAgent(Agent):
    def __init__(self, agent_id: str, mcp_server_url: str, api_key: str):
        super().__init__(name=agent_id)
        self._mcp_server_url = mcp_server_url
        self._api_key = api_key # Still pass, though MCP handles it for OWM. Could be used for other APIs.
        self._client = httpx.AsyncClient()
        print(f"WeatherAgent '{self.name}' initialized.")

    async def get_current_weather(self, city: str):
        """
        Fetches current weather data for a given city by calling MCP server's
        /weather_current endpoint.
        """
        url = f"{self._mcp_server_url}/weather_current?city={city}"
        try:
            print(f"WeatherAgent: Calling MCP for current weather: {url}")
            response = await self._client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            # The structure of the response now comes from MCP's parsing
            # of One Call API 3.0 'current' data.
            temp = data.get("temperature", "N/A")
            desc = data.get("description", "N/A")
            humidity = data.get("humidity", "N/A")
            
            return {"temperature": temp, "description": desc, "humidity": humidity}
        except httpx.HTTPStatusError as e:
            print(f"WeatherAgent: HTTP error fetching weather for {city} from MCP: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Weather API error via MCP: {e.response.text}")
        except httpx.RequestError as e:
            print(f"WeatherAgent: Network error fetching weather for {city} from MCP: {e}")
            raise Exception(f"Weather API connection error via MCP: {e}")
        except Exception as e:
            print(f"WeatherAgent: An unexpected error occurred fetching weather for {city} from MCP: {e}")
            raise Exception(f"Failed to get weather data via MCP: {e}")

    # You could add a similar method for historical if needed by the agent:
    async def get_historical_weather(self, city: str, dt: int):
        url = f"{self._mcp_server_url}/weather_historical?city={city}&dt={dt}"
        try:
            print(f"WeatherAgent: Calling MCP for historical weather: {url}")
            response = await self._client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            # Parse historical data from MCP response
            temp = data.get("temperature", "N/A")
            desc = data.get("description", "N/A")
            humidity = data.get("humidity", "N/A")
            return {"temperature": temp, "description": desc, "humidity": humidity, "actual_dt": data.get("actual_data_dt")}
        except Exception as e:
            print(f"WeatherAgent: Error getting historical weather: {e}")
            raise

    async def handle_message(self, message: UserContent, city: str = "Bengaluru") -> ModelContent:
        query = ""
        for part in message.parts:
            if hasattr(part, 'text') and part.text:
                query = part.text.lower()
                break

        print(f"WeatherAgent '{self.name}' received query: '{query}' for city: '{city}' from {message.role}")

        response_text = "I'm sorry, I don't understand that weather query."

        if "weather in" in query or "weather for" in query or "current weather" in query:
            if "weather in" in query:
                parts = query.split("weather in", 1)
                if len(parts) > 1:
                    city_from_query = parts[1].strip().split(" ")[0]
                    if city_from_query:
                        city = city_from_query.capitalize()

            try:
                weather_data_extracted = await self.get_current_weather(city) 
                temp = weather_data_extracted.get("temperature", "N/A")
                desc = weather_data_extracted.get("description", "N/A")
                humidity = weather_data_extracted.get("humidity", "N/A")
                
                if temp != "N/A" and desc != "N/A":
                    response_text = f"The current weather in {city} is {desc} with a temperature of {temp}°C and {humidity}% humidity."
                else:
                    response_text = f"Could not retrieve full current weather data for {city}."
            except Exception as e:
                response_text = f"Sorry, I couldn't get the current weather for {city} right now: {e}"
        elif "historical weather" in query and "for" in query: # Example for historical query
            parts = query.split("historical weather for", 1)
            if len(parts) > 1:
                city_and_time = parts[1].strip()
                # Basic parsing, needs improvement for real dates/times
                city_from_query = city_and_time.split(" ")[0].capitalize()
                # For simplicity, let's request for 24 hours ago for historical test
                historical_dt = int(time.time()) - (24 * 3600) 
                try:
                    historical_data_extracted = await self.get_historical_weather(city_from_query, historical_dt)
                    temp = historical_data_extracted.get("temperature", "N/A")
                    desc = historical_data_extracted.get("description", "N/A")
                    response_text = f"Historical weather in {city_from_query} around {time.ctime(historical_dt)} was {desc} with a temperature of {temp}°C."
                except Exception as e:
                    response_text = f"Sorry, I couldn't get historical weather for {city_from_query}: {e}"
        else:
            return None

        print(f"WeatherAgent responding with: '{response_text}'")
        return ModelContent(parts=[Part(text=response_text)])

    async def get_response(self, request_data: dict) -> ModelContent:
        if isinstance(request_data, dict) and "query" in request_data:
            city = request_data.get("city", "Bengaluru") # Default city for direct requests
            mock_message = UserContent(parts=[Part(text=request_data["query"])])
            return await self.handle_message(mock_message, city)
        
        return ModelContent(
            parts=[Part(text="Invalid request format to WeatherAgent. Expects a 'query' key in dict.")]
        )