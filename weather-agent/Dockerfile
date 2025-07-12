# Stage 1: Builder - for installing dependencies
# Using a slim-bullseye image for better compatibility than alpine in some cases
FROM python:3.11-slim-bullseye AS builder

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker cache
# If requirements.txt doesn't change, this layer won't be rebuilt
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir: Prevents pip from storing cached .whl files, reducing image size
# --upgrade: Ensures all packages are upgraded to their latest compatible versions
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Stage 2: Production - for the final, lean image
FROM python:3.11-slim-bullseye

# Set the working directory again
WORKDIR /app

# Copy installed dependencies from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the rest of your application code
# This should be done after dependencies to maximize cache hits
COPY app ./app

# Create a non-root user for security best practices
RUN adduser --system --group appuser
USER appuser

# Expose the port your FastAPI application will run on
EXPOSE 8000

# Command to run the application using Uvicorn
# main:app assumes your FastAPI app instance is named 'app' in 'app/main.py'
# --host 0.0.0.0 allows it to be accessed from outside the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]