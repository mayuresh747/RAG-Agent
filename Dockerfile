# Use official Python runtime
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies (for building some python packages)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port
EXPOSE 8000

# Run the application
CMD ["python", "scripts/run_chat.py", "--host", "0.0.0.0", "--port", "8000"]
