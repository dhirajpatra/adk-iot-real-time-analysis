#!/bin/bash

# Start Ollama server in the background
# The 'exec' command ensures that 'ollama serve' becomes PID 1, allowing it to
# receive signals (like SIGTERM for graceful shutdown). The '&' allows
# the script to continue to the next commands.
exec ollama serve &
OLLAMA_PID=$!

# Ensure model directory exists (Ollama usually handles this, but good for explicit paths)
mkdir -p /root/.ollama/models

# Wait for the Ollama server to be available locally before trying to list/pull
echo "Waiting for the Ollama server to become responsive locally..."
until curl -s http://localhost:11434 > /dev/null; do
  echo "Ollama server is still starting..."
  sleep 2
done
echo "Ollama server is responsive."


# Pull model if not already present
MODEL_NAME="gemma2:2b" # Only this model will be pulled

if ! ollama list | grep -q "$MODEL_NAME"; then
  echo "Model not found. Pulling $MODEL_NAME..."
  until ollama pull "$MODEL_NAME"; do
    echo "Retrying model download in 5 seconds..."
    sleep 5 # Added a sleep for more robust retries
  done
else
  echo "Model $MODEL_NAME already exists. Skipping pull."
fi

# Keep container alive by waiting for the Ollama server process
# This ensures the container doesn't exit as long as Ollama is running.
echo "Ollama initialization complete. Keeping Ollama server running."
wait $OLLAMA_PID