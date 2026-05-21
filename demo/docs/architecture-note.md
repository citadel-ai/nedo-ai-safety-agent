# Architecture Compatibility: ARM64 vs AMD64

Google Cloud Run only supports **AMD64/x86_64**. If you're on Apple Silicon (M1/M2/M3), Docker images default to ARM64 and must be cross-compiled.

## The Error

```
ERROR: Container manifest type 'application/vnd.oci.image.index.v1+json'
must support amd64/linux.
```

## Solution

Use the deployment script, which handles this automatically:

```bash
./deploy-to-cloud-run.sh
```

Or build manually for AMD64:

```bash
docker buildx build --platform linux/amd64 -t gcr.io/PROJECT_ID/SERVICE_NAME . --load
docker push gcr.io/PROJECT_ID/SERVICE_NAME
gcloud run deploy SERVICE_NAME --image gcr.io/PROJECT_ID/SERVICE_NAME --region REGION
```

## Local Testing vs Deployment

| Scenario | Command | Architecture |
|----------|---------|-------------|
| Local testing | `docker build -t APP .` | Native (ARM64 on Apple Silicon) |
| Cloud Run | `docker buildx build --platform linux/amd64 -t IMAGE . --load` | AMD64 |

## Troubleshooting

**"Cannot load build result"** -- create a new buildx builder:

```bash
docker buildx create --use --name multiarch --driver docker-container
docker buildx build --platform linux/amd64 -t IMAGE_NAME . --load
```

**Verify image architecture:**

```bash
docker inspect IMAGE_NAME | grep Architecture
# Expected: "Architecture": "amd64"
```
