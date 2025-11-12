# Dockerfile for Daily Screener Cloud Run Job
#
# This runs daily via Cloud Scheduler to populate Firestore with screener results.
# Optimized for batch processing with longer timeouts and higher memory.

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir google-cloud-firestore

# Copy application code
COPY app ./app
COPY jobs ./jobs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Run the job
CMD ["python", "jobs/run_daily_screeners.py"]
