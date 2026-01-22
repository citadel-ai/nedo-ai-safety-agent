# Multi-stage Dockerfile for Japan Procedures Agent
# Optimized for Google Cloud Run deployment

# Stage 1: Build frontend
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies (including dev dependencies needed for build)
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Build frontend (outputs to ../agent/dist)
RUN npm run build

# Stage 2: Build Python backend
FROM python:3.11-slim AS backend

WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

# Add uv to PATH
ENV PATH="/root/.cargo/bin:$PATH"

# Copy dependency files
COPY pyproject.toml .

# Install Python dependencies using uv (production only, no dev deps)
RUN uv pip install --system --no-cache .

# Copy backend code
COPY backend/ ./backend/
COPY run_server.py .

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/agent/dist ./agent/dist

# Create a non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Cloud Run expects the app to listen on $PORT
# Default to 8080 if PORT is not set
ENV PORT=8080
ENV API_HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/api/health')"

# Start the application
CMD ["sh", "-c", "python -m uvicorn backend.api.server:app --host 0.0.0.0 --port ${PORT:-8080}"]

