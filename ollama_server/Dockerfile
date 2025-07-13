# ./ollama_server/Dockerfile
# Start from the official ollama image
FROM ollama/ollama:latest

# Install Python and dependencies needed by your entrypoint or other scripts
# 'build-essential' and 'python3-dev' are common for many Python packages
# 'python3-venv' is needed to create virtual environments
RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv curl build-essential python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Set working directory inside the container
WORKDIR /app/ollama_server

# Copy all files from the build context (which is ./ollama_server on the host)
# directly into the WORKDIR (/app/ollama_server inside the container)
COPY . .

# Create a Python virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV

# Activate the virtual environment and install Python dependencies
# 'set +e' is used to temporarily disable exit on error for the activation command
# as 'source' can sometimes cause issues in non-interactive shells, though this
# approach with 'venv/bin/pip' is more direct.
# We explicitly use the pip from the virtual environment.
RUN $VIRTUAL_ENV/bin/pip install --no-cache-dir -r requirements.txt

# Ensure entrypoint script is executable
RUN chmod +x entrypoint.sh

# Define this script as the container's entrypoint
# Modify entrypoint.sh to activate the venv before running python scripts if needed.
ENTRYPOINT ["/bin/bash", "entrypoint.sh"]