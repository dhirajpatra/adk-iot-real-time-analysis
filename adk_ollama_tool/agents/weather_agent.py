# adk_ollama_tool/agents/weather_agent.py (Corrected)
import httpx # Assuming you use httpx for API calls
from google.adk.agents.llm_agent import Agent
from google.genai.types import UserContent, ModelContent, Part

class WeatherAgent(Agent):
    """
    An agent that fetches real-time weather data using the OpenWeatherMap API
    via the MCP server's weather_api_tool.
    """
    # IMPORTANT: Add mcp_server_url and api_key to the __init__ signature
    def __init__(self, agent_id: str, mcp_server_url: str, api_key: str): # <--- FIX IS HERE
        super().__init__(name=agent_id) # Call the base Agent constructor
        self._mcp_server_url = mcp_server_url # Store these as instance variables
        self._api_key = api_key # Store these as instance variables
        self._client = httpx.AsyncClient() # Initialize an HTTP client for MCP calls
        print(f"WeatherAgent '{self.name}' initialized.")

    async def get_current_weather(self, city: str):
        """
        Fetches current weather data for a given city from the MCP server's weather tool.
        """
        url = f"{self._mcp_server_url}/weather?city={city}&api_key={self._api_key}"
        try:
            response = await self._client.get(url, timeout=10.0) # Add a timeout
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            # print(f"Weather data for {city}: {data}") # Debugging
            return data
        except httpx.HTTPStatusError as e:
            print(f"WeatherAgent: HTTP error fetching weather for {city}: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Weather API error: {e.response.text}")
        except httpx.RequestError as e:
            print(f"WeatherAgent: Network error fetching weather for {city}: {e}")
            raise Exception(f"Weather API connection error: {e}")
        except Exception as e:
            print(f"WeatherAgent: An unexpected error occurred fetching weather for {city}: {e}")
            raise Exception(f"Failed to get weather data: {e}")

    async def handle_message(self, message: UserContent, city: str = "Bengaluru") -> ModelContent:
        """
        Processes incoming ADK messages related to weather queries.
        """
        query = ""
        for part in message.parts:
            if hasattr(part, 'text') and part.text:
                query = part.text.lower()
                break

        print(f"WeatherAgent '{self.name}' received query: '{query}' for city: '{city}' from {message.role}")

        response_text = "I'm sorry, I don't understand that weather query."

        if "weather in" in query or "weather for" in query or "current weather" in query:
            # Extract city from query if present, otherwise use default
            # (More robust city extraction might be needed for a full solution)
            if "weather in" in query:
                parts = query.split("weather in", 1)
                if len(parts) > 1:
                    city_from_query = parts[1].strip().split(" ")[0] # Takes first word after "weather in"
                    if city_from_query:
                        city = city_from_query.capitalize() # Capitalize for API consistency

            try:
                weather_data = await self.get_current_weather(city)
                temp = weather_data.get("temperature", "N/A")
                desc = weather_data.get("description", "N/A")
                humidity = weather_data.get("humidity", "N/A")
                
                if temp != "N/A" and desc != "N/A":
                    response_text = f"The current weather in {city} is {desc} with a temperature of {temp}°C and {humidity}% humidity."
                else:
                    response_text = f"Could not retrieve full weather data for {city}."
            except Exception as e:
                response_text = f"Sorry, I couldn't get the weather for {city} right now: {e}"
        elif "forecast for" in query:
             response_text = f"Forecast functionality is not yet implemented for {city}."
        else:
            return None # Indicate that this agent didn't handle the message

        print(f"WeatherAgent responding with: '{response_text}'")
        return ModelContent(parts=[Part(text=response_text)])

    async def get_response(self, request_data: dict) -> ModelContent:
        """
        Required ADK method to get a response for direct HTTP requests.
        """
        if isinstance(request_data, dict) and "query" in request_data:
            city = request_data.get("city", "London") # Allow city to be passed in request_data
            mock_message = UserContent(parts=[Part(text=request_data["query"])])
            return await self.handle_message(mock_message, city)
        
        return ModelContent(
            parts=[Part(text="Invalid request format to WeatherAgent. Expects a 'query' key in dict.")]
        )