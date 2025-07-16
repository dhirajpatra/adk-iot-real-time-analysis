# adk_ollama_tool/agents/smart_home_agent.py
import random
import os
import asyncio
import paho.mqtt.client as paho_mqtt
from google.adk.agents.llm_agent import Agent
from typing import Any # Still good to keep 'Any' for flexibility if needed elsewhere
from google.genai.types import UserContent, ModelContent, Part # Corrected import for Part

class SmartHomeAgent(Agent):
    """
    A simple agent that simulates smart home data and responds to queries about its state,
    now integrated with MQTT for real-time sensor updates.
    """
    def __init__(self, agent_id: str, initial_state: dict):
        super().__init__(name=agent_id)
        self._state = initial_state
        print(f"SmartHomeAgent '{self.name}' initialized with state: {self._state}")

        # MQTT Client Setup
        self._mqtt_client = paho_mqtt.Client(client_id=f"{self.name}_client")
        self._mqtt_client.on_connect = self._on_connect
        self._mqtt_client.on_message = self._on_message

        # Get MQTT broker details from environment variables
        self._mqtt_broker_host = os.environ.get("MQTT_BROKER_HOST", "localhost")
        self._mqtt_broker_port = int(os.environ.get("MQTT_BROKER_PORT", 1883))

        # Start MQTT client in the background as a separate task
        asyncio.create_task(self._start_mqtt_client())

    async def _start_mqtt_client(self):
        """Connects to MQTT broker and starts the loop."""
        try:
            print(f"MQTT: Connecting to broker at {self._mqtt_broker_host}:{self._mqtt_broker_port}...")
            self._mqtt_client.connect(self._mqtt_broker_host, self._mqtt_broker_port, 60)
            self._mqtt_client.loop_start() # Runs the MQTT network loop in a separate thread
            print("MQTT: MQTT client started.")
        except Exception as e:
            print(f"MQTT Error: Could not connect to MQTT broker: {e}")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("MQTT: Connected successfully to broker.")
            # Subscribe to topics where Arduino will publish data
            client.subscribe("smarthome/arduino/temperature")
            client.subscribe("smarthome/arduino/humidity")
            print("MQTT: Subscribed to 'smarthome/arduino/temperature' and 'smarthome/arduino/humidity'.")
        else:
            print(f"MQTT: Failed to connect, return code {rc}\n")

    def _on_message(self, client, userdata, msg):
        """Callback for when a message is received from the broker."""
        topic = msg.topic
        payload = msg.payload.decode()
        # print(f"MQTT: Received message - Topic: '{topic}', Payload: '{payload}'") # Uncomment for verbose MQTT logging

        try:
            if topic == "smarthome/arduino/temperature":
                temp = float(payload)
                self._state["temperature"] = temp
                print(f"SmartHomeAgent: Updated temperature to {temp}°C via MQTT.")
            elif topic == "smarthome/arduino/humidity":
                humidity = float(payload)
                self._state["humidity"] = humidity
                print(f"SmartHomeAgent: Updated humidity to {humidity}% via MQTT.")
        except ValueError:
            print(f"MQTT Error: Could not parse payload '{payload}' for topic '{topic}'. Expected a number.")
        except Exception as e:
            print(f"MQTT Error: Problem processing MQTT message: {e}")

    # --- CRITICAL CHANGE HERE: Type hints for message and return ---
    async def handle_message(self, message: UserContent) -> ModelContent:
        """
        Processes incoming ADK messages (UserContent) from other agents or clients.
        """
        query = ""
        # Assuming the message object will have a 'parts' attribute
        for part in message.parts:
            if hasattr(part, 'text') and part.text:
                query = part.text.lower()
                break # Assuming the first text part is the query

        print(f"SmartHomeAgent '{self.name}' received query: '{query}' from {message.role}")

        response_text = "I'm sorry, I don't understand that specific query about the smart home."

        if "temperature" in query:
            if "temperature" in self._state:
                response_text = f"The current temperature is {self._state['temperature']} degrees Celsius."
            else:
                response_text = "I don't have current temperature data yet."
        elif "humidity" in query:
            if "humidity" in self._state:
                response_text = f"The current humidity is {self._state['humidity']}%."
            else:
                response_text = "I don't have current humidity data yet."
        elif "light status" in query or "lights on" in query or "lights off" in query:
            if "on" in query:
                self._state["light"] = "on"
            elif "off" in query:
                self._state["light"] = "off"
            response_text = f"The lights are currently {self._state['light']}."
        elif "status" in query or "home state" in query:
            response_text = (
                f"The current smart home status is: "
                f"Temperature {self._state.get('temperature', 'N/A')}°C, "
                f"Humidity {self._state.get('humidity', 'N/A')}%, "
                f"Lights are {self._state.get('light', 'N/A')}."
            )
        elif "update temperature" in query or "change temperature" in query:
            self._state['temperature'] = round(random.uniform(20.0, 30.0), 1)
            response_text = f"Simulated temperature has been updated to {self._state['temperature']}°C."
        else:
            response_text = "I can tell you the temperature, humidity, or light status."

        print(f"SmartHomeAgent responding with: '{response_text}'")

        # --- CRITICAL CHANGE HERE: Use ModelContent for response ---
        return ModelContent(
            parts=[Part(text=response_text)]
        )

    # --- CRITICAL CHANGE HERE: Return type hint for get_response ---
    async def get_response(self, request_data: dict) -> ModelContent:
        """
        Required ADK method to get a response for direct HTTP requests.
        Converts the request_data to a UserContent message and passes it to handle_message.
        """
        if isinstance(request_data, dict) and "query" in request_data:
            # --- CRITICAL CHANGE HERE: Use UserContent for incoming mock message ---
            mock_message = UserContent(
                parts=[Part(text=request_data["query"])]
            )
            
            return await self.handle_message(mock_message)
        
        # --- CRITICAL CHANGE HERE: Use ModelContent for error return ---
        return ModelContent(
            parts=[Part(text="Invalid request format to SmartHomeAgent. Expects a 'query' key in dict.")]
        )