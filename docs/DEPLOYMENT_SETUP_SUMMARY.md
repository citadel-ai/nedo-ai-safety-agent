# Deployment Setup Summary

This document summarizes the deployment infrastructure created for easy local development and Cloud Run deployment.

## Files Created

### 1. `start.sh` - Application Startup Script
**Location**: Root directory

**Purpose**: Easily start both backend and frontend services for local development.

**Features**:
- ✅ Checks for virtual environment and dependencies
- ✅ Verifies `.env` file exists
- ✅ Installs frontend dependencies if needed
- ✅ Starts backend on port 8000
- ✅ Starts frontend dev server on port 3000
- ✅ Saves process IDs for easy cleanup
- ✅ Creates log files in `logs/` directory
- ✅ Provides helpful URLs and monitoring commands

**Usage**:
```bash
./start.sh
```

**Output**:
- Backend logs: `logs/backend.log`
- Frontend logs: `logs/frontend.log`
- PID files: `.pids/backend.pid`, `.pids/frontend.pid`

### 2. `stop.sh` - Application Shutdown Script
**Location**: Root directory

**Purpose**: Gracefully stop all running services.

**Features**:
- ✅ Reads PID files to stop services
- ✅ Graceful shutdown with fallback to force kill
- ✅ Cleans up processes on ports 8000 and 3000
- ✅ Removes PID files after cleanup
- ✅ Handles stale PID files

**Usage**:
```bash
./stop.sh
```

### 3. `Dockerfile` - Production Container Image
**Location**: Root directory

**Purpose**: Build a production-ready Docker image for Cloud Run deployment.

**Features**:
- ✅ Multi-stage build (frontend + backend)
- ✅ Optimized for Cloud Run (PORT environment variable)
- ✅ Non-root user for security
- ✅ Health check endpoint
- ✅ Slim base images for smaller size
- ✅ Production dependencies only

**Build Stages**:
1. **Frontend Builder**: Builds React app with Vite
2. **Backend**: Python backend with built frontend assets

**Usage**:
```bash
# Build
docker build -t japan-procedures-agent .

# Run locally
docker run -p 8080:8080 \
  -e GOOGLE_CLOUD_PROJECT=your-project \
  -e VERTEX_AI_SEARCH_DATA_STORE_ID=your-datastore \
  -e VERTEX_AI_SEARCH_ENGINE_ID=your-engine \
  japan-procedures-agent

# Deploy to Cloud Run
gcloud run deploy japan-procedures-agent \
  --image gcr.io/PROJECT_ID/japan-procedures-agent \
  --region us-central1
```

### 4. `.dockerignore` - Docker Build Exclusions
**Location**: Root directory

**Purpose**: Exclude unnecessary files from Docker builds.

**Excludes**:
- Python cache files and virtual environments
- Node modules (rebuilt in container)
- IDE and OS files
- Environment files (use Cloud Run env vars)
- Logs and temporary files
- Documentation (except README)
- Test files and notebooks

### 5. `cloudbuild.yaml` - CI/CD Configuration
**Location**: Root directory

**Purpose**: Automated build and deployment with Google Cloud Build.

**Features**:
- ✅ Automated build on git push
- ✅ Multi-tag images (SHA + latest)
- ✅ Automatic Cloud Run deployment
- ✅ Configurable resource limits
- ✅ Environment variable management
- ✅ Supports Secret Manager for sensitive data

**Usage**:
```bash
# Manual trigger
gcloud builds submit --config cloudbuild.yaml

# Or set up automatic triggers in GCP Console
```

**Customization**:
Edit substitution variables:
- `_SERVICE_NAME`: Service name in Cloud Run
- `_REGION`: Deployment region
- `_MEMORY`: Memory allocation
- `_CPU`: CPU allocation
- `_MIN_INSTANCES`: Minimum instances (0 for scale-to-zero)
- `_MAX_INSTANCES`: Maximum instances

### 6. `DEPLOYMENT_GUIDE.md` - Complete Documentation
**Location**: Root directory

**Purpose**: Comprehensive guide for all deployment scenarios.

**Contents**:
- Local development setup
- Docker development and testing
- Cloud Run deployment (step-by-step)
- Environment variable reference
- Monitoring and logging
- Troubleshooting guide
- Performance optimization
- Cost optimization tips
- Security best practices

### 7. Updated `.gitignore`
**Changes**: Added exclusions for:
- `logs/` directory (created by start.sh)
- `.pids/` directory (PID files from start.sh)

### 8. Updated `README.md`
**Changes**: 
- Added quick start with scripts
- Added Docker deployment section
- Updated architecture to reflect current structure
- Added all API endpoints
- Improved troubleshooting section
- Added links to deployment documentation

## Directory Structure Created

```
nedo-ai-safety-agent-new/
├── logs/                      # Created by start.sh (gitignored)
│   ├── backend.log
│   └── frontend.log
└── .pids/                     # Created by start.sh (gitignored)
    ├── backend.pid
    └── frontend.pid
```

## Quick Start Guide

### Local Development

**First time setup**:
```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Install frontend dependencies
cd frontend
npm install
cd ..

# 3. Configure environment
cp env_template.txt .env
# Edit .env with your credentials

# 4. Authenticate with Google Cloud
gcloud auth application-default login
```

