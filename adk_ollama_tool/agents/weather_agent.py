# adk_ollama_tool/agents/weather_agent.py
from adk.agent import Agent
from adk.message import MessageBuilder, Message
from tools.weather_api_tool import WeatherAPITool # Import the weather tool

class WeatherAgent(Agent):
    """
    An agent that provides current weather data for Indian cities using a WeatherAPITool.
    """
    def __init__(self, agent_id: str, weather_tool: WeatherAPITool):
        super().__init__(agent_id)
        self._weather_tool = weather_tool
        print(f"WeatherAgent {self.id} initialized.")

    async def handle_message(self, message: Message):
        """
        Processes incoming ADK messages, attempting to extract a city name
        to fetch weather data.
        """
        query = message.text().lower()
        print(f"WeatherAgent received query: '{query}' from {message.sender_id}")

        city = None
        # Simple keyword extraction for Indian cities for demonstration
        # In a real app, you might use NLP or a more robust city list/lookup.
        indian_cities = ["mumbai", "delhi", "bengaluru", "chennai", "kolkata", "hyderabad", "pune", "ahmedabad", "jaipur", "lucknow", "nagpur", "patna"]
        for c in indian_cities:
            if c in query:
                city = c.capitalize() # Capitalize for API consistency
                break

        if city:
            try:
                weather_data = await self._weather_tool.get_current_weather(city)
                if weather_data:
                    temp = weather_data.get('main', {}).get('temp')
                    description = weather_data.get('weather', [{}])[0].get('description')
                    response_text = f"The current weather in {city} is {description} with a temperature of {temp}°C."
                else:
                    response_text = f"Could not retrieve weather for {city} from the API. Please check the city name or API status."
            except Exception as e:
                response_text = f"An error occurred while fetching weather for {city}: {e}"
        else:
            response_text = "Please specify an Indian city to get weather information (e.g., 'What's the weather in Mumbai?')."

        print(f"WeatherAgent responding with: '{response_text}' to {message.sender_id}")
        return MessageBuilder().text_message(response_text).add_sender_id(self.id).add_recipient_id(message.sender_id).build()

    async def get_response(self, request_data: dict) -> Message:
        """
        Required ADK method to get a response for direct HTTP requests.
        Converts the request_data to a Message and passes it to handle_message.
        """
        if isinstance(request_data, dict) and "query" in request_data:
            mock_message = MessageBuilder().text_message(request_data["query"]).add_sender_id("adk_client_http_request").add_recipient_id(self.id).build()
            return await self.handle_message(mock_message)
        
        return MessageBuilder().text_message("Invalid request format to WeatherAgent").add_sender_id(self.id).add_recipient_id("unknown").build()