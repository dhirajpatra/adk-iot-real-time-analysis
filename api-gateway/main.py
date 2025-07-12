from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import asyncio
import json
import logging
from typing import Dict, Optional
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ADK Agent Gateway", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
IOT_AGENT_URL = os.getenv("IOT_AGENT_URL", "http://iot-agent:8000")
WEATHER_AGENT_URL = os.getenv("WEATHER_AGENT_URL", "http://weather-agent:8000")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

class MultiAgentRequest(BaseModel):
    query: str
    city: str
    include_iot: bool = True
    include_weather: bool = True

class MultiAgentResponse(BaseModel):
    success: bool
    query: str
    city: str
    iot_data: Optional[Dict] = None
    weather_data: Optional[Dict] = None
    combined_analysis: str
    timestamp: str

class AgentGateway:
    def __init__(self):
        self.iot_agent_url = IOT_AGENT_URL
        self.weather_agent_url = WEATHER_AGENT_URL
        self.ollama_url = OLLAMA_URL
        
    async def query_iot_agent(self, query: str, city: str) -> Dict:
        """Query the IoT data agent"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.iot_agent_url}/analyze",
                    json={"query": query, "city": city},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"IoT Agent error: {response.status_code}")
                    return {"success": False, "error": f"IoT Agent error: {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"IoT Agent query failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def query_weather_agent(self, query: str, city: str) -> Dict:
        """Query the weather data agent"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.weather_agent_url}/analyze",
                    json={"query": query, "city": city},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Weather Agent error: {response.status_code}")
                    return {"success": False, "error": f"Weather Agent error: {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Weather Agent query failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def combine_analysis(self, iot_data: Dict, weather_data: Dict, query: str, city: str) -> str:
        """Combine IoT and weather analysis using Ollama"""
        try:
            # Prepare combined data for analysis
            combined_data = {
                "iot_data": iot_data,
                "weather_data": weather_data,
                "city": city,
                "query": query
            }
            
            prompt = f"""
            You are an expert data analyst specializing in IoT and weather data correlation. 
            Analyze the following combined data for {city} and provide comprehensive insights.
            
            User Query: {query}
            
            IoT Data Analysis:
            {iot_data.get('analysis', 'No IoT analysis available')}
            
            Weather Data Analysis:
            {weather_data.get('analysis', 'No weather analysis available')}
            
            IoT Raw Data:
            {json.dumps(iot_data.get('data', {}), indent=2)}
            
            Weather Raw Data:
            {json.dumps(weather_data.get('weather_data', {}), indent=2)}
            
            Please provide:
            1. Correlation between IoT sensor data and weather conditions
            2. Environmental impact analysis
            3. Recommendations based on both data sources
            4. Potential patterns or anomalies
            5. Actionable insights for {city}
            
            Keep the response comprehensive but concise.
            """
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": "gemma2:2b",
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=45.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "No combined analysis available")
                else:
                    logger.error(f"Ollama API error: {response.status_code}")
                    return "Error: Unable to generate combined analysis"
                    
        except Exception as e:
            logger.error(f"Combined analysis error: {e}")
            return f"Error generating combined analysis: {str(e)}"
    
    async def get_agent_status(self, agent_url: str) -> Dict:
        """Get status of a specific agent"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{agent_url}/status", timeout=5.0)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

# Initialize Gateway
gateway = AgentGateway()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ADK Agent Gateway"}

@app.post("/query", response_model=MultiAgentResponse)
async def multi_agent_query(request: MultiAgentRequest):
    """Query both agents and provide combined analysis"""
    try:
        tasks = []
        
        # Query IoT agent if requested
        if request.include_iot:
            tasks.append(gateway.query_iot_agent(request.query, request.city))
        
        # Query Weather agent if requested
        if request.include_weather:
            tasks.append(gateway.query_weather_agent(request.query, request.city))
        
        # Execute queries concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        iot_data = None
        weather_data = None
        
        if request.include_iot:
            iot_result = results[0] if len(results) > 0 else None
            if isinstance(iot_result, dict) and iot_result.get("success"):
                iot_data = iot_result
        
        if request.include_weather:
            weather_result = results[-1] if len(results) > 0 else None
            if isinstance(weather_result, dict) and weather_result.get("success"):
                weather_data = weather_result
        
        # Generate combined analysis
        combined_analysis = "No analysis available"
        if iot_data or weather_data:
            combined_analysis = await gateway.combine_analysis(
                iot_data or {}, 
                weather_data or {}, 
                request.query, 
                request.city
            )
        
        return MultiAgentResponse(
            success=True,
            query=request.query,
            city=request.city,
            iot_data=iot_data,
            weather_data=weather_data,
            combined_analysis=combined_analysis,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Multi-agent query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def get_system_status():
    """Get status of all agents and services"""
    try:
        # Get status of all agents concurrently
        iot_status_task = gateway.get_agent_status(IOT_AGENT_URL)
        weather_status_task = gateway.get_agent_status(WEATHER_AGENT_URL)
        
        # Check Ollama status
        ollama_status_task = gateway.get_agent_status(OLLAMA_URL.replace('/api', ''))
        
        iot_status, weather_status, ollama_status = await asyncio.gather(
            iot_status_task, 
            weather_status_task, 
            ollama_status_task,
            return_exceptions=True
        )
        
        return {
            "gateway": {
                "status": "running",
                "timestamp": datetime.now().isoformat()
            },
            "agents": {
                "iot_agent": iot_status if isinstance(iot_status, dict) else {"status": "error", "error": str(iot_status)},
                "weather_agent": weather_status if isinstance(weather_status, dict) else {"status": "error", "error": str(weather_status)},
                "ollama": ollama_status if isinstance(ollama_status, dict) else {"status": "error", "error": str(ollama_status)}
            },
            "services": {
                "iot_agent_url": IOT_AGENT_URL,
                "weather_agent_url": WEATHER_AGENT_URL,
                "ollama_url": OLLAMA_URL
            }
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/iot/data")
async def get_iot_data():
    """Get raw IoT data"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{IOT_AGENT_URL}/data", timeout=10.0)
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail="IoT Agent unavailable")
    except Exception as e:
        logger.error(f"IoT data fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/weather/{city}")
async def get_weather_data(city: str):
    """Get raw weather data for a city"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{WEATHER_AGENT_URL}/weather/{city}", timeout=10.0)
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail="Weather Agent unavailable")
    except Exception as e:
        logger.error(f"Weather data fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/iot/analyze")
async def analyze_iot_data(request: dict):
    """Direct IoT analysis endpoint"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{IOT_AGENT_URL}/analyze",
                json=request,
                timeout=30.0
            )
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail="IoT Agent analysis failed")
    except Exception as e:
        logger.error(f"IoT analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/weather/analyze")
async def analyze_weather_data(request: dict):
    """Direct weather analysis endpoint"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{WEATHER_AGENT_URL}/analyze",
                json=request,
                timeout=30.0
            )
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail="Weather Agent analysis failed")
    except Exception as e:
        logger.error(f"Weather analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)