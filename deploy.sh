#!/bin/bash

# Japan Helpdesk - Cloud Run Deployment Script
# This script builds and deploys the Japan Helpdesk system to Google Cloud Run

set -e

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"your-project-id"}
REGION=${REGION:-"us-central1"}
SERVICE_NAME="japan-helpdesk"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Japan Helpdesk - Cloud Run Deployment${NC}"
echo "=================================================="

# Check if required tools are installed
check_tool() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 is not installed. Please install it first.${NC}"
        exit 1
    fi
}

echo -e "${YELLOW}🔍 Checking required tools...${NC}"
check_tool "gcloud"
check_tool "docker"

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}❌ Not authenticated with gcloud. Please run 'gcloud auth login'${NC}"
    exit 1
fi

# Set the project
if [ "$PROJECT_ID" = "your-project-id" ]; then
    echo -e "${RED}❌ Please set your GOOGLE_CLOUD_PROJECT environment variable${NC}"
    echo "   export GOOGLE_CLOUD_PROJECT=your-actual-project-id"
    exit 1
fi

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "   Project ID: $PROJECT_ID"
echo "   Region: $REGION"
echo "   Service Name: $SERVICE_NAME"
echo "   Image: $IMAGE_NAME"
echo ""

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com --project=$PROJECT_ID
gcloud services enable run.googleapis.com --project=$PROJECT_ID
gcloud services enable containerregistry.googleapis.com --project=$PROJECT_ID

# Build the frontend
echo -e "${YELLOW}⚛️ Building React frontend...${NC}"
cd frontend
npm install
npm run build
cd ..

# Build and push the Docker image
echo -e "${YELLOW}🐳 Building Docker image...${NC}"
docker build -t $IMAGE_NAME .

echo -e "${YELLOW}📤 Pushing image to Google Container Registry...${NC}"
docker push $IMAGE_NAME

# Deploy to Cloud Run
echo -e "${YELLOW}☁️ Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 8080 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --concurrency 100 \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars "LANGFUSE_ENABLED=false" \
    --project $PROJECT_ID

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --format="value(status.url)")

echo ""
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo "=================================================="
echo -e "${GREEN}✅ Service URL: $SERVICE_URL${NC}"
echo -e "${GREEN}✅ Health Check: $SERVICE_URL/health${NC}"
echo -e "${GREEN}✅ API Docs: $SERVICE_URL/docs${NC}"
echo ""
echo -e "${BLUE}📝 Next Steps:${NC}"
echo "1. Test the API: curl $SERVICE_URL/health"
echo "2. Try a chat request: curl -X POST $SERVICE_URL/chat -H 'Content-Type: application/json' -d '{\"message\":\"How do I renew my visa?\",\"user_id\":\"test\"}'"
echo "3. View logs: gcloud logs read --project=$PROJECT_ID --filter=\"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\""
echo ""
echo -e "${YELLOW}💡 To enable full AI functionality:${NC}"
echo "   # Set up Google Cloud authentication for the service"
echo "   gcloud run services update $SERVICE_NAME --region=$REGION --project=$PROJECT_ID \\"
echo "     --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
echo ""
echo -e "${YELLOW}💡 To enable Langfuse observability:${NC}"
echo "   gcloud run services update $SERVICE_NAME --region=$REGION --project=$PROJECT_ID \\"
echo "     --set-env-vars LANGFUSE_ENABLED=true,LANGFUSE_SECRET_KEY=your-key,LANGFUSE_PUBLIC_KEY=your-key"
echo ""
echo -e "${BLUE}📋 Current Status:${NC}"
echo "   The service is running with a mock agent that provides helpful information"
echo "   about living in Japan without requiring AI services. This is perfect for"
echo "   demonstration and testing purposes."
