# 🚀 Japan Helpdesk - Cloud Run Deployment Guide

This guide will help you deploy the Japan Helpdesk system to Google Cloud Run for production use.

## 📋 Prerequisites

### Required Tools
- **Google Cloud SDK** (`gcloud`) - [Install Guide](https://cloud.google.com/sdk/docs/install)
- **Docker** - [Install Guide](https://docs.docker.com/get-docker/)
- **Node.js 18+** - [Install Guide](https://nodejs.org/)

### Google Cloud Setup
1. **Create a Google Cloud Project** or use an existing one
2. **Enable billing** for your project
3. **Authenticate with gcloud**:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

## 🚀 Quick Deployment

### Option 1: Automated Deployment Script

```bash
# Set your project ID
export GOOGLE_CLOUD_PROJECT=your-project-id

# Run the deployment script
./deploy.sh
```

### Option 2: Manual Deployment

1. **Enable required APIs**:
   ```bash
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable run.googleapis.com
   gcloud services enable containerregistry.googleapis.com
   ```

2. **Build the Docker image**:
   ```bash
   docker build -t gcr.io/$GOOGLE_CLOUD_PROJECT/japan-helpdesk .
   docker push gcr.io/$GOOGLE_CLOUD_PROJECT/japan-helpdesk
   ```

3. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy japan-helpdesk \
     --image gcr.io/$GOOGLE_CLOUD_PROJECT/japan-helpdesk \
     --platform managed \
     --region us-central1 \
     --port 8080 \
     --memory 2Gi \
     --cpu 2 \
     --timeout 300 \
     --concurrency 100 \
     --min-instances 0 \
     --max-instances 10 \
     --set-env-vars "LANGFUSE_ENABLED=false" \
     --no-invoker-iam-check
   ```

   **Alternative**: If you need to enable public access after deployment:
   ```bash
   gcloud run services update japan-helpdesk \
     --region=us-central1 \
     --no-invoker-iam-check
   ```

   For more details, see the [Cloud Run public access documentation](https://cloud.google.com/run/docs/authenticating/public#disable_invoker).

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GOOGLE_CLOUD_PROJECT` | Your Google Cloud project ID | - | Yes |
| `LANGFUSE_ENABLED` | Enable Langfuse observability | `false` | No |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key | - | No* |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | - | No* |
| `LANGFUSE_HOST` | Langfuse instance URL | `https://cloud.langfuse.com` | No |
| `VERTEX_AI_LOCATION` | Vertex AI region | `us-central1` | No |
| `MODEL_NAME` | LLM model to use | `gemini-2.5-flash` | No |

*Required only if `LANGFUSE_ENABLED=true`

### Resource Configuration

The deployment uses the following Cloud Run settings:
- **Memory**: 2 GiB
- **CPU**: 2 vCPU
- **Timeout**: 300 seconds (5 minutes)
- **Concurrency**: 100 requests per instance
- **Min Instances**: 0 (scales to zero)
- **Max Instances**: 10

## 🔍 Observability Setup

### Enable Langfuse (Optional)

1. **Sign up for Langfuse**: [langfuse.com](https://langfuse.com)
2. **Get your API keys** from the Langfuse dashboard
3. **Update environment variables**:
   ```bash
   gcloud run services update japan-helpdesk \
     --region us-central1 \
     --set-env-vars \
     LANGFUSE_ENABLED=true,\
     LANGFUSE_SECRET_KEY=your-secret-key,\
     LANGFUSE_PUBLIC_KEY=your-public-key
   ```

### Google Cloud Monitoring

Cloud Run automatically provides:
- **Request metrics** (latency, error rate, request count)
- **Resource metrics** (CPU, memory usage)
- **Logs** (application and system logs)

Access via: [Google Cloud Console > Cloud Run > japan-helpdesk > Metrics](https://console.cloud.google.com/run)

## 🧪 Testing the Deployment

### Health Check
```bash
SERVICE_URL=$(gcloud run services describe japan-helpdesk --region=us-central1 --format="value(status.url)")
curl $SERVICE_URL/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0", 
  "workflow_type": "langgraph-mock"
}
```

### API Test
```bash
curl -X POST $SERVICE_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"How do I renew my student visa?","user_id":"test"}'
```

Expected response: Detailed visa renewal information with mock agent disclaimer.

### Frontend Test
Open your browser and navigate to the service URL to access the React frontend.

### Mock Agent Behavior
The deployed service initially runs with a **mock agent** that:
- ✅ Provides helpful information about living in Japan
- ✅ Responds to common queries (visa, work, healthcare)
- ✅ Works without Google Cloud credentials
- ✅ Perfect for demonstration and testing
- ⚠️ Does not use real AI models (clearly indicated in responses)

## 📊 Monitoring & Debugging

### View Logs
```bash
# Real-time logs
gcloud logs tail --project=$GOOGLE_CLOUD_PROJECT \
  --filter="resource.type=cloud_run_revision AND resource.labels.service_name=japan-helpdesk"

# Historical logs
gcloud logs read --project=$GOOGLE_CLOUD_PROJECT \
  --filter="resource.type=cloud_run_revision AND resource.labels.service_name=japan-helpdesk" \
  --limit=100
```

### Performance Monitoring
- **Latency**: Monitor P95 response times in Cloud Console
- **Error Rate**: Track 4xx/5xx responses
- **Memory Usage**: Ensure memory usage stays below 2 GiB
- **CPU Usage**: Monitor CPU utilization

### Common Issues

1. **Cold Start Latency**: First request may take 10-30 seconds
   - **Solution**: Consider setting `min-instances=1` for production
   
2. **Memory Issues**: Large models may cause OOM errors
   - **Solution**: Increase memory to 4 GiB or 8 GiB
   
3. **Timeout Errors**: Complex queries may exceed 300s timeout
   - **Solution**: Increase timeout or optimize workflow

## 🔄 CI/CD Pipeline

For automated deployments, consider setting up:

1. **Cloud Build** for automatic builds on git push
2. **Cloud Deploy** for staged rollouts
3. **GitHub Actions** for external CI/CD

Example Cloud Build configuration:
```yaml
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-t', 'gcr.io/$PROJECT_ID/japan-helpdesk', '.']
- name: 'gcr.io/cloud-builders/docker'
  args: ['push', 'gcr.io/$PROJECT_ID/japan-helpdesk']
- name: 'gcr.io/cloud-builders/gcloud'
  args: ['run', 'deploy', 'japan-helpdesk', 
         '--image', 'gcr.io/$PROJECT_ID/japan-helpdesk',
         '--region', 'us-central1',
         '--platform', 'managed']
```

## 🔒 Security Considerations

### Authentication
- The service is deployed with `--allow-unauthenticated` for demo purposes
- For production, consider using Cloud IAM or Firebase Auth

### Network Security
- Cloud Run provides HTTPS by default
- Consider using Cloud Armor for DDoS protection
- Use VPC connectors for private resource access

### Data Privacy
- All data is processed in Google Cloud
- No user data is stored persistently (stateless design)
- Consider data residency requirements for your use case

## 💰 Cost Optimization

### Pricing Factors
- **CPU time**: Charged per vCPU-second
- **Memory time**: Charged per GiB-second  
- **Requests**: Charged per million requests
- **Networking**: Egress charges apply

### Optimization Tips
1. **Scale to zero**: Default configuration scales to 0 instances
2. **Right-size resources**: Monitor and adjust CPU/memory
3. **Optimize cold starts**: Consider keeping 1 warm instance
4. **Use regional deployment**: Avoid cross-region charges

## 📚 Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Langfuse Documentation](https://langfuse.com/docs)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)

---

**🎉 Your Japan Helpdesk system is now ready for production use on Google Cloud Run!**
