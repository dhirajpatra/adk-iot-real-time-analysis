# adk_ollama_tool/app.py
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

# ADK imports
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool
from google.generativeai import types

# RUNNER AND SESSION SERVICE
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Import your agents
from agents.smart_home_agent import SmartHomeAgent
from agents.weather_agent import WeatherAgent

# Import your tools
from tools.ollama_tool import OllamaTool
from tools.mcp_tool import MCPTool
from tools.weather_api_tool import WeatherAPITool
from tools.time_tool import get_current_time

# Load environment variables
load_dotenv()

# --- Session Management Constants ---
APP_NAME = "adk_multi_agent_app"
USER_ID = "test_user"
SESSION_ID = "default_session"

# --- Initialize Tools ---
ollama_tool = OllamaTool(
    ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
)
mcp_tool = MCPTool(
    mcp_server_url=os.environ.get("MCP_SERVER_URL", "http://mcp_server:4000")
)
weather_api_tool = WeatherAPITool(
    api_key=os.environ.get("OPENWEATHER_API_KEY")
)

# --- Define Sub-Agents ---
smart_home_agent_instance = SmartHomeAgent(
    agent_id="smart_home_agent",
    initial_state={"temperature": 25.0, "light": "on"}
)
weather_agent_instance = WeatherAgent(
    agent_id="weather_agent",
    weather_tool=weather_api_tool
)

# --- Create the Main Orchestrator Agent ---
main_orchestrator_agent = Agent(
    name="main_adk_orchestrator",
    model=LiteLlm(model="ollama/gemma2:2b"),
    description="I am a multi-purpose assistant that can answer general questions, "
                "provide smart home information, fetch weather data, and tell the current time.",
    instruction="""You are a helpful and versatile assistant.
    If the user asks about smart home status or to control smart home devices, use the 'smart_home_agent'.
    If the user asks about current weather for an Indian city, use the 'weather_agent'.
    If the user asks about the current time in a specific city, use the 'get_current_time' tool.
    Otherwise, respond to general questions.
    """,
    tools=[
        AgentTool(smart_home_agent_instance),
        AgentTool(weather_agent_instance),
        get_current_time,
    ]
)

# --- Initialize ADK Runner ---
session_service = InMemorySessionService()
adk_runner = Runner(
    agent=main_orchestrator_agent,
    app_name=APP_NAME,
    session_service=session_service
)

# --- Initialize the Main FastAPI Application ---
# This is your primary FastAPI app instance.
app = FastAPI()

# --- Include ADK Runner's Routes ---
# This line is crucial for exposing ADK's internal endpoints (like /adk/v1/...).
# If this line causes an error (AttributeError: 'Runner' object has no attribute 'router'),
# then your ADK version's Runner API is different.
try:
    app.include_router(adk_runner.router, prefix="/adk/v1")
except AttributeError:
    print("Warning: adk_runner.router attribute not found. ADK Runner API might have changed.")
    print("Please provide the output of 'pip show google-adk' from your Docker container.")
    # If .router doesn't exist, the ADK Runner might be directly runnable by uvicorn
    # and custom routes need to be added to it via a different mechanism,
    # or you're expected to only use the routes it exposes by default.
    # For now, we'll proceed assuming the issue is with Runner's router exposure.


# --- Define Custom API Endpoints on the main 'app' instance ---
@app.get("/")
async def read_root():
    return {"message": "ADK Multi-Agent Application is running and ready for interaction!"}

@app.post("/ask_agent")
async def ask_agent(query: str):
    """
    Example endpoint to send a query to the main orchestrator agent.
    Uses the static USER_ID and SESSION_ID defined at the top.
    """
    user_id = USER_ID
    session_id = SESSION_ID

    content = types.Content(
        role="user",
        parts=[types.Part(text=query)]
    )

    try:
        events_async = adk_runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content
        )

        response_parts = []
        async for event in events_async:
            if event.output.message and event.output.message.text:
                response_parts.append(event.output.message.text)

        if response_parts:
            return {"query": query, "response": "\n".join(response_parts)}
        else:
            return {"query": query, "response": "No final response received from agent."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interacting with agent: {e}")

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