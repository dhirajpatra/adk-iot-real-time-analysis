# adk_ollama_tool/tools/mcp_tool.py
import httpx
import json

class MCPTool:
    """
    A tool to interact with the MCP (Math Calculation Provider) server.
    """
    def __init__(self, mcp_server_url: str):
        self._mcp_server_url = mcp_server_url
        self._client = httpx.AsyncClient()

    async def calculate(self, num1: int, num2: int) -> dict:
        """
        Sends two numbers to the MCP server's /calculate endpoint and returns the JSON result.
        """
        payload = {
            "num1": num1,
            "num2": num2
        }
        try:
            mcp_url = f"{self._mcp_server_url}/calculate"
            print(f"MCPTool: Sending calculation request to {mcp_url} with {payload}")
            response = await self._client.post(mcp_url, json=payload, timeout=60.0)
            response.raise_for_status() # Raise an exception for HTTP errors
            return response.json()
        except httpx.RequestError as exc:
            print(f"MCPTool: Could not connect to MCP server: {exc}")
            return {"error": f"Could not connect to MCP server. Ensure it's running. Details: {exc}"}
        except httpx.HTTPStatusError as exc:
            print(f"MCPTool: MCP server responded with an HTTP error: {exc.response.status_code} - {exc.response.text}")
            return {"error": f"MCP server HTTP error. Status: {exc.response.status_code}. Details: {exc.response.text}"}
        except Exception as e:
            print(f"MCPTool: An unexpected error occurred: {e}")
            return {"error": f"An unexpected error occurred while interacting with MCP. Details: {e}"}