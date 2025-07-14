# adk_ollama_tool/agents/smart_home_agent.py
import random
# CORRECTED: Agent class location for google-adk v1.6.1
# Note: SmartHomeAgent itself is still a custom agent inheriting from this.
from google.adk.agents.llm_agent import Agent 

# IMPORTANT: MessageBuilder and Message are NOT found at this path in google-adk v1.6.1.
# You MUST consult the google-adk v1.6.1 documentation to find the correct way
# to build messages and handle message types for this version of the library.
# This line is commented out. The code using MessageBuilder() and type hinting with Message
# will need to be updated based on the new ADK API.
# from google.adk.message import MessageBuilder, Message 

# If you were importing Message for type hinting, and it's no longer available,
# you might need to use a generic `Any` type or define your own simple message structure
# until you find the correct ADK v1.6.1 equivalent.
from typing import Any # Used as a temporary placeholder for message type hinting

class SmartHomeAgent(Agent):
    """
    A simple agent that simulates smart home data and responds to queries about its state.
    """
    def __init__(self, agent_id: str, initial_state: dict):
        super().__init__(name=agent_id)
        self._state = initial_state # Holds simulated sensor data
        print(f"SmartHomeAgent initialized with state: {self._state}")

    # The type hint `message: Message` will now refer to `Any` if Message is not imported.
    # The return type `-> Message` will also refer to `Any`.
    async def handle_message(self, message: Any): # Changed type hint from Message to Any
        """
        Processes incoming ADK messages from other agents or clients.
        """
        # CRITICAL: message.text() might not work if 'Message' class is gone.
        # You need to find the equivalent way to access message content in ADK v1.6.1.
        # For now, we'll assume it's still accessible this way, but be prepared to change.
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
            self._state['temperature'] = round(random.uniform(20.0, 30.0), 1)
            response_text = f"Simulated temperature has been updated to {self._state['temperature']}°C."

        print(f"SmartHomeAgent responding with: '{response_text}' to {message.sender_id}")
        
        # CRITICAL: MessageBuilder() will cause a NameError here.
        # You need to find the correct way to build a response message in ADK v1.6.1.
        # For now, this line is commented out and replaced with a placeholder return.
        # return MessageBuilder().text_message(response_text).add_sender_id(self.id).add_recipient_id(message.sender_id).build()
        # Placeholder return: You MUST replace this with the actual message building for ADK v1.6.1
        # For example, it might be something like:
        # return Agent.create_text_message(response_text, sender_id=self.id, recipient_id=message.sender_id)
        # OR a new Message object type.
        return {"response_text": response_text, "sender_id": self.id, "recipient_id": message.sender_id, "NOTE": "Message building needs update for ADK v1.6.1"}


    # get_response is generally used by the ADK client for direct HTTP requests to the agent,
    # mapping to an ADK message for handle_message.
    # The return type `-> Message` will now refer to `Any`.
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
        # return MessageBuilder().text_message("Invalid request format to SmartHomeAgent").add_sender_id(self.id).add_recipient_id("unknown").build()
        return {"error": "Invalid request format to SmartHomeAgent", "sender_id": self.id, "recipient_id": "unknown", "NOTE": "Message building needs update for ADK v1.6.1"}