# adk_ollama_tool/tools/ollama_tool.py
import httpx
import json

class OllamaTool:
    """
    A tool to interact with the Ollama local LLM service.
    """
    def __init__(self, ollama_base_url: str):
        self._ollama_base_url = ollama_base_url
        self._client = httpx.AsyncClient()
        self.model_name = "gemma2:2b" # Define the LLM model to use with Ollama

    async def chat_with_ollama(self, prompt: str) -> str:
        """
        Sends a text prompt to the Ollama service and returns the LLM's response.
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False # Set to True if you want to handle streaming responses
        }
        try:
            ollama_url = f"{self._ollama_base_url}/api/generate"
            print(f"OllamaTool: Sending prompt '{prompt}' to Ollama at {ollama_url}")
            response = await self._client.post(ollama_url, json=payload, timeout=300.0) # Increased timeout for LLM
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)

            data = response.json()
            # Ollama's /api/generate returns the response in a 'response' field
            return data.get("response", "No response received from Ollama.")
        except httpx.RequestError as exc:
            print(f"OllamaTool: Could not connect to Ollama service: {exc}")
            return f"Error: Could not connect to Ollama service. Ensure it's running. Details: {exc}"
        except httpx.HTTPStatusError as exc:
            print(f"OllamaTool: Ollama service responded with an HTTP error: {exc.response.status_code} - {exc.response.text}")
            return f"Error: Ollama service HTTP error. Status: {exc.response.status_code}. Details: {exc.response.text}"
        except Exception as e:
            print(f"OllamaTool: An unexpected error occurred: {e}")
            return f"Error: An unexpected error occurred while interacting with Ollama. Details: {e}"