# Multi-stage Dockerfile for FastAPI Backend with Testing
# Production-optimized with security best practices and test validation

# ========================================
# Stage 1: Test and Build
# ========================================
FROM python:3.11-slim as test

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt requirements-dev.txt ./

# Install ALL dependencies (including test dependencies)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-dev.txt

# Copy application code
COPY . .

# Run linting and type checking
RUN echo "Running code quality checks..." && \
    black --check app/ || (echo "❌ Black formatting check failed" && exit 1) && \
    flake8 app/ --max-line-length=100 --extend-ignore=E203,W503 || (echo "❌ Flake8 linting failed" && exit 1) && \
    mypy app/ --ignore-missing-imports || (echo "❌ MyPy type checking failed" && exit 1) && \
    echo "✅ Code quality checks passed"

# Run security scanning
RUN echo "Running security scans..." && \
    bandit -r app/ -ll || (echo "❌ Bandit security scan failed" && exit 1) && \
    echo "✅ Security scans passed"

# Run tests with coverage
RUN echo "Running test suite..." && \
    pytest tests/ \
      --cov=app \
      --cov-report=term-missing \
      --cov-report=html \
      --cov-report=xml \
      --cov-fail-under=80 \
      -v \
      || (echo "❌ Tests failed or coverage below 80%" && exit 1) && \
    echo "✅ All tests passed with adequate coverage"

# ========================================
# Stage 2: Production Builder
# ========================================
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only production requirements
COPY requirements.txt .

# Install Python dependencies to a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# ========================================
# Stage 3: Production Runtime
# ========================================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000 \
    ENVIRONMENT=production

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code (only what passed tests!)
COPY --chown=appuser:appuser --from=test /app/app ./app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=2)"

# Run the application
CMD exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT} \
    --workers 2 \
    --loop uvloop \
    --log-level info \
    --no-access-log

# Build metadata
LABEL maintainer="GoingMerry-Stonks Team"
LABEL version="1.0.0"
LABEL description="FastAPI backend for stock and options analysis (tested and production-ready)"
