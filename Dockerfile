# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM python:3.11-slim

# Install system dependencies including build tools
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.6.12

WORKDIR /code

# Copy Python dependencies
COPY ./pyproject.toml ./uv.lock* ./

# Install Python dependencies
RUN uv sync --frozen

# Copy application code
COPY ./app ./app

# Copy pre-built frontend
COPY ./frontend/dist ./static

ARG COMMIT_SHA=""
ENV COMMIT_SHA=${COMMIT_SHA}

# Set environment variables for production
ENV PYTHONPATH=/code
ENV LANGFUSE_ENABLED=false

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uv", "run", "uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8080"]