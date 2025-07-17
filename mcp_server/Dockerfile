# mcp_server/Dockerfile.mcp (or Dockerfile)

# Assuming a Debian-based image like python:3.9-slim-buster or similar
FROM python:3.11-slim

# Install curl (and other dependencies if your server.py needed them, like git for example)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose the port FastAPI runs on
EXPOSE 4000

# Your CMD or ENTRYPOINT
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "4000"]