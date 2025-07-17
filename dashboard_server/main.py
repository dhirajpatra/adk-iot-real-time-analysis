# dashboard_server/main.py
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import httpx # For making HTTP requests to other services
import asyncio # For async HTTP requests
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="ADK IoT Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify: ["http://localhost:3000"] etc.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Jinja2 templates directory
templates = Jinja2Templates(directory="templates")

# Mount static files directory (for CSS, JS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Get the URL of your ADK application from environment variables
# In Docker Compose, this will be the service name 'adk_app'
ADK_APP_URL = os.getenv("ADK_APP_URL", "http://adk_app:8000") # Default for Docker Compose internal network

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    """
    Renders the main dashboard page, fetching data from the ADK app.
    """
    dashboard_data = {
        "indoor_temp": "N/A",
        "indoor_humidity": "N/A",
        "outdoor_temp": "N/A",
        "outdoor_humidity": "N/A",
        "outdoor_conditions": "N/A",
        "llm_briefing": "Fetching latest insights...",
        "llm_activity_suggestion": "Fetching latest insights...",
        "llm_clothing_suggestion": "Fetching latest insights...",
        "error_message": None
    }
    print(f"Fetching data from ADK app at {ADK_APP_URL}")  # Debugging output
    try:
        async with httpx.AsyncClient() as client:
            # Call the ADK app's endpoint to get the combined data and recommendations
            response = await client.get(f"{ADK_APP_URL}/get_dashboard_data/", timeout=30.0) # Increased timeout
            response.raise_for_status() # Raise an exception for bad status codes
            data = response.json()
            print(f"Fetched dashboard data: {data}")  # Debugging output

            # Check if the response contains the expected keys
            if not isinstance(data, dict):
                raise ValueError("Unexpected data format received from ADK app.")
            
            # Populate dashboard_data with fetched information
            dashboard_data["indoor_temp"] = data.get("indoor_temp", "N/A")
            dashboard_data["indoor_humidity"] = data.get("indoor_humidity", "N/A")
            dashboard_data["outdoor_temp"] = data.get("outdoor_temp", "N/A")
            dashboard_data["outdoor_humidity"] = data.get("outdoor_humidity", "N/A")
            dashboard_data["outdoor_conditions"] = data.get("outdoor_conditions", "N/A")
            dashboard_data["llm_briefing"] = data.get("llm_briefing", "No briefing available.")
            dashboard_data["llm_activity_suggestion"] = data.get("llm_activity_suggestion", "No activity suggestion available.")
            dashboard_data["llm_clothing_suggestion"] = data.get("llm_clothing_suggestion", "No clothing suggestion available.")

    except httpx.HTTPStatusError as e:
        dashboard_data["error_message"] = f"Error fetching data from ADK app: HTTP {e.response.status_code} - {e.response.text}"
        print(f"HTTP error fetching dashboard data: {e}")
    except httpx.RequestError as e:
        dashboard_data["error_message"] = f"Network error connecting to ADK app: {e}"
        print(f"Network error fetching dashboard data: {e}")
    except Exception as e:
        dashboard_data["error_message"] = f"An unexpected error occurred: {e}"
        print(f"Unexpected error fetching dashboard data: {e}")

    # Pass the dashboard_data to the HTML template
    return templates.TemplateResponse("index.html", {"request": request, "data": dashboard_data})

# You can add other API endpoints here if needed for specific data fetches (e.g., /api/data)
# but for a simple dashboard, fetching all at once is fine.