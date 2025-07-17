# adk_ollama_tool/tools/ollama_tool.py (ensure this part is correct)
import httpx
import json

class OllamaTool:
    def __init__(self, base_url: str, model: str = "gemma3:1b"): # <-- Ensure model is gemma3:1b
        self.base_url = base_url
        self.model = model
        self.client = httpx.AsyncClient()

    async def query(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        headers = {"Content-Type": "application/json"}
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False # We want a single response for the dashboard
        }
        try:
            response = await self.client.post(url, headers=headers, json=data, timeout=600.0) # Increased timeout for LLM
            response.raise_for_status()
            result = response.json()
            return result.get("response", "No response from LLM.")
        except httpx.RequestError as e:
            print(f"Ollama connection error: {e}")
            return f"Error: Could not connect to Ollama ({e}). Is it running and accessible?"
        except httpx.HTTPStatusError as e:
            print(f"Ollama API error: {e.response.status_code} - {e.response.text}")
            return f"Error from Ollama API: {e.response.status_code} - {e.response.text}"
        except Exception as e:
            print(f"An unexpected error occurred with Ollama: {e}")
            return f"An unexpected error occurred while querying Ollama: {e}"

    async def get_available_models(self) -> list:
        url = f"{self.base_url}/api/tags"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            models_info = response.json().get("models", [])
            return [model["name"] for model in models_info]
        except httpx.RequestError as e:
            print(f"Ollama connection error when fetching models: {e}")
            return []
        except httpx.HTTPStatusError as e:
            print(f"Ollama API error when fetching models: {e.response.status_code} - {e.response.text}")
            return []