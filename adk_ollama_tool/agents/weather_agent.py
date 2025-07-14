# adk_ollama_tool/agents/weather_agent.py
# CORRECTED: Agent class location for google-adk v1.6.1
from google.adk.agents.llm_agent import Agent 
from tools.weather_api_tool import WeatherAPITool # Import the weather tool
from typing import Any # Used as a temporary placeholder for message type hinting

# IMPORTANT: MessageBuilder and Message are NOT found at this path in google-adk v1.6.1.
# You MUST consult the google-adk v1.6.1 documentation to find the correct way
# to build messages and handle message types for this version of the library.
# This line is commented out. The code using MessageBuilder() and type hinting with Message
# will need to be updated based on the new ADK API.
# from google.adk.message import MessageBuilder, Message 

class WeatherAgent(Agent):
    """
    An agent that provides current weather data for Indian cities using a WeatherAPITool.
    """
    def __init__(self, agent_id: str, weather_tool: WeatherAPITool):
        super().__init__(agent_id)
        self._weather_tool = weather_tool
        print(f"WeatherAgent {self.id} initialized.")

    # The type hint `message: Message` will now refer to `Any` if Message is not imported.
    # The return type `-> Message` will also refer to `Any`.
    async def handle_message(self, message: Any): # Changed type hint from Message to Any
        """
        Processes incoming ADK messages, attempting to extract a city name
        to fetch weather data.
        """
        # CRITICAL: message.text() might not work if 'Message' class is gone.
        # You need to find the equivalent way to access message content in ADK v1.6.1.
        # For now, we'll assume it's still accessible this way, but be prepared to change.
        query = message.text().lower()
        print(f"WeatherAgent received query: '{query}' from {message.sender_id}")

        city = None
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
        
        # CRITICAL: MessageBuilder() will cause a NameError here.
        # You need to find the correct way to build a response message in ADK v1.6.1.
        # For now, this line is commented out and replaced with a placeholder return.
        # return MessageBuilder().text_message(response_text).add_sender_id(self.id).add_recipient_id(message.sender_id).build()
        # Placeholder return: You MUST replace this with the actual message building for ADK v1.6.1
        # For example, it might be something like:
        # return Agent.create_text_message(response_text, sender_id=self.id, recipient_id=message.sender_id)
        # OR a new Message object type.
        return {"response_text": response_text, "sender_id": self.id, "recipient_id": message.sender_id, "NOTE": "Message building needs update for ADK v1.6.1"}


    async def get_response(self, request_data: dict) -> Any: # Changed return type hint from Message to Any
        """
        Required ADK method to get a response for direct HTTP requests.
        Converts the request_data to a Message and passes it to handle_message.
        """
        if isinstance(request_data, dict) and "query" in request_data:
            # CRITICAL: MessageBuilder() will cause a NameError here.
            # You need to find the correct way to build a mock message in ADK v1.6.1.
            # For now, using a simple dict as a mock, but this might not be compatible.
            # mock_message = MessageBuilder().text_message(request_data["query"]).add_sender_id("adk_client_http_request").add_recipient_id(self.id).build()
            mock_message = {"text": request_data["query"], "sender_id": "adk_client_http_request", "recipient_id": self.id}
            
            # handle_message expects a 'Message' type, which we've temporarily changed to 'Any'.
            # This call might still fail if handle_message expects specific Message attributes (like .text()).
            return await self.handle_message(mock_message)
        
        # CRITICAL: MessageBuilder() will cause a NameError here.
        # return MessageBuilder().text_message("Invalid request format to WeatherAgent").add_sender_id(self.id).add_recipient_id("unknown").build()
        return {"error": "Invalid request format to WeatherAgent", "sender_id": self.id, "recipient_id": "unknown", "NOTE": "Message building needs update for ADK v1.6.1"}