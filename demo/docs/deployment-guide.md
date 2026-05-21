# Deployment Guide

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 20+
- Virtual environment set up

### Running Locally

```bash
./start.sh   # backend on :8000, frontend on :3000
./stop.sh    # tears down both
```

Or manually in two terminals:

```bash
# Terminal 1
source .venv/bin/activate && python run_server.py

# Terminal 2
cd frontend && npm run dev
```

Logs are written to `logs/backend.log` and `logs/frontend.log`.

---

## Docker

### Build

```bash
# Local testing (native architecture)
docker build -t japan-procedures-agent .

# Cloud Run (must be AMD64)
docker buildx build --platform linux/amd64 -t japan-procedures-agent . --load
```

### Run

```bash
docker run -p 8080:8080 \
  -e GOOGLE_CLOUD_PROJECT=your-project-id \
  -e VERTEX_AI_SEARCH_DATA_STORE_ID=your-datastore-id \
  -e VERTEX_AI_SEARCH_ENGINE_ID=your-engine-id \
  japan-procedures-agent
```

For local Docker testing, mount Google Cloud credentials:

```bash
docker run -p 8080:8080 \
  --env-file .env \
  -v ~/.config/gcloud:/root/.config/gcloud:ro \
  japan-procedures-agent
```

When deployed to Cloud Run, authentication works automatically via the service account.

---

## Cloud Run Deployment

### Secret Management

**Never put secrets in `--set-env-vars`.** Use Secret Manager:

```bash
echo -n "your-key" | gcloud secrets create langfuse-public-key --data-file=-
echo -n "your-key" | gcloud secrets create langfuse-secret-key --data-file=-
```

Grant Cloud Run access:

```bash
PROJECT_ID=your-project-id
SERVICE_ACCOUNT="${PROJECT_ID}@appspot.gserviceaccount.com"

gcloud secrets add-iam-policy-binding langfuse-public-key \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

| Type | Method | Examples |
|------|--------|----------|
| Non-sensitive config | `--set-env-vars` | `GOOGLE_CLOUD_PROJECT`, `VERTEX_AI_SEARCH_DATA_STORE_ID`, `LANGFUSE_ENABLED` |
| Secrets/API Keys | `--set-secrets` | `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY` |

### Prerequisites

1. Google Cloud Project with these APIs enabled: Cloud Run, Container/Artifact Registry, Vertex AI, Discovery Engine
2. `gcloud` CLI authenticated: `gcloud auth login && gcloud config set project YOUR_PROJECT_ID`

### Deploy

**Recommended:**

```bash
./deploy-to-cloud-run.sh
```

**Manual:**

```bash
export PROJECT_ID=your-project-id
export REGION=us-central1
export SERVICE_NAME=japan-procedures-agent
export IMAGE_NAME=gcr.io/${PROJECT_ID}/${SERVICE_NAME}

docker buildx build --platform linux/amd64 -t ${IMAGE_NAME} . --load
gcloud auth configure-docker
docker push ${IMAGE_NAME}

gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --timeout 300 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
  --set-env-vars "VERTEX_AI_SEARCH_DATA_STORE_ID=your-datastore-id" \
  --set-env-vars "VERTEX_AI_SEARCH_ENGINE_ID=your-engine-id" \
  --set-env-vars "LANGFUSE_ENABLED=true" \
  --set-env-vars "LANGFUSE_HOST=https://cloud.langfuse.com" \
  --set-secrets "LANGFUSE_PUBLIC_KEY=langfuse-public-key:latest" \
  --set-secrets "LANGFUSE_SECRET_KEY=langfuse-secret-key:latest"
```

### Verify

```bash
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format='value(status.url)')
curl ${SERVICE_URL}/api/health
gcloud run services logs read ${SERVICE_NAME} --region ${REGION}
```

---

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLOUD_PROJECT` | GCP project ID |
| `VERTEX_AI_SEARCH_DATA_STORE_ID` | Vertex AI Search datastore ID |
| `VERTEX_AI_SEARCH_ENGINE_ID` | Vertex AI Search engine ID |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGFUSE_ENABLED` | `false` | Enable Langfuse tracing |
| `LANGFUSE_PUBLIC_KEY` | -- | Langfuse public key |
| `LANGFUSE_SECRET_KEY` | -- | Langfuse secret key |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | Langfuse host URL |
| `PORT` | `8080` | Server port (Cloud Run sets this) |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Container manifest must support amd64/linux" | Rebuild with `--platform linux/amd64` or use `./deploy-to-cloud-run.sh` |
| Service fails to start | Check logs: `gcloud run services logs read ${SERVICE_NAME}` |
| Container fails health check | Verify `/api/health` is accessible, check memory/CPU limits |
| Authentication errors | Verify service account permissions and enabled APIs |
| Scripts don't run | `chmod +x start.sh stop.sh` |
| Ports already in use | `./stop.sh` or `lsof -ti:8000 | xargs kill -9` |

---

## Production Tuning

```bash
gcloud run deploy ${SERVICE_NAME} \
  --memory 4Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --timeout 300 \
  --concurrency 80
```

Set `min-instances > 0` to reduce cold starts. Set up [budget alerts](https://cloud.google.com/billing/docs/how-to/budgets) to control costs.

## Security Checklist

- Use Secret Manager for all API keys
- Restrict service account permissions (least privilege)
- Remove `--allow-unauthenticated` for production
- Never commit `.env` files to git
