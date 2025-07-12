#!/bin/sh

# Wait for Ollama to be ready
echo "Waiting for Ollama to be ready..."
until curl -s http://ollama:11434/api/tags > /dev/null 2>&1; do
    echo "Ollama not ready yet, waiting..."
    sleep 5
done

echo "Ollama is ready! Pulling Gemma models..."

# Pull Gemma 3 model (smaller, faster)
echo "Pulling gemma3:9b model..."
curl -X POST http://ollama:11434/api/pull \
  -H "Content-Type: application/json" \
  -d '{"name": "gemma3:9b"}'

# Pull Gemma 2 model (alternative)
echo "Pulling gemma2:2b model..."
curl -X POST http://ollama:11434/api/pull \
  -H "Content-Type: application/json" \
  -d '{"name": "gemma2:2b"}'

echo "Models pulled successfully!"

# Verify models are available
echo "Available models:"
curl -s http://ollama:11434/api/tags | jq '.models[].name'

echo "Ollama initialization complete!"