# adk_ollama_tool/app.py
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

# ADK imports
from google.adk.agents.llm_agent import Agent # LlmAgent is aliased to Agent
from google.adk.models.lite_llm import LiteLlm # For connecting to Ollama via LiteLLM
from google.adk.tools.agent_tool import AgentTool # To use other agents as tools
from google.generativeai import types # For creating message content

# Import your agents from the new 'agents' directory
from agents.smart_home_agent import SmartHomeAgent
from agents.weather_agent import WeatherAgent

# Import your tools from the new 'tools' directory
from tools.ollama_tool import OllamaTool # Still keep this for direct access if needed
from tools.mcp_tool import MCPTool
from tools.weather_api_tool import WeatherAPITool # This tool is used by WeatherAgent

# Load environment variables from .env file (if it exists).
load_dotenv()

app = FastAPI()

# --- Initialize Tools (used by sub-agents or directly) ---
ollama_tool = OllamaTool(
    ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
)
mcp_tool = MCPTool(
    mcp_server_url=os.environ.get("MCP_SERVER_URL", "http://mcp_server:4000")
)
weather_api_tool = WeatherAPITool(
    api_key=os.environ.get("OPENWEATHER_API_KEY")
)

# --- Define Sub-Agents (which will act as tools for the main orchestrator) ---
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
    model=LiteLlm(model="ollama/gemma2:2b"), # Use ollama/ prefix for LiteLlm
    description="I am a multi-purpose assistant that can answer general questions, "
                "provide smart home information, and fetch weather data.",
    instruction="""You are a helpful and versatile assistant.
    If the user asks about smart home status or to control smart home devices, use the 'smart_home_agent'.
    If the user asks about current weather for an Indian city, use the 'weather_agent'.
    Otherwise, respond to general questions.
    """,
    tools=[
        AgentTool(smart_home_agent_instance),
        AgentTool(weather_agent_instance),
    ]
)

# --- Mount ADK Client's Endpoints ---
app.include_router(main_orchestrator_agent.router, prefix="/adk/v1")


# --- Basic Health Check Endpoint ---
@app.get("/")
async def read_root():
    return {"message": "ADK Multi-Agent Application is running and ready for interaction!"}


# --- Example Endpoint for Direct Interaction ---
@app.post("/ask_agent")
async def ask_agent(query: str):
    """
    Example endpoint to send a query to the main orchestrator agent,
    which will then route to sub-agents if needed.
    """
    user_id = "test_user" # A unique identifier for the user
    session_id = "default_session" # A session ID for continuous conversation

    content = types.Content(
        role="user",
        parts=[types.Part(text=query)]
    )

    try:
        events_async = main_orchestrator_agent.run_async(
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