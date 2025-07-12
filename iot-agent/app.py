#!/usr/bin/env python3
"""
IoT Agent Application
Based on Dhiraj Patra's tutorial: Real-Time Data With IoT & MQTT
Tutorial: https://dhirajpatra.medium.com/real-time-data-with-iot-mqtt-b7186022e47

This POC simulates Arduino+ESP8266 with DHT11 sensor data collection
and provides REST API endpoints for the multi-agent system.
"""

import os
import json
import time
import random
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

import requests
import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.emqx.io")  # Free MQTT broker as per tutorial
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "iot_agent_poc")

# MQTT Topics (as per tutorial)
TEMP_TOPIC = "sensor/temperature"
HUMIDITY_TOPIC = "sensor/humidity"

# Initialize FastAPI app
app = FastAPI(
    title="IoT Agent - Smart House",
    description="Arduino DHT11 Temperature & Humidity Sensor Agent",
    version="1.0.0"
)

# Data models
class SensorReading(BaseModel):
    """DHT11 sensor reading model"""
    temperature: float = Field(..., description="Temperature in Celsius")
    humidity: float = Field(..., description="Humidity percentage")
    timestamp: datetime = Field(default_factory=datetime.now)
    sensor_id: str = Field(default="DHT11_001", description="Sensor identifier")

class SensorData(BaseModel):
    """Aggregated sensor data"""
    current_reading: Optional[SensorReading] = None
    readings_history: List[SensorReading] = []
    sensor_status: str = "online"
    last_update: Optional[datetime] = None

class OllamaAnalysisRequest(BaseModel):
    """Request for Ollama analysis"""
    sensor_data: List[SensorReading]
    analysis_type: str = Field(default="comfort_analysis", description="Type of analysis to perform")

# Global data storage (POC level - in production use Redis/PostgreSQL)
sensor_data_store = SensorData()
mqtt_client = None

# DHT11 Sensor Simulation (based on tutorial specs)
@dataclass
class DHT11Simulator:
    """Simulates DHT11 sensor readings like Arduino+ESP8266"""
    
    def __init__(self):
        self.base_temp = 24.0  # Base temperature in Celsius
        self.base_humidity = 60.0  # Base humidity percentage
        self.temp_variance = 5.0  # Temperature variation range
        self.humidity_variance = 15.0  # Humidity variation range
    
    def read_sensor(self) -> SensorReading:
        """Simulate DHT11 sensor reading"""
        # Add realistic sensor variations
        temp = self.base_temp + random.uniform(-self.temp_variance, self.temp_variance)
        humidity = self.base_humidity + random.uniform(-self.humidity_variance, self.humidity_variance)
        
        # Ensure realistic ranges
        temp = max(0, min(50, temp))  # DHT11 range: 0-50°C
        humidity = max(20, min(95, humidity))  # DHT11 range: 20-95% RH
        
        return SensorReading(
            temperature=round(temp, 1),
            humidity=round(humidity, 1),
            timestamp=datetime.now(),
            sensor_id="DHT11_001"
        )

# Initialize DHT11 simulator
dht11_sim = DHT11Simulator()

# MQTT Functions (based on tutorial)
def on_connect(client, userdata, flags, rc):
    """MQTT connection callback"""
    if rc == 0:
        logger.info(f"Connected to MQTT broker: {MQTT_BROKER}")
        # Subscribe to topics if needed
        client.subscribe(f"{TEMP_TOPIC}/command")
        client.subscribe(f"{HUMIDITY_TOPIC}/command")
    else:
        logger.error(f"Failed to connect to MQTT broker: {rc}")

def on_message(client, userdata, msg):
    """MQTT message callback"""
    try:
        topic = msg.topic
        payload = msg.payload.decode()
        logger.info(f"Received MQTT message - Topic: {topic}, Payload: {payload}")
    except Exception as e:
        logger.error(f"Error processing MQTT message: {e}")

def publish_sensor_data(reading: SensorReading):
    """Publish sensor data to MQTT (as per tutorial)"""
    global mqtt_client
    
    try:
        if mqtt_client and mqtt_client.is_connected():
            # Publish temperature
            temp_payload = json.dumps({
                "value": reading.temperature,
                "timestamp": reading.timestamp.isoformat(),
                "sensor_id": reading.sensor_id
            })
            mqtt_client.publish(TEMP_TOPIC, temp_payload)
            
            # Publish humidity
            humidity_payload = json.dumps({
                "value": reading.humidity,
                "timestamp": reading.timestamp.isoformat(),
                "sensor_id": reading.sensor_id
            })
            mqtt_client.publish(HUMIDITY_TOPIC, humidity_payload)
            
            logger.info(f"Published sensor data - Temp: {reading.temperature}°C, Humidity: {reading.humidity}%")
    except Exception as e:
        logger.error(f"Error publishing MQTT data: {e}")

def initialize_mqtt():
    """Initialize MQTT client"""
    global mqtt_client
    
    try:
        mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        
        # Connect to broker
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        
        logger.info("MQTT client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize MQTT client: {e}")
        mqtt_client = None

