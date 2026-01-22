# Japan Procedures Assistant

A minimal, stable AI assistant for official procedures in Japan, powered by LangGraph and Vertex AI Search with a React frontend.

## Features

- ✅ **Simple & Stable**: FastAPI backend + React frontend
- ✅ **LangGraph**: Following best practices for agent orchestration  
- ✅ **Vertex AI Search**: Grounded answers with automatic citations
- ✅ **Clean UI**: Minimalistic React + Tailwind design with card layout
- ✅ **Langfuse v3 Integration**: Full observability with session tracking, tags, and metadata
  - [Quick Start Guide](LANGFUSE_V3_QUICK_START.md) - 5-minute setup
  - [Session Tracking](LANGFUSE_SESSION_TRACKING.md) - Multi-turn conversation tracking
  - [Best Practices](LANGFUSE_BEST_PRACTICES.md) - Following official Langfuse docs
  - [Full Documentation](LANGFUSE_INTEGRATION.md) - Complete integration guide
- ✅ **Easy Deployment**: Docker support with Cloud Run ready
- ✅ **No Complex Dependencies**: Just the essentials

## Architecture

```
backend/
├── api/
│   └── server.py            # FastAPI REST API
├── core/
│   ├── graph.py             # LangGraph orchestration
│   └── state.py             # State management
├── nodes/                   # Agent nodes
├── services/                # Business logic
├── tools/                   # External integrations
└── utils/                   # Configuration & utilities

frontend/
├── src/
│   ├── App.jsx              # Main React component
│   ├── components/          # UI components
│   └── index.css            # Tailwind styles
├── vite.config.js           # Vite configuration
└── package.json             # Node dependencies
```

## Quick Start

### Option 1: Easy Start/Stop Scripts (Recommended for Development)

```bash
# Start both backend and frontend
./start.sh

# Stop everything
./stop.sh
```

The scripts will:
- ✅ Check dependencies and virtual environment
- ✅ Start backend on http://localhost:8000
- ✅ Start frontend on http://localhost:3000
- ✅ Create log files in `logs/` directory
- ✅ Track processes for easy cleanup

### Option 2: Manual Setup

#### 1. Setup Environment

```bash
# Copy environment template
cp env_template.txt .env

# Edit .env with your credentials
nano .env
```

Add your Google Cloud credentials:
```env
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_AI_SEARCH_DATA_STORE_ID=projects/.../data-stores/...
VERTEX_AI_SEARCH_ENGINE_ID=your-engine-id
```

#### 2. Authenticate Google Cloud

```bash
gcloud auth application-default login
```

#### 3. Install Dependencies

**Recommended: Using uv (10-100x faster)**

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"  # includes dev tools like ruff, pytest

# Frontend dependencies
cd frontend
npm install
cd ..
```

**Alternative: Using pip**

```bash
# Python dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend dependencies
cd frontend
npm install
cd ..
```

See [README_UV_SETUP.md](README_UV_SETUP.md) for detailed uv usage and benefits.

#### 4. Run the Application

**Development Mode (two terminals):**

Terminal 1 - Backend:
```bash
source venv/bin/activate
python run_server.py
```

Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

Then open http://localhost:3000

### Option 3: Docker (Production)

```bash
# Build the Docker image
docker build -t japan-procedures-agent .

# Run with environment variables
docker run -p 8080:8080 \
  -e GOOGLE_CLOUD_PROJECT=your-project-id \
  -e VERTEX_AI_SEARCH_DATA_STORE_ID=your-datastore-id \
  -e VERTEX_AI_SEARCH_ENGINE_ID=your-engine-id \
  japan-procedures-agent
```

Then open http://localhost:8080

## Deployment

### Google Cloud Run

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for complete deployment instructions.

**⚠️ Apple Silicon Users**: If you're on M1/M2/M3 Mac, the deployment script automatically handles the architecture conversion (ARM64 → AMD64). See [ARCHITECTURE_NOTE.md](ARCHITECTURE_NOTE.md) for details.

**Quick deployment:**

```bash
./deploy-to-cloud-run.sh
```

**Manual deployment:**

```bash
# Set your project
export PROJECT_ID=your-project-id
export SERVICE_NAME=japan-procedures-agent

# Create secrets (one-time)
echo -n "your-langfuse-public-key" | gcloud secrets create langfuse-public-key --data-file=-
echo -n "your-langfuse-secret-key" | gcloud secrets create langfuse-secret-key --data-file=-

# Build and push
docker build -t gcr.io/${PROJECT_ID}/${SERVICE_NAME} .
docker push gcr.io/${PROJECT_ID}/${SERVICE_NAME}

