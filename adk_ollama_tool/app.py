# adk_ollama_tool/app.py
import os
import uvicorn
from fastapi import FastAPI, HTTPException # HTTPException is still useful for error responses
from dotenv import load_dotenv

# ADK imports
from adk.agent_client import AgentClient
from adk.message import MessageBuilder, Message # Import Message for type hinting

# Import your agents from the new 'agents' directory
from agents.smart_home_agent import SmartHomeAgent
from agents.weather_agent import WeatherAgent

# Import your tools from the new 'tools' directory
from tools.ollama_tool import OllamaTool
from tools.mcp_tool import MCPTool
from tools.weather_api_tool import WeatherAPITool

# Load environment variables from .env file (if it exists).
# This is crucial for your API keys and service URLs.
load_dotenv()

app = FastAPI()
agent_client = AgentClient()

# --- Initialize Tools ---
# These tools encapsulate the logic for interacting with external services.
# They are passed to agents or can be used directly by the application.
ollama_tool = OllamaTool(
    ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
)
mcp_tool = MCPTool(
    mcp_server_url=os.environ.get("MCP_SERVER_URL", "http://mcp_server:4000")
)
weather_api_tool = WeatherAPITool(
    api_key=os.environ.get("OPENWEATHER_API_KEY") # Ensure this ENV VAR is set in docker-compose or .env
)

# --- Register Agents ---
# Each agent needs a unique ID. You pass the necessary tools or initial state to them.
agent_client.register_agent(SmartHomeAgent(agent_id="smart_home_agent", initial_state={"temperature": 25.0, "light": "on"}))
agent_client.register_agent(WeatherAgent(agent_id="weather_agent", weather_tool=weather_api_tool))


# --- Mount ADK Client's Endpoints ---
# This makes the ADK client's internal endpoints accessible at /adk/v1.
# This is how external systems (or other agents in a more complex setup) can communicate.
app.include_router(agent_client.router, prefix="/adk/v1")


# --- Basic Health Check Endpoint ---
@app.get("/")
async def read_root():
    return {"message": "ADK Multi-Agent Application is running and ready for interaction!"}


# --- Example Endpoints for Direct Interaction (for easy testing via browser/curl) ---
# These endpoints allow you to directly send messages to specific agents
# without needing to understand the full ADK message format.

@app.get("/ask_smart_home")
async def ask_smart_home(query: str = "What's the temperature?"):
    """
    Example endpoint to send a query to the Smart Home Agent.
    """
    # Build an ADK message to send to the smart_home_agent
    message = MessageBuilder().text_message(query).add_sender_id("user_client").add_recipient_id("smart_home_agent").build()
    
    # Send the message and get the response from the agent
    response_message: Message = await agent_client.send_message(message)
    
    return {"query_sent": query, "smart_home_agent_response": response_message.text()}

@app.get("/get_weather")
async def get_weather_data(city: str = "Mumbai"):
    """
    Example endpoint to send a query to the Weather Agent.
    """
    # Build an ADK message to send to the weather_agent
    message = MessageBuilder().text_message(f"What's the weather in {city}?").add_sender_id("user_client").add_recipient_id("weather_agent").build()
    
    # Send the message and get the response from the agent
    response_message: Message = await agent_client.send_message(message)
    
    return {"city_queried": city, "weather_agent_response": response_message.text()}

# You can also add endpoints to directly call your tools for testing purposes,
# though typically agents would use these tools internally.
@app.post("/direct_call_ollama")
async def direct_call_ollama(prompt: str):
    """Directly calls the OllamaTool, bypassing agent routing."""
    response = await ollama_tool.chat_with_ollama(prompt)
    return {"prompt": prompt, "ollama_tool_response": response}

@app.post("/direct_call_mcp")
async def direct_call_mcp(num1: int, num2: int):
    """Directly calls the MCPTool, bypassing agent routing."""
    response = await mcp_tool.calculate(num1, num2)
    return {"numbers": [num1, num2], "mcp_tool_response": response}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)