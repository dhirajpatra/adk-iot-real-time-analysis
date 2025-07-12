from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import json
import logging
from typing import Dict, Optional
import os
from datetime import datetime
import redis
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Weather Data Agent", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "demo_key")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# Redis connection
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception as e:
    logger.error(f"Redis connection failed: {e}")
    redis_client = None

class WeatherRequest(BaseModel):
    city: str
    query: Optional[str] = None
    days: Optional[int] = 1

class WeatherResponse(BaseModel):
    success: bool
    city: str
    weather_data: Dict
    analysis: str
    timestamp: str

class WeatherAgent:
    def __init__(self):
        self.ollama_url = OLLAMA_URL
        self.api_key = WEATHER_API_KEY
        self.model_name = "gemma2:2b"
        
    async def fetch_weather_data(self, city: str, days: int = 1) -> Dict:
        """Fetch weather data from OpenWeatherMap API or simulate data"""
        try:
            # Check cache first
            cache_key = f"weather:{city}:{days}"
            if redis_client:
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            
            # Try to fetch real weather data
            if self.api_key != "demo_key":
                weather_data = await self._fetch_real_weather(city, days)
            else:
                weather_data = self._simulate_weather_data(city)
            
            # Cache the result
            if redis_client:
                redis_client.setex(cache_key, 300, json.dumps(weather_data))  # Cache for 5 minutes
            
            return weather_data
            
        except Exception as e:
            logger.error(f"Weather fetch failed: {e}")
            return self._simulate_weather_data(city)
    
    async def _fetch_real_weather(self, city: str, days: int) -> Dict:
        """Fetch real weather data from OpenWeatherMap"""
        base_url = "http://api.openweathermap.org/data/2.5"
        
        async with httpx.AsyncClient() as client:
            # Current weather
            current_response = await client.get(
                f"{base_url}/weather",
                params={
                    "q": city,
                    "appid": self.api_key,
                    "units": "metric"
                }
            )
            
            if current_response.status_code == 200:
                current_data = current_response.json()
                
                # Forecast data
                forecast_response = await client.get(
                    f"{base_url}/forecast",
                    params={
                        "q": city,
                        "appid": self.api_key,
                        "units": "metric",
                        "cnt": days * 8  # 8 forecasts per day (3-hour intervals)
                    }
                )
                
                forecast_data = forecast_response.json() if forecast_response.status_code == 200 else {}
                
                return {
                    "source": "openweathermap",
                    "current": current_data,
                    "forecast": forecast_data,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                raise Exception(f"Weather API error: {current_response.status_code}")
    
    def _simulate_weather_data(self, city: str) -> Dict:
        """Simulate weather data for demonstration"""
        import random
        
        # Weather conditions
        conditions = ["Clear", "Partly Cloudy", "Cloudy", "Rainy", "Thunderstorm"]
        
        return {
            "source": "simulated",
            "city": city,
            "current": {
                "temperature": round(random.uniform(20, 35), 1),
                "feels_like": round(random.uniform(22, 37), 1),
                "humidity": random.randint(40, 80),
                "pressure": random.randint(995, 1025),
                "visibility": round(random.uniform(5, 15), 1),
                "wind_speed": round(random.uniform(0, 20), 1),
                "wind_direction": random.choice(["N", "NE", "E", "SE", "S", "SW", "W", "NW"]),
                "condition": random.choice(conditions),
                "uv_index": random.randint(1, 10)
            },
            "forecast": {
                "today": {
                    "high": round(random.uniform(28, 38), 1),
                    "low": round(random.uniform(18, 25), 1),
                    "condition": random.choice(conditions),
                    "rain_chance": random.randint(0, 80)
                },
                "tomorrow": {
                    "high": round(random.uniform(28, 38), 1),
                    "low": round(random.uniform(18, 25), 1),
                    "condition": random.choice(conditions),
                    "rain_chance": random.randint(0, 80)
                }
            },
            "air_quality": {
                "aqi": random.randint(50, 150),
                "quality": random.choice(["Good", "Moderate", "Poor"]),
                "pm25": round(random.uniform(20, 80), 1),
                "pm10": round(random.uniform(30, 100), 1)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def analyze_with_ollama(self, weather_data: Dict, query: str, city: str) -> str:
        """Analyze weather data using Ollama Gemma model"""
        try:
            # Create cache key
            cache_key = f"weather_analysis:{hashlib.md5(f'{query}:{city}:{json.dumps(weather_data, sort_keys=True)}'.encode()).hexdigest()}"
            
            # Check cache first
            if redis_client:
                cached_result = redis_client.get(cache_key)
                if cached_result:
                    return cached_result
            
            prompt = f"""
            You are a meteorologist and weather analysis expert. Analyze the following weather data for {city} and answer the user's query.
            
            Weather Data:
            {json.dumps(weather_data, indent=2)}
            
            User Query: {query if query else f"Provide a comprehensive weather analysis for {city}"}
            
            Please provide analysis including:
            1. Current conditions summary
            2. Weather trends and patterns
            3. Recommendations for activities
            4. Health and safety considerations
            5. Forecast insights
            
            Keep your response informative and practical.
            """
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    analysis = result.get("response", "No analysis available")
                    
                    # Cache the result
                    if redis_client:
                        redis_client.setex(cache_key, 300, analysis)  # Cache for 5 minutes
                    
                    return analysis
                else:
                    logger.error(f"Ollama API error: {response.status_code}")
                    return "Error: Unable to analyze weather data with AI model"
                    
        except Exception as e:
            logger.error(f"Weather analysis error: {e}")
            return f"Error analyzing weather data: {str(e)}"

# Initialize Weather Agent
weather_agent = WeatherAgent()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "agent": "Weather Data Agent"}

@app.post("/analyze", response_model=WeatherResponse)
async def analyze_weather(request: WeatherRequest):
    """Analyze weather data for a specific city"""
    try:
        # Fetch weather data
        weather_data = await weather_agent.fetch_weather_data(request.city, request.days)
        
        # Analyze with Ollama
        analysis = await weather_agent.analyze_with_ollama(
            weather_data, 
            request.query or f"Weather analysis for {request.city}",
            request.city
        )
        
        return WeatherResponse(
            success=True,
            city=request.city,
            weather_data=weather_data,
            analysis=analysis,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Weather analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/weather/{city}")
async def get_weather(city: str):
    """Get raw weather data for a city"""
    try:
        data = await weather_agent.fetch_weather_data(city)
        return {"success": True, "city": city, "data": data}
    except Exception as e:
        logger.error(f"Weather fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def get_agent_status():
    """Get agent status and capabilities"""
    try:
        # Check Ollama connection
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
            ollama_status = response.status_code == 200
            
        return {
            "agent": "Weather Data Agent",
            "status": "running",
            "ollama_connected": ollama_status,
            "redis_connected": redis_client is not None,
            "model": weather_agent.model_name,
            "weather_api_configured": WEATHER_API_KEY != "demo_key",
            "capabilities": [
                "Weather data collection",
                "Forecast analysis",
                "Weather recommendations",
                "Air quality monitoring"
            ]
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "agent": "Weather Data Agent",
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)