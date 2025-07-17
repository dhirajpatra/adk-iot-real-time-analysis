# mcp_server/server.py

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import asyncio
import json
import time
import os
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

# Adjusted import path: It's now inside the 'tools' package within mcp_server
from tools.weather_api_tool import WeatherAPITool

app = FastAPI(title="MCP Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify: ["http://localhost:3000"] etc.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
if not OPENWEATHER_API_KEY:
    raise ValueError("FATAL ERROR: OPENWEATHER_API_KEY environment variable is not set for MCP Server.")

weather_tool = WeatherAPITool(api_key=OPENWEATHER_API_KEY)

@app.get("/")
async def read_root():
    """Basic health check endpoint for the MCP server."""
    return {"message": "MCP Server (FastAPI) is running!"}

@app.get("/weather_current")
async def get_current_weather_endpoint(city: str):
    """
    Fetches current weather data for a given city using OpenWeatherMap 2.5 API (via Geocoding).
    """
    print(f"MCP Server: Received request for current weather for city='{city}'")
    current_weather_data_raw = await weather_tool.get_current_weather_2_5(city)

    if not current_weather_data_raw:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve current weather for {city}. Check MCP server logs for details from 2.5 API call.")

    # Parse the 2.5 API response structure as per your Postman output
    coord = current_weather_data_raw.get("coord", {})
    weather_list = current_weather_data_raw.get("weather", [{}])
    main_data = current_weather_data_raw.get("main", {})
    wind_data = current_weather_data_raw.get("wind", {})
    sys_data = current_weather_data_raw.get("sys", {})

    temp = main_data.get("temp")
    humidity = main_data.get("humidity")
    pressure = main_data.get("pressure")
    wind_speed = wind_data.get("speed")
    
    weather_info = weather_list[0].get("description", "N/A") if weather_list else "N/A"
    
    response_payload = {
        "city": city,
        "lat": coord.get("lat"),
        "lon": coord.get("lon"),
        "dt": current_weather_data_raw.get("dt"), # Unix timestamp of the data
        "temperature": temp,
        "humidity": humidity,
        "description": weather_info,
        "pressure": pressure,
        "wind_speed": wind_speed,
        "country": sys_data.get("country")
    }
    print(f"MCP Server: Successfully prepared current weather data for {city}.")
    return JSONResponse(content=response_payload, status_code=200)

@app.get("/weather_historical")
async def get_historical_weather_endpoint(city: str, dt: int):
    """
    Fetches historical weather data for a given city at a specific Unix timestamp
    using the OpenWeatherMap 3.0 One Call API (Timemachine).
    """
    print(f"MCP Server: Received request for historical weather for city='{city}' at dt='{dt}'")
    historical_weather_data_raw = await weather_tool.get_historical_weather_one_call_3_0(city, dt)

    if not historical_weather_data_raw or "data" not in historical_weather_data_raw or len(historical_weather_data_raw["data"]) == 0:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve historical weather for {city} at {dt}. No data found or API error. Check MCP server logs for details.")
    
    hourly_data = historical_weather_data_raw["data"][0] 
    
    temp = hourly_data.get("temp")
    humidity = hourly_data.get("humidity")
    pressure = hourly_data.get("pressure")
    wind_speed = hourly_data.get("wind_speed")
    
    weather_info = "N/A"
    if "weather" in hourly_data and len(hourly_data["weather"]) > 0:
        weather_info = hourly_data["weather"][0].get("description", "N/A")
    
    response_payload = {
        "city": city,
        "requested_dt": dt,
        "actual_data_dt": hourly_data.get("dt"), # The actual timestamp of the data point
        "temperature": temp,
        "humidity": humidity,
        "description": weather_info,
        "pressure": pressure,
        "wind_speed": wind_speed,
    }
    print(f"MCP Server: Successfully prepared historical weather data for {city}.")
    return JSONResponse(content=response_payload, status_code=200)

@app.get("/health")
async def health_check():
    """Endpoint for Docker healthchecks."""
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4000)