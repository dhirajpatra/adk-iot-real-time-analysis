# adk_ollama_tool/app.py 
import os
import json
import asyncio
import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Import your agents and tools
from agents.smart_home_agent import SmartHomeAgent
from agents.weather_agent import WeatherAgent # Make sure this WeatherAgent is updated from previous step!
from tools.ollama_tool import OllamaTool

# Load environment variables
load_dotenv()

app = FastAPI(title="ADK Ollama Application")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify: ["http://localhost:3000"] etc.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Configuration for MQTT, MCP, Ollama, OpenWeatherMap ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# --- Initialize Agents and Tools ---
smart_home_agent = SmartHomeAgent(agent_id="HomeSensorAgent", initial_state={"temperature": "N/A", "humidity": "N/A", "light": "off"})

ollama_tool = None
weather_agent = None

try:
    ollama_tool = OllamaTool(base_url=OLLAMA_BASE_URL, model="gemma3:1b")
except Exception as e:
    print(f"OllamaTool init failed: {e}")

try:
    weather_agent = WeatherAgent(agent_id="WeatherGuru", mcp_server_url=MCP_SERVER_URL, api_key=OPENWEATHER_API_KEY)
except Exception as e:
    print(f"WeatherAgent init failed: {e}")


# --- FastAPI Application Lifecycle Events ---
@app.on_event("startup")
async def startup_event():
    print("Starting up ADK App...")
    print("ADK App startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down ADK App...")
    print("ADK App shutdown complete.")

# --- API Endpoints ---

class ChatRequest(BaseModel):
    message: str
    city: str = "Bengaluru"

@app.post("/chat/")
async def chat_with_adk(request: ChatRequest):
    try:
        response_content = await smart_home_agent.handle_message(request.message)
        if response_content and response_content.parts and response_content.parts[0].text:
            return {"response": response_content.parts[0].text}

        response_content = await weather_agent.handle_message(request.message, request.city)
        if response_content and response_content.parts and response_content.parts[0].text:
            return {"response": response_content.parts[0].text}

        llm_response = await ollama_tool.query(request.message)
        return {"response": llm_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_indoor_status/")
async def get_indoor_status():
    return smart_home_agent._state

@app.get("/get_outdoor_status/")
async def get_outdoor_status(city: str = "London"):
    try:
        current_weather = await weather_agent.get_current_weather(city)
        return current_weather
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get outdoor weather: {e}")

@app.get("/get_dashboard_data/")
async def get_dashboard_data(city: str = "London"):
    try:
        indoor_data = smart_home_agent._state
        outdoor_data = await weather_agent.get_current_weather(city)

        indoor_temp = indoor_data.get("temperature", "N/A")
        indoor_humidity = indoor_data.get("humidity", "N/A")
        outdoor_temp = outdoor_data.get("temperature", "N/A")
        outdoor_humidity = outdoor_data.get("humidity", "N/A")
        outdoor_conditions = outdoor_data.get("description", "N/A")

        briefing_prompt = (
            f"The current indoor temperature is {indoor_temp}°C and humidity is {indoor_humidity}%. "
            f"Outside, it's {outdoor_temp}°C with {outdoor_conditions} and {outdoor_humidity}% humidity. "
            "Provide a concise, friendly weather briefing and a recommendation for indoor comfort, "
            "considering opening windows or using a fan/AC. Keep it under 50 words."
        )
        llm_briefing = await ollama_tool.query(briefing_prompt)

        activity_prompt = (
            f"Given the current outdoor weather is {outdoor_temp}°C and {outdoor_conditions}, "
            "suggest 2-3 suitable activities, including both indoor and outdoor options. Keep it concise."
        )
        llm_activity_suggestion = await ollama_tool.query(activity_prompt)

        clothing_prompt = (
            f"The current outdoor temperature is {outdoor_temp}°C with {outdoor_conditions}. "
            "What kind of clothing would you recommend for going outside today? Keep it brief."
        )
        llm_clothing_suggestion = await ollama_tool.query(clothing_prompt)

        return {
            "indoor_temp": indoor_temp,
            "indoor_humidity": indoor_humidity,
            "outdoor_temp": outdoor_temp,
            "outdoor_humidity": outdoor_humidity,
            "outdoor_conditions": outdoor_conditions,
            "llm_briefing": llm_briefing,
            "llm_activity_suggestion": llm_activity_suggestion,
            "llm_clothing_suggestion": llm_clothing_suggestion,
        }
    except Exception as e:
        print(f"Error in get_dashboard_data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate dashboard data: {e}")

@app.get("/health/")
async def health_check():
    return {"status": "ok"}