# Ollama Integration
def analyze_sensor_data_with_ollama(readings: List[SensorReading]) -> Dict:
    """Send sensor data to Ollama for AI analysis"""
    try:
        # Prepare data for analysis
        sensor_summary = {
            "total_readings": len(readings),
            "latest_temp": readings[-1].temperature if readings else 0,
            "latest_humidity": readings[-1].humidity if readings else 0,
            "avg_temp": sum(r.temperature for r in readings) / len(readings) if readings else 0,
            "avg_humidity": sum(r.humidity for r in readings) / len(readings) if readings else 0,
            "time_range": {
                "start": readings[0].timestamp.isoformat() if readings else None,
                "end": readings[-1].timestamp.isoformat() if readings else None
            }
        }
        
        # Create prompt for Ollama
        prompt = f"""
        Analyze this IoT sensor data from Arduino DHT11 temperature and humidity sensor:
        
        Sensor Data Summary:
        - Total readings: {sensor_summary['total_readings']}
        - Latest temperature: {sensor_summary['latest_temp']}°C
        - Latest humidity: {sensor_summary['latest_humidity']}%
        - Average temperature: {sensor_summary['avg_temp']:.1f}°C
        - Average humidity: {sensor_summary['avg_humidity']:.1f}%
        
        Please provide:
        1. Comfort level assessment (comfortable, too hot, too cold, too humid, too dry)
        2. Recommendations for smart house climate control
        3. Any anomalies or patterns detected
        4. Energy efficiency suggestions
        
        Respond in JSON format.
        """
        
        # Send to Ollama
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": "gemma:2b",
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            ollama_response = response.json()
            return {
                "analysis": ollama_response.get("response", "No analysis available"),
                "sensor_summary": sensor_summary,
                "timestamp": datetime.now().isoformat()
            }
        else:
            logger.error(f"Ollama API error: {response.status_code}")
            return {"error": "Failed to get analysis from Ollama"}
            
    except Exception as e:
        logger.error(f"Error analyzing data with Ollama: {e}")
        return {"error": str(e)}

# Background task for continuous sensor simulation
async def simulate_sensor_readings():
    """Background task to simulate Arduino sensor readings"""
    while True:
        try:
            # Simulate DHT11 reading
            reading = dht11_sim.read_sensor()
            
            # Store reading
            sensor_data_store.current_reading = reading
            sensor_data_store.readings_history.append(reading)
            sensor_data_store.last_update = datetime.now()
            sensor_data_store.sensor_status = "online"
            
            # Keep only last 100 readings (POC limitation)
            if len(sensor_data_store.readings_history) > 100:
                sensor_data_store.readings_history = sensor_data_store.readings_history[-100:]
            
            # Publish to MQTT
            publish_sensor_data(reading)
            
            # Wait 30 seconds (as per tutorial setup)
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error in sensor simulation: {e}")
            sensor_data_store.sensor_status = "error"
            await asyncio.sleep(60)

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "IoT Agent",
        "timestamp": datetime.now().isoformat(),
        "mqtt_connected": mqtt_client.is_connected() if mqtt_client else False,
        "sensor_status": sensor_data_store.sensor_status
    }

@app.get("/current-data")
async def get_current_sensor_data():
    """Get latest sensor reading"""
    if sensor_data_store.current_reading:
        return {
            "status": "success",
            "data": sensor_data_store.current_reading,
            "sensor_status": sensor_data_store.sensor_status
        }
    else:
        raise HTTPException(status_code=404, detail="No sensor data available")

@app.get("/history")
async def get_sensor_history(limit: int = 50):
    """Get historical sensor readings"""
    history = sensor_data_store.readings_history[-limit:] if sensor_data_store.readings_history else []
    return {
        "status": "success",
        "total_readings": len(sensor_data_store.readings_history),
        "returned_readings": len(history),
        "data": history
    }

@app.post("/analyze")
async def analyze_sensor_data(request: OllamaAnalysisRequest):
    """Analyze sensor data using Ollama"""
    try:
        # Use provided data or current history
        readings = request.sensor_data if request.sensor_data else sensor_data_store.readings_history[-10:]
        
        if not readings:
            raise HTTPException(status_code=404, detail="No sensor data available for analysis")
        
        # Get analysis from Ollama
        analysis_result = analyze_sensor_data_with_ollama(readings)
        
        return {
            "status": "success",
            "analysis_type": request.analysis_type,
            "result": analysis_result
        }
        
    except Exception as e:
        logger.error(f"Error in analysis endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sensor-status")
async def get_sensor_status():
    """Get sensor and system status"""
    return {
        "sensor_status": sensor_data_store.sensor_status,
        "last_update": sensor_data_store.last_update,
        "total_readings": len(sensor_data_store.readings_history),
        "mqtt_connected": mqtt_client.is_connected() if mqtt_client else False,
        "mqtt_broker": MQTT_BROKER,
        "topics": {
            "temperature": TEMP_TOPIC,
            "humidity": HUMIDITY_TOPIC
        }
    }

@app.post("/simulate-reading")
async def manual_sensor_reading():
    """Manually trigger a sensor reading (for testing)"""
    try:
        reading = dht11_sim.read_sensor()
        
        # Store reading
        sensor_data_store.current_reading = reading
        sensor_data_store.readings_history.append(reading)
        sensor_data_store.last_update = datetime.now()
        
        # Publish to MQTT
        publish_sensor_data(reading)
        
        return {
            "status": "success",
            "reading": reading
        }
        
    except Exception as e:
        logger.error(f"Error in manual reading: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting IoT Agent...")
    
    # Initialize MQTT
    initialize_mqtt()
    
    # Start sensor simulation
    import asyncio
    asyncio.create_task(simulate_sensor_readings())
    
    logger.info("IoT Agent started successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down IoT Agent...")
    
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    
    logger.info("IoT Agent shutdown complete")

# Main entry point
if __name__ == "__main__":
    import uvicorn
    import asyncio
    
    # Run the application
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )