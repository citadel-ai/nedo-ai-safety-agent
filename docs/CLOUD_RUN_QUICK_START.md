# Cloud Run Quick Start Guide

**Deploy to Google Cloud Run in 2 simple steps!**

## Prerequisites

- Google Cloud account with billing enabled
- `gcloud` CLI installed and authenticated: `gcloud auth login`
- Docker installed

## Step 1: Set Up Secrets (One-time Setup)

Run the interactive script to securely store your API keys in Google Cloud Secret Manager:

```bash
./setup-secrets.sh
```

This will prompt you for:
- `LANGFUSE_PUBLIC_KEY` (starts with `pk-`)
- `LANGFUSE_SECRET_KEY` (starts with `sk-`)
- `GOOGLE_PLACES_API_KEY` (optional)

**Why Secret Manager?**
- ✅ Secrets are encrypted at rest
- ✅ Fine-grained access control
- ✅ Automatic rotation support
- ✅ Audit logs of secret access
- ❌ NEVER put secrets in environment variables or git

## Step 2: Deploy to Cloud Run

Run the deployment script:

```bash
./deploy-to-cloud-run.sh
```

This will:
1. Build the Docker image
2. Push to Google Container Registry
3. Deploy to Cloud Run with:
   - 2GB memory, 1 CPU
   - Auto-scaling (0-10 instances)
   - Health checks enabled
   - Secrets mounted from Secret Manager

## That's It! 🎉

Your application will be live at a URL like:
```
https://japan-procedures-agent-xxxxx-uc.a.run.app
```

## Verify Deployment

```bash
# Get your service URL
SERVICE_URL=$(gcloud run services describe japan-procedures-agent --region us-central1 --format='value(status.url)')

# Test the health endpoint
curl ${SERVICE_URL}/api/health

# Expected response:
# {"status":"healthy","service":"japan_procedures_agent"}
```

## View Logs

```bash
# Real-time logs
gcloud run services logs tail japan-procedures-agent --region us-central1

# Recent logs
gcloud run services logs read japan-procedures-agent --region us-central1 --limit 50
```

## Update Your Application

To deploy code changes:

```bash
./deploy-to-cloud-run.sh
```

The script automatically:
- Rebuilds the Docker image
- Pushes the new version
- Updates Cloud Run (zero-downtime deployment)

## Environment Variables

### Non-Sensitive (set via `--set-env-vars`)
- `GOOGLE_CLOUD_PROJECT` - Your GCP project ID
- `VERTEX_AI_SEARCH_DATA_STORE_ID` - Vertex AI Search datastore
- `VERTEX_AI_SEARCH_ENGINE_ID` - Vertex AI Search engine
- `LANGFUSE_ENABLED` - Enable Langfuse tracing (true/false)
- `LANGFUSE_HOST` - Langfuse server URL

**Note**: The system automatically uses single-turn search for first queries and multi-turn answer method for follow-ups.

### Sensitive (set via `--set-secrets`)
- `LANGFUSE_PUBLIC_KEY` - From Secret Manager
- `LANGFUSE_SECRET_KEY` - From Secret Manager
- `GOOGLE_PLACES_API_KEY` - From Secret Manager

## Cost Estimates

Cloud Run charges only for:
- **CPU/Memory usage** during request processing
- **Number of requests**
- **Container Registry storage**

Estimated costs for moderate usage:
- **Free tier**: 2 million requests/month, 360,000 GB-seconds
- **After free tier**: ~$0.40 per million requests
- **Min instances = 0**: Scale to zero when idle = $0 cost when unused!

For production, set min-instances > 0 to avoid cold starts.

## Troubleshooting

### "Container manifest must support amd64/linux" Error

**Problem**: You're on Apple Silicon (M1/M2/M3) and the image was built for ARM64.

**Solution**: The deployment script automatically handles this. If you built manually:

```bash
# Rebuild for AMD64
docker buildx build --platform linux/amd64 -t gcr.io/PROJECT_ID/SERVICE_NAME . --load
docker push gcr.io/PROJECT_ID/SERVICE_NAME

# Or just use the script (recommended)
./deploy-to-cloud-run.sh
```

### Deployment Fails

```bash
# Check Cloud Run service status
gcloud run services describe japan-procedures-agent --region us-central1

# View error logs
gcloud run services logs read japan-procedures-agent --region us-central1 --limit 100
```

### Secrets Not Working

```bash
# List secrets
gcloud secrets list

# Check secret access
gcloud secrets describe langfuse-secret-key

# Verify service account has access
gcloud secrets get-iam-policy langfuse-secret-key
```

### Application Errors

```bash
# Follow logs in real-time
gcloud run services logs tail japan-procedures-agent --region us-central1

# Check health endpoint
curl https://YOUR-SERVICE-URL/api/health
```

## Security Best Practices

✅ **DO:**
- Use Secret Manager for all API keys and secrets
- Use the default Cloud Run service account or a custom one with minimal permissions
- Enable VPC connectors for accessing private resources
- Use Cloud Armor for DDoS protection (if public-facing)
- Implement authentication (remove `--allow-unauthenticated` for production)

❌ **DON'T:**
- Put secrets in `--set-env-vars`
- Commit `.env` files to git
- Use `--allow-unauthenticated` for sensitive applications
- Grant overly broad IAM permissions

## Advanced Configuration

### Custom Domain

```bash
gcloud run domain-mappings create --service japan-procedures-agent --domain your-domain.com --region us-central1
```

### Increase Resources

Edit `deploy-to-cloud-run.sh` and change:
```bash
--memory 4Gi \
--cpu 2 \
--min-instances 1 \  # Keep 1 instance warm
--max-instances 100 \
```

### VPC Access

```bash
# Create VPC connector
gcloud compute networks vpc-access connectors create my-connector \
  --region us-central1 \
  --range 10.8.0.0/28

# Add to deployment
--vpc-connector my-connector \
--vpc-egress all-traffic
```

## Monitoring

View metrics in Cloud Console:
1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
2. Click your service
3. Go to "Metrics" tab

Key metrics to watch:
- **Request count**: Track traffic patterns
- **Request latency**: Monitor performance
- **Container instance count**: Check scaling
- **Billable time**: Monitor costs

## Next Steps

- Set up Cloud Build for CI/CD automation
- Configure custom domain and SSL
- Set up Cloud Monitoring alerts
- Implement authentication with Identity Platform
- Add Cloud CDN for static assets

## Need Help?

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Detailed deployment guide

