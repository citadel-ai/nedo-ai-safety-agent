# Deployment Guide

This guide covers local development and Google Cloud Run deployment for the Japan Procedures Agent.

## Table of Contents
- [Local Development](#local-development)
- [Docker Development](#docker-development)
- [Cloud Run Deployment](#cloud-run-deployment)
- [Environment Variables](#environment-variables)

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 20+
- Virtual environment set up

### Quick Start

**Start the application:**
```bash
./start.sh
```

This will:
- Check for virtual environment and dependencies
- Start the backend API on http://localhost:8000
- Start the frontend dev server on http://localhost:3000
- Save process IDs for easy cleanup
- Create log files in `logs/` directory

**Stop the application:**
```bash
./stop.sh
```

This will:
- Gracefully stop both backend and frontend
- Clean up any processes on ports 8000 and 3000
- Remove PID files

### Manual Start (Alternative)

**Backend:**
```bash
source venv/bin/activate
python run_server.py
```

**Frontend (in a separate terminal):**
```bash
cd frontend
npm run dev
```

---

## Docker Development

### Build the Docker image

**For local testing (any architecture):**
```bash
docker build -t japan-procedures-agent .
```

**For Cloud Run deployment (must be AMD64):**
```bash
docker buildx build --platform linux/amd64 -t japan-procedures-agent . --load
```

### Run locally with Docker

```bash
docker run -p 8080:8080 \
  -e GOOGLE_CLOUD_PROJECT=your-project-id \
  -e VERTEX_AI_SEARCH_DATA_STORE_ID=your-datastore-id \
  -e VERTEX_AI_SEARCH_ENGINE_ID=your-engine-id \
  -e LANGFUSE_ENABLED=false \
  japan-procedures-agent
```

Access the application at http://localhost:8080

### Test with environment file

**Note**: For local Docker testing, you need to mount Google Cloud credentials:

```bash
# Option 1: Mount your gcloud credentials (recommended for local testing)
docker run -p 8080:8080 \
  --env-file .env \
  -v ~/.config/gcloud:/root/.config/gcloud:ro \
  japan-procedures-agent

# Option 2: Use a service account key file
docker run -p 8080:8080 \
  --env-file .env \
  -v /path/to/service-account.json:/app/credentials.json:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
  japan-procedures-agent
```

**Important**: When deployed to Cloud Run, authentication works automatically via the service account - no credentials mounting needed!

---

## Cloud Run Deployment

### Secret Management (Important!)

**⚠️ NEVER put secrets in `--set-env-vars`!** Use Secret Manager instead.

#### Quick Setup with Script

```bash
# Interactive script to create all secrets
./setup-secrets.sh
```

#### Manual Secret Setup

```bash
# Create secrets (one-time setup)
echo -n "your-langfuse-public-key" | gcloud secrets create langfuse-public-key --data-file=-
echo -n "your-langfuse-secret-key" | gcloud secrets create langfuse-secret-key --data-file=-
echo -n "your-google-places-api-key" | gcloud secrets create google-places-api-key --data-file=-

# Grant Cloud Run access to secrets
PROJECT_ID=your-project-id
SERVICE_ACCOUNT="${PROJECT_ID}@appspot.gserviceaccount.com"

gcloud secrets add-iam-policy-binding langfuse-public-key \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding langfuse-secret-key \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding google-places-api-key \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

#### What Goes Where?

| Type | Method | Examples |
|------|--------|----------|
| **Non-sensitive config** | `--set-env-vars` | `GOOGLE_CLOUD_PROJECT`, `VERTEX_AI_SEARCH_DATA_STORE_ID`, `LANGFUSE_ENABLED`, `LANGFUSE_HOST` |
| **Secrets/API Keys** | `--set-secrets` | `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `GOOGLE_PLACES_API_KEY` |

### Prerequisites

1. **Google Cloud Project**: Set up and configured
2. **APIs Enabled**:
   - Cloud Run API
   - Container Registry or Artifact Registry
   - Vertex AI API
   - Discovery Engine API

3. **gcloud CLI**: Installed and authenticated
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

### Step 1: Build and Push to Artifact Registry

**Important**: Cloud Run requires AMD64 architecture. If you're on Apple Silicon (M1/M2/M3), you must build for AMD64.

```bash
# Set variables
export PROJECT_ID=your-project-id
export REGION=us-central1
export SERVICE_NAME=japan-procedures-agent
export IMAGE_NAME=gcr.io/${PROJECT_ID}/${SERVICE_NAME}

# Build the image for AMD64 (required for Cloud Run)
docker buildx build --platform linux/amd64 -t ${IMAGE_NAME} . --load

# Configure Docker for GCR
gcloud auth configure-docker

# Push to GCR
docker push ${IMAGE_NAME}
```

### Step 2: Deploy to Cloud Run

**Option A: Using the deployment script (recommended)**

```bash
./deploy-to-cloud-run.sh
```

**Option B: Manual deployment**

```bash
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
  --set-secrets "LANGFUSE_SECRET_KEY=langfuse-secret-key:latest" \
  --set-secrets "GOOGLE_PLACES_API_KEY=google-places-api-key:latest"
```

### Step 3: Verify Deployment

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format='value(status.url)')

# Test the health endpoint
curl ${SERVICE_URL}/api/health

# View logs
gcloud run services logs read ${SERVICE_NAME} --region ${REGION}
```

### Step 4: Update Service

To update an existing deployment, just run the script again:

```bash
./deploy-to-cloud-run.sh
```

Or manually:

```bash
# Rebuild and push
docker build -t ${IMAGE_NAME} .
docker push ${IMAGE_NAME}

# Redeploy (keeps existing env vars and secrets)
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --region ${REGION}
```

### Continuous Deployment with Cloud Build

Create `cloudbuild.yaml`:

```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/japan-procedures-agent', '.']
  
  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/japan-procedures-agent']
  
  # Deploy container image to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'japan-procedures-agent'
      - '--image'
      - 'gcr.io/$PROJECT_ID/japan-procedures-agent'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'

images:
  - 'gcr.io/$PROJECT_ID/japan-procedures-agent'
```

Then trigger builds:

```bash
gcloud builds submit --config cloudbuild.yaml
```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_CLOUD_PROJECT` | Your GCP project ID | `my-project-123` |
| `VERTEX_AI_SEARCH_DATA_STORE_ID` | Vertex AI Search datastore ID | `default_data_store` |
| `VERTEX_AI_SEARCH_ENGINE_ID` | Vertex AI Search engine ID | `my-search-engine_123` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LANGFUSE_ENABLED` | Enable Langfuse tracing | `false` |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | - |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key | - |
| `LANGFUSE_HOST` | Langfuse host URL | `https://cloud.langfuse.com` |
| `GOOGLE_PLACES_API_KEY` | Google Places API key | - |
| `PORT` | Server port (Cloud Run sets this) | `8080` |

**Note**: The system automatically chooses between single-turn (`search()`) and multi-turn (`answer()`) methods based on conversation state. First queries use fast single-turn, follow-ups automatically use multi-turn with session continuity.

---

## Monitoring and Logs

### View Cloud Run Logs

```bash
gcloud run services logs read ${SERVICE_NAME} --region ${REGION}
```

### View Logs in Console

1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
2. Click on your service
3. Go to "Logs" tab

### Local Logs

When running locally with `./start.sh`:
- Backend logs: `logs/backend.log`
- Frontend logs: `logs/frontend.log`

View in real-time:
```bash
tail -f logs/backend.log
tail -f logs/frontend.log
```

---

## Troubleshooting

### Cloud Run Issues

**Issue: "Container manifest type must support amd64/linux"**
- **Cause**: You built the image on Apple Silicon (ARM64) but Cloud Run requires AMD64
- **Solution**: Rebuild with the correct architecture:
  ```bash
  docker buildx build --platform linux/amd64 -t gcr.io/PROJECT_ID/SERVICE_NAME . --load
  docker push gcr.io/PROJECT_ID/SERVICE_NAME
  ```
- **Or**: Use the deployment script which handles this automatically:
  ```bash
  ./deploy-to-cloud-run.sh
  ```

**Issue: Service fails to start**
- Check logs: `gcloud run services logs read ${SERVICE_NAME}`
- Verify environment variables are set
- Check that APIs are enabled

**Issue: Container fails health check**
- Ensure `/api/health` endpoint is accessible
- Check memory/CPU limits
- Review application logs

**Issue: Authentication errors**
- Verify service account has necessary permissions
- Enable required APIs
- Check Secret Manager access

### Docker Issues

**Issue: Build fails**
- Check that all source files are present
- Verify `.dockerignore` isn't excluding necessary files
- Ensure base images are accessible

**Issue: Image too large**
- Review `.dockerignore` configuration
- Use multi-stage builds (already implemented)
- Consider using slim base images

### Local Development Issues

**Issue: Scripts don't run**
- Make scripts executable: `chmod +x start.sh stop.sh`
- Check that virtual environment exists
- Verify Node.js and Python are installed

**Issue: Ports already in use**
- Run `./stop.sh` to clean up
- Manually kill processes: `lsof -ti:8000 | xargs kill -9`

---

## Performance Optimization

### Cloud Run Settings

For production workloads, consider:

```bash
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --region ${REGION} \
  --memory 4Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --timeout 300 \
  --concurrency 80
```

- **Memory**: Increase for better LLM performance
- **CPU**: More CPUs = faster processing
- **Min instances**: Keep warm instances to reduce cold starts
- **Max instances**: Limit to control costs
- **Concurrency**: Requests per container instance

---

## Cost Optimization

1. **Use min-instances=0** for development (scale to zero)
2. **Enable CPU throttling** when idle
3. **Optimize Docker image size** (use multi-stage builds)
4. **Monitor with Cloud Monitoring** to track usage
5. **Set up budget alerts** in GCP

---

## Security Best Practices

1. **Use Secret Manager** for sensitive data (not environment variables)
2. **Restrict service account permissions** (principle of least privilege)
3. **Enable VPC Service Controls** for sensitive workloads
4. **Use Cloud Armor** for DDoS protection
5. **Implement authentication** for production (remove --allow-unauthenticated)
6. **Regular security scans** of container images

---

## Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Vertex AI Search Documentation](https://cloud.google.com/generative-ai-app-builder/docs)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)

