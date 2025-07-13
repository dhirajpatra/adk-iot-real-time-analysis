from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import asyncio
import json
import time
import random
import uvicorn # <--- Add this import

app = FastAPI()

@app.get("/")
async def read_root():
    """Basic health check endpoint for the MCP server."""
    return {"message": "MCP Server (FastAPI) is running!"}

@app.get("/sse")
async def sse_endpoint(request: Request):
    """
    Server-Sent Events endpoint for real-time updates.
    This simulates sending math results or other data.
    """
    async def event_generator():
        client_disconnected = False
        while not client_disconnected:
            try:
                await asyncio.sleep(0.1)
                # For FastAPI, checking request.is_disconnected() is more reliable
                if await request.is_disconnected(): # Better disconnection check
                    client_disconnected = True
                    print("Client disconnected from SSE.")
                    break
            except asyncio.CancelledError:
                client_disconnected = True
                print("Client disconnected from SSE (CancelledError).")
                break

            math_result = {
                "timestamp": time.time(),
                "value": random.uniform(100, 1000),
                "operation": "random_math_op"
            }
            yield f"data: {json.dumps(math_result)}\n\n"

            await asyncio.sleep(1) # Send an event every 1 second

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/calculate")
async def calculate_something(data: dict):
    print(f"Received calculation request: {data}")
    result = data.get("num1", 0) + data.get("num2", 0)
    return {"result": result, "status": "completed"}

# --- ADD THIS BLOCK TO RUN THE FASTAPI APPLICATION ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4000)