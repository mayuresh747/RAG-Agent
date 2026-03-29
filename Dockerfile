# Use official Python runtime
FROM python:3.11-slim

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

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Copy the rest of the application and set ownership
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Pre-bake cross-encoder model as appuser so cache lands in /home/appuser/.cache/huggingface/
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

# Expose the port
EXPOSE 8000

# Run the application
CMD ["python", "scripts/run_chat.py", "--host", "0.0.0.0", "--port", "8000"]
