#!/bin/bash

# Deploy to Google Cloud Run with proper secret management
# Usage: ./deploy-to-cloud-run.sh

set -e

# Configuration
PROJECT_ID="nedo-ai-safety-citadel-ai"
SERVICE_NAME="japan-helpdesk"
REGION="asia-northeast1"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Deploying Japan Procedures Agent to Cloud Run${NC}"
echo ""

# Check if gcloud is configured
if ! gcloud config get-value project &> /dev/null; then
    echo -e "${RED}❌ gcloud is not configured. Run: gcloud auth login${NC}"
    exit 1
fi

# Set project
echo -e "${BLUE}Setting project to ${PROJECT_ID}...${NC}"
gcloud config set project ${PROJECT_ID}

# Ensure buildx is available
if ! docker buildx version &> /dev/null; then
    echo -e "${YELLOW}Setting up Docker buildx...${NC}"
    docker buildx create --use --name multiarch --driver docker-container
fi

# Build Docker image for AMD64 (Cloud Run requirement)
echo -e "${BLUE}📦 Building Docker image for AMD64 (Cloud Run)...${NC}"
docker buildx build --platform linux/amd64 -t ${IMAGE} . --load

# Configure Docker for GCR
echo -e "${BLUE}🔐 Configuring Docker authentication...${NC}"
gcloud auth configure-docker --quiet

# Push to GCR
echo -e "${BLUE}⬆️  Pushing image to Container Registry...${NC}"
docker push ${IMAGE}

# Deploy to Cloud Run
echo -e "${BLUE}🚢 Deploying to Cloud Run...${NC}"
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE} \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
  --set-env-vars "VERTEX_AI_SEARCH_DATA_STORE_ID=periodic-pdf_1760448175058_gcs_store" \
  --set-env-vars "VERTEX_AI_SEARCH_ENGINE_ID=test-periodic-pdfs_1760523041262" \
  --set-env-vars "LANGFUSE_ENABLED=true" \
  --set-env-vars "LANGFUSE_HOST=https://langfuse-sso.ai-safety-agent.com" \
  --set-secrets "LANGFUSE_PUBLIC_KEY=langfuse-public-key:latest" \
  --set-secrets "LANGFUSE_SECRET_KEY=langfuse-secret-key:latest" \
  --set-secrets "GOOGLE_PLACES_API_KEY=google-places-api-key:latest"

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format='value(status.url)')
echo -e "${GREEN}🌐 Service URL: ${SERVICE_URL}${NC}"
echo -e "${GREEN}📊 Health Check: ${SERVICE_URL}/api/health${NC}"
echo -e "${GREEN}📚 API Docs: ${SERVICE_URL}/docs${NC}"
echo ""
echo -e "${BLUE}To view logs:${NC}"
echo "  gcloud run services logs read ${SERVICE_NAME} --region ${REGION}"
echo ""
echo -e "${BLUE}To update the service later:${NC}"
echo "  ./deploy-to-cloud-run.sh"

