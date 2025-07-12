from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import asyncio
import json
import logging
from typing import Dict, List, Optional
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import redis
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="IoT Data Agent", version="1.0.0")

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
IOT_BLOG_URL = os.getenv("IOT_BLOG_URL", "https://dhirajpatra.blogspot.com/2023/08/iot-real-time-data-analysis.html")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# Redis connection
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception as e:
    logger.error(f"Redis connection failed: {e}")
    redis_client = None

class IoTDataRequest(BaseModel):
    query: str
    city: Optional[str] = None
    data_type: Optional[str] = None

class IoTDataResponse(BaseModel):
    success: bool
    data: Dict
    analysis: str
    timestamp: str

class IoTAgent:
    def __init__(self):
        self.ollama_url = OLLAMA_URL
        self.blog_url = IOT_BLOG_URL
        self.model_name = "gemma3:9b"
        
    async def fetch_iot_data(self) -> Dict:
        """Fetch IoT data from the blog or simulate real-time data"""
        try:
            # Try to fetch from blog first
            response = requests.get(self.blog_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                content = soup.get_text()
                
                # Extract relevant IoT data patterns
                iot_data = {
                    "source": "blog",
                    "content": content[:2000],  # First 2000 chars
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # Simulate IoT data if blog is not accessible
                iot_data = self._simulate_iot_data()
                
        except Exception as e:
            logger.error(f"Failed to fetch IoT data: {e}")
            iot_data = self._simulate_iot_data()
            
        return iot_data
    
    def _simulate_iot_data(self) -> Dict:
        """Simulate IoT sensor data for demonstration"""
        import random
        
        return {
            "source": "simulated",
            "sensors": {
                "temperature": round(random.uniform(20, 35), 2),
                "humidity": round(random.uniform(40, 80), 2),
                "pressure": round(random.uniform(995, 1025), 2),
                "air_quality": random.choice(["Good", "Moderate", "Poor"]),
                "noise_level": round(random.uniform(30, 80), 2),
                "light_intensity": round(random.uniform(100, 1000), 2)
            },
            "location": {
                "city": "Bengaluru",
                "latitude": 12.9716,
                "longitude": 77.5946
            },
            "timestamp": datetime.now().isoformat(),
            "device_id": f"sensor_{random.randint(1000, 9999)}",
            "battery_level": round(random.uniform(20, 100), 2)
        }
    
    async def analyze_with_ollama(self, data: Dict, query: str) -> str:
        """Analyze IoT data using Ollama Gemma model"""
        try:
            # Create cache key
            cache_key = f"iot_analysis:{hashlib.md5(f'{query}:{json.dumps(data, sort_keys=True)}'.encode()).hexdigest()}"
            
            # Check cache first
            if redis_client:
                cached_result = redis_client.get(cache_key)
                if cached_result:
                    return cached_result
            
            prompt = f"""
            You are an IoT data analysis expert. Analyze the following IoT data and answer the user's query.
            
            IoT Data:
            {json.dumps(data, indent=2)}
            
            User Query: {query}
            
            Please provide a comprehensive analysis including:
            1. Data interpretation
            2. Trends and patterns
            3. Recommendations
            4. Potential issues or anomalies
            
            Keep your response informative but concise.
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
                    return "Error: Unable to analyze data with AI model"
                    
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return f"Error analyzing data: {str(e)}"

# Initialize IoT Agent
iot_agent = IoTAgent()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "agent": "IoT Data Agent"}

@app.post("/analyze", response_model=IoTDataResponse)
async def analyze_iot_data(request: IoTDataRequest):
    """Analyze IoT data based on user query"""
    try:
        # Fetch IoT data
        iot_data = await iot_agent.fetch_iot_data()
        
        # Analyze with Ollama
        analysis = await iot_agent.analyze_with_ollama(iot_data, request.query)
        
        return IoTDataResponse(
            success=True,
            data=iot_data,
            analysis=analysis,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/data")
async def get_iot_data():
    """Get raw IoT data"""
    try:
        data = await iot_agent.fetch_iot_data()
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Data fetch failed: {e}")
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
            "agent": "IoT Data Agent",
            "status": "running",
            "ollama_connected": ollama_status,
            "redis_connected": redis_client is not None,
            "model": iot_agent.model_name,
            "capabilities": [
                "IoT data collection",
                "Real-time analysis",
                "Pattern recognition",
                "Anomaly detection"
            ]
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "agent": "IoT Data Agent",
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)