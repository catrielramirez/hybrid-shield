# Use an official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.11-slim

# Allow statements and log messages to immediately appear in the logs
ENV PYTHONUNBUFFERED=True
# Prevents Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1

# Set the working directory to /app
WORKDIR /app

# Copy local code to the container image.
COPY requirements.txt .

# Install dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code.
COPY . .

# Cloud Run uses the PORT environment variable, which defaults to 8080.
EXPOSE 8080

# Command to run the application using uvicorn.
# Use 0.0.0.0 to bind to all network interfaces.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
