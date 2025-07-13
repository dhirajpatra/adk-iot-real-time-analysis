# adk_ollama_tool/agents/smart_home_agent.py
import random
from adk.agent import Agent
from adk.message import MessageBuilder, Message

class SmartHomeAgent(Agent):
    """
    A simple agent that simulates smart home data and responds to queries about its state.
    """
    def __init__(self, agent_id: str, initial_state: dict):
        super().__init__(agent_id)
        self._state = initial_state # Holds simulated sensor data
        print(f"SmartHomeAgent {self.id} initialized with state: {self._state}")

    async def handle_message(self, message: Message):
        """
        Processes incoming ADK messages from other agents or clients.
        """
        query = message.text().lower()
        print(f"SmartHomeAgent received query: '{query}' from {message.sender_id}")

        response_text = "I'm sorry, I don't understand that specific query about the smart home."

        if "temperature" in query:
            response_text = f"The current simulated temperature is {self._state.get('temperature', 'N/A')}°C."
        elif "light" in query:
            response_text = f"The lights are currently {self._state.get('light', 'N/A')}."
        elif "status" in query or "home state" in query:
            response_text = f"The current smart home status is: Temperature {self._state.get('temperature')}°C, Lights are {self._state.get('light')}."
        elif "update temperature" in query or "change temperature" in query:
            # Simulate a dynamic update to the temperature
            self._state['temperature'] = round(random.uniform(20.0, 30.0), 1)
            response_text = f"Simulated temperature has been updated to {self._state['temperature']}°C."

        print(f"SmartHomeAgent responding with: '{response_text}' to {message.sender_id}")
        return MessageBuilder().text_message(response_text).add_sender_id(self.id).add_recipient_id(message.sender_id).build()

    # get_response is generally used by the ADK client for direct HTTP requests to the agent,
    # mapping to an ADK message for handle_message.
    async def get_response(self, request_data: dict) -> Message:
        """
        Required ADK method to get a response for direct HTTP requests.
        Converts the request_data to a Message and passes it to handle_message.
        """
        if isinstance(request_data, dict) and "query" in request_data:
            # Create a mock ADK message from the HTTP request data
            mock_message = MessageBuilder().text_message(request_data["query"]).add_sender_id("adk_client_http_request").add_recipient_id(self.id).build()
            return await self.handle_message(mock_message)
        
        return MessageBuilder().text_message("Invalid request format to SmartHomeAgent").add_sender_id(self.id).add_recipient_id("unknown").build()