**Daily development**:
```bash
# Start everything
./start.sh

# ... do your work ...

# Stop everything
./stop.sh
```

### Docker Testing

```bash
# Build
docker build -t japan-procedures-agent .

# Test locally
docker run -p 8080:8080 --env-file .env japan-procedures-agent

# Open http://localhost:8080
```

### Cloud Run Deployment

```bash
# Set variables
export PROJECT_ID=your-project-id
export SERVICE_NAME=japan-procedures-agent

# Build and push
gcloud auth configure-docker
docker build -t gcr.io/${PROJECT_ID}/${SERVICE_NAME} .
docker push gcr.io/${PROJECT_ID}/${SERVICE_NAME}

# Deploy
gcloud run deploy ${SERVICE_NAME} \
  --image gcr.io/${PROJECT_ID}/${SERVICE_NAME} \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"
  # Add more --set-env-vars as needed
```

## Environment Variables

### Required for Cloud Run
```bash
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_AI_SEARCH_DATA_STORE_ID=projects/.../dataStores/...
VERTEX_AI_SEARCH_ENGINE_ID=your-engine-id
```

### Optional
```bash
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-xxx
LANGFUSE_SECRET_KEY=sk-xxx  # Use Secret Manager in production
LANGFUSE_HOST=https://cloud.langfuse.com
USE_ANSWER_METHOD=false
GOOGLE_PLACES_API_KEY=your-key  # Use Secret Manager
```

## Best Practices

### Local Development
1. Use `start.sh` and `stop.sh` for convenience
2. Monitor logs: `tail -f logs/backend.log`
3. Keep virtual environment activated
4. Use `.env` file for local configuration

### Docker Development
1. Test locally before pushing to Cloud Run
2. Use `--env-file .env` for local testing
3. Check image size: `docker images`
4. Test health endpoint: `curl http://localhost:8080/api/health`

### Cloud Run Production
1. Use Secret Manager for sensitive data (API keys, secrets)
2. Set appropriate memory/CPU limits
3. Enable Cloud Logging and Monitoring
4. Use min-instances > 0 for production (avoid cold starts)
5. Set up custom domains with Cloud Load Balancing
6. Enable Cloud Armor for DDoS protection
7. Implement authentication (remove --allow-unauthenticated)

### CI/CD
1. Use Cloud Build triggers for automatic deployment
2. Deploy to staging first, then production
3. Tag images with commit SHA and latest
4. Set up build notifications (Slack, email)
5. Monitor build logs and costs

## Monitoring

### Local Logs
```bash
# View logs
tail -f logs/backend.log
tail -f logs/frontend.log

# Follow both
tail -f logs/*.log
```

### Docker Logs
```bash
# View container logs
docker logs <container-id>

# Follow logs
docker logs -f <container-id>
```

### Cloud Run Logs
```bash
# View in terminal
gcloud run services logs read japan-procedures-agent --region us-central1

# Follow logs
gcloud run services logs tail japan-procedures-agent --region us-central1

# Or use Cloud Console: Logging > Logs Explorer
```

## Troubleshooting

### Scripts don't run
```bash
chmod +x start.sh stop.sh
```

### Ports already in use
```bash
./stop.sh
# Or manually: lsof -ti:8000 | xargs kill -9
```

### Docker build fails
```bash
# Clean Docker cache
docker system prune -a

# Rebuild without cache
docker build --no-cache -t japan-procedures-agent .
```

### Cloud Run deployment fails
```bash
# Check logs
gcloud run services logs read SERVICE_NAME --region REGION

# Describe service
gcloud run services describe SERVICE_NAME --region REGION

# Check IAM permissions
gcloud projects get-iam-policy PROJECT_ID
```

## Cost Optimization

1. **Scale to zero**: Set `min-instances=0` for dev/staging
2. **Right-size resources**: Start with 1 CPU, 2Gi memory
3. **Use Artifact Registry**: Cheaper than Container Registry
4. **Clean up old images**: Delete unused container images
5. **Monitor usage**: Set up budget alerts

## Security Checklist

- ✅ Use Secret Manager for sensitive data
- ✅ Run containers as non-root user (already implemented)
- ✅ Restrict service account permissions
- ✅ Enable VPC Service Controls (if needed)
- ✅ Implement authentication (for production)
- ✅ Regular security scans of images
- ✅ Keep dependencies updated
- ✅ Use HTTPS only (Cloud Run does this by default)

## Next Steps

1. **Local Development**: Run `./start.sh` to begin development
2. **Docker Testing**: Build and test the Docker image locally
3. **Cloud Run Deploy**: Follow DEPLOYMENT_GUIDE.md for production deployment
4. **Set Up CI/CD**: Configure Cloud Build triggers for automatic deployments
5. **Enable Monitoring**: Set up Cloud Monitoring dashboards and alerts
6. **Production Hardening**: Implement authentication, use Secret Manager, enable security features

## Additional Resources

- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Full deployment documentation
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)

## Support

For issues or questions:
1. Check the troubleshooting sections
2. Review application logs
3. Consult the deployment guide
4. Check Cloud Run service status in GCP Console

