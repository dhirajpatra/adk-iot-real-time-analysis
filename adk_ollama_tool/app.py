# adk_ollama_tool/app.py
from fastapi import FastAPI, HTTPException, Request # <--- ADDED 'Request' here
from fastapi.responses import HTMLResponse
import httpx # Correct: For making HTTP requests to Ollama and MCP server
import os
import json
import asyncio

app = FastAPI()

# Get URLs from environment variables
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://mcp_server:4000")

# Initialize HTTP client for asynchronous requests
# Using a global client for better performance
client = httpx.AsyncClient()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """
    Root endpoint for a simple HTML response or health check.
    """
    html_content = """
    <html>
        <head>
            <title>ADK Ollama Tool</title>
        </head>
        <body>
            <h1>ADK Ollama Tool is running!</h1>
            <p>Try these endpoints:</p>
            <ul>
                <li><a href="/chat?prompt=hello">/chat?prompt=hello</a> - Interact with Ollama (gemma2:2b)</li>
                <li><a href="/math?num1=5&num2=3">/math?num1=5&num2=3</a> - Interact with MCP Server</li>
                <li><a href="/sse_test">/sse_test</a> - Test SSE from MCP Server</li>
            </ul>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/chat")
async def chat_with_ollama(prompt: str = "tell me a short story"):
    """
    Endpoint to interact with the Ollama service.
    Sends a prompt and returns the LLM's response.
    """
    model_name = "gemma2:2b" # Ensure this model is pulled by your Ollama service

    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False # Set to True for streaming responses
    }

    try:
        ollama_url = f"{OLLAMA_BASE_URL}/api/generate"
        print(f"Sending prompt '{prompt}' to Ollama at {ollama_url}")
        response = await client.post(ollama_url, json=payload, timeout=300.0) # Increased timeout
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

        data = response.json()
        print(f"Received response from Ollama: {data}")

        if "response" in data:
            return {"model": model_name, "prompt": prompt, "response": data["response"]}
        else:
            # If Ollama's API changes or provides a different structure
            return {"error": "Unexpected response format from Ollama", "details": data}

    except httpx.RequestError as exc:
        print(f"An error occurred while requesting Ollama: {exc}")
        raise HTTPException(status_code=500, detail=f"Could not connect to Ollama service: {exc}")
    except httpx.HTTPStatusError as exc:
        print(f"HTTP error from Ollama: {exc.response.status_code} - {exc.response.text}")
        raise HTTPException(status_code=exc.response.status_code, detail=f"Ollama service responded with an error: {exc.response.text}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.get("/math")
async def get_math_result(num1: int, num2: int):
    """
    Endpoint to interact with the MCP server for a calculation.
    """
    payload = {
        "num1": num1,
        "num2": num2
    }
    try:
        mcp_url = f"{MCP_SERVER_URL}/calculate"
        print(f"Sending math request to MCP server at {mcp_url} with {payload}")
        response = await client.post(mcp_url, json=payload, timeout=60.0)
        response.raise_for_status()
        result = response.json()
        print(f"Received result from MCP server: {result}")
        return {"operation": "sum", "input": payload, "mcp_response": result}
    except httpx.RequestError as exc:
        print(f"An error occurred while requesting MCP server: {exc}")
        raise HTTPException(status_code=500, detail=f"Could not connect to MCP server: {exc}")
    except httpx.HTTPStatusError as exc:
        print(f"HTTP error from MCP server: {exc.response.status_code} - {exc.response.text}")
        raise HTTPException(status_code=exc.response.status_code, detail=f"MCP server responded with an error: {exc.response.text}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@app.get("/sse_test", response_class=HTMLResponse)
async def sse_test_page():
    """
    A simple HTML page to test the SSE endpoint from MCP server.
    """
    return """
    <html>
        <head>
            <title>SSE Test</title>
        </head>
        <body>
            <h1>SSE from MCP Server</h1>
            <div id="events"></div>
            <script>
                const eventSource = new EventSource("/internal_sse_proxy");
                eventSource.onmessage = function(event) {
                    const newElement = document.createElement("p");
                    newElement.textContent = `Event: ${event.data}`;
                    document.getElementById("events").appendChild(newElement);
                };
                eventSource.onerror = function(err) {
                    console.error("EventSource failed:", err);
                    eventSource.close();
                };
            </script>
            <p>Check browser console for SSE errors.</p>
        </body>
    </html>
    """

@app.get("/internal_sse_proxy")
async def internal_sse_proxy(request: Request):
    """
    Proxies the SSE stream from MCP server to the ADK app client.
    This is necessary because client-side EventSource might not directly
    access a service URL (like mcp_server:4000)
    """
    async def sse_events():
        try:
            async with client.stream("GET", f"{MCP_SERVER_URL}/sse", timeout=None) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    if await request.is_disconnected():
                        print("Client disconnected from ADK SSE proxy.")
                        break
                    yield chunk
        except httpx.RequestError as exc:
            print(f"SSE Proxy: An error occurred while connecting to MCP server: {exc}")
        except httpx.HTTPStatusError as exc:
            print(f"SSE Proxy: HTTP error from MCP server: {exc.response.status_code} - {exc.response.text}")
        except Exception as e:
            print(f"SSE Proxy: An unexpected error occurred: {e}")

    return StreamingResponse(sse_events(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)