# Deploy with secrets
gcloud run deploy ${SERVICE_NAME} \
  --image gcr.io/${PROJECT_ID}/${SERVICE_NAME} \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
  --set-env-vars "VERTEX_AI_SEARCH_DATA_STORE_ID=your-datastore-id" \
  --set-env-vars "VERTEX_AI_SEARCH_ENGINE_ID=your-engine-id" \
  --set-secrets "LANGFUSE_PUBLIC_KEY=langfuse-public-key:latest" \
  --set-secrets "LANGFUSE_SECRET_KEY=langfuse-secret-key:latest"
```

## Usage

1. Open the application in your browser
2. Enter your visa type and location to set context
3. Type your questions in the chat interface
4. View answers with automatic citations
5. See collected facts and useful phrases/places

## API Endpoints

### POST /api/context
Set user context (visa type and location).

**Request:**
```json
{
  "thread_id": "user-123",
  "visa_type": "Student Visa",
  "location": "Tokyo"
}
```

### POST /api/query
Query the agent with a question.

**Request:**
```json
{
  "question": "How do I get a residence card in Japan?",
  "thread_id": "user-123"
}
```

**Response:**
```json
{
  "query": "How do I get a residence card in Japan?",
  "answer": "To obtain a residence card...",
  "citations": [
    {
      "citation_number": 1,
      "title": "Immigration Guide",
      "url": "https://example.com",
      "source_type": "web"
    }
  ],
  "collected_facts": ["User has student visa", "Located in Tokyo"],
  "useful_phrases": [],
  "useful_places": [],
  "error": null
}
```

### GET /api/thread/{thread_id}
Get current state of a conversation thread.

### DELETE /api/thread/{thread_id}/facts
Remove a specific fact from collected facts.

### GET /api/health
Health check endpoint.

## Technology Stack

- **Backend**: FastAPI, uvicorn, LangGraph, LangChain
- **Agent**: LangGraph StateGraph + Vertex AI Search
- **Frontend**: React, Vite, Tailwind CSS, Flowbite
- **Search**: Vertex AI Search & Vertex AI Answer (Google Cloud)
- **Observability**: Langfuse v3, LangSmith
- **Deployment**: Docker, Google Cloud Run

## Configuration

Environment variables in `.env`:

### Required
```env
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_AI_SEARCH_DATA_STORE_ID=your-data-store-id
VERTEX_AI_SEARCH_ENGINE_ID=your-engine-id
```

### Optional
```env
# Langfuse (Observability)
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-xxx
LANGFUSE_SECRET_KEY=sk-xxx
LANGFUSE_HOST=https://cloud.langfuse.com

# Google Places (for location services)
GOOGLE_PLACES_API_KEY=your-places-api-key
```

## Development

### Viewing Logs

```bash
# If using start.sh script
tail -f logs/backend.log
tail -f logs/frontend.log

# Or view both
tail -f logs/*.log
```

### Hot Reload

Both backend and frontend support hot reload in development mode:
- Backend: uvicorn with `--reload`
- Frontend: Vite HMR (Hot Module Replacement)

## Project Structure

- **backend/api/server.py**: FastAPI server with REST API
- **backend/core/graph.py**: LangGraph agent orchestration
- **backend/nodes/**: Agent nodes (check_scope, extract_facts, etc.)
- **backend/tools/**: External integrations (Vertex AI, Google Maps)
- **frontend/src/**: React UI components
- **run_server.py**: Entry point for running the server
- **start.sh**: Convenience script to start everything
- **stop.sh**: Convenience script to stop everything
- **Dockerfile**: Production-ready Docker image
- **deploy-to-cloud-run.sh**: Deployment script for Google Cloud Run

## Documentation

- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Complete deployment instructions
- [LANGFUSE_BEST_PRACTICES.md](LANGFUSE_BEST_PRACTICES.md) - Observability best practices
- [LANGGRAPH_TIME_TRAVEL.md](LANGGRAPH_TIME_TRAVEL.md) - Time travel debugging
- [MULTI_TURN_IMPLEMENTATION.md](MULTI_TURN_IMPLEMENTATION.md) - Multi-turn conversations
- [CITATION_EXTRACTION.md](CITATION_EXTRACTION.md) - Citation handling

## Troubleshooting

### Scripts won't run
```bash
chmod +x start.sh stop.sh
```

### Backend won't start
- Check `.env` configuration
- Verify Google Cloud authentication: `gcloud auth application-default login`
- Ensure dependencies are installed: `pip install -r requirements.txt`

### Frontend not connecting
- Check backend is running on port 8000
- Verify CORS is enabled (it is by default)
- Check browser console for errors

### Ports already in use
```bash
./stop.sh  # Clean up any running processes
```

### Docker build fails
- Ensure all dependencies are installed
- Check `.dockerignore` isn't excluding necessary files
- Verify Docker is running

### No results from queries
- Verify Vertex AI Search data store has documents
- Check data store ID and engine ID format in `.env`
- Ensure Google Cloud APIs are enabled

## License

This project is provided as-is for educational and development purposes.
