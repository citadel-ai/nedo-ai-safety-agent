# Architecture Compatibility Note

## 🍎 Apple Silicon Users (M1/M2/M3)

**Important**: If you're on Apple Silicon, your Docker images are built for ARM64 by default, but **Google Cloud Run only supports AMD64/x86_64 architecture**.

## ⚠️ The Error You'll See

```
ERROR: Container manifest type 'application/vnd.oci.image.index.v1+json' 
must support amd64/linux.
```

## ✅ Solution: Use the Deployment Script

**The easiest solution** - our deployment script handles this automatically:

```bash
./deploy-to-cloud-run.sh
```

The script automatically builds for AMD64 using:
```bash
docker buildx build --platform linux/amd64 -t IMAGE_NAME . --load
```

## 🔧 Manual Build for AMD64

If you need to build manually:

```bash
# Build for AMD64 (Cloud Run compatible)
docker buildx build --platform linux/amd64 -t gcr.io/PROJECT_ID/SERVICE_NAME . --load

# Push to registry
docker push gcr.io/PROJECT_ID/SERVICE_NAME

# Deploy
gcloud run deploy SERVICE_NAME --image gcr.io/PROJECT_ID/SERVICE_NAME --region REGION
```

## 🏗️ How It Works

### Docker Buildx

Docker Buildx is a CLI plugin that extends Docker with multi-platform build capabilities:

- **ARM64** (Apple Silicon): Your Mac's native architecture
- **AMD64/x86_64**: Cloud Run's required architecture

The `--platform linux/amd64` flag tells Docker to build for AMD64 even on ARM64 machines.

### Cross-Platform Building

When you build for a different architecture:
- **Slower build**: Emulation is slower than native builds
- **Fully compatible**: The resulting image runs perfectly on AMD64 systems
- **Transparent**: Your code doesn't need any changes

## 📊 Architecture Comparison

| Platform | Your Mac | Cloud Run | Compatible? |
|----------|----------|-----------|-------------|
| ARM64 (Apple Silicon) | ✅ Native | ❌ Not supported | ❌ Won't run |
| AMD64/x86_64 | ⚠️ Emulated | ✅ Native | ✅ Will run |

## 🚀 Best Practices

### 1. **Always use the deployment script** for Cloud Run
```bash
./deploy-to-cloud-run.sh  # Handles architecture automatically
```

### 2. **Local testing** - use native architecture
```bash
docker build -t APP_NAME .  # Builds for your Mac (ARM64)
docker run -p 8080:8080 APP_NAME  # Runs natively, faster
```

### 3. **Cloud deployment** - use AMD64
```bash
docker buildx build --platform linux/amd64 -t IMAGE . --load  # Builds for Cloud Run
```

## 🛠️ Troubleshooting

### "Cannot load build result"

If you see this error:
```
ERROR: failed to solve: cannot load build result
```

Solution:
```bash
# Create a new buildx builder
docker buildx create --use --name multiarch --driver docker-container

# Rebuild
docker buildx build --platform linux/amd64 -t IMAGE_NAME . --load
```

### Verify Image Architecture

Check what architecture your image was built for:

```bash
docker inspect IMAGE_NAME | grep Architecture
```

Expected output for Cloud Run:
```json
"Architecture": "amd64"
```

## 📚 Additional Resources

- [Docker Buildx Documentation](https://docs.docker.com/buildx/working-with-buildx/)
- [Cloud Run Container Requirements](https://cloud.google.com/run/docs/container-contract)
- [Multi-platform Images](https://docs.docker.com/build/building/multi-platform/)

## 💡 Quick Fix Summary

**Problem**: Deployment fails with architecture error  
**Cause**: Image built for ARM64 (Apple Silicon)  
**Solution**: Run `./deploy-to-cloud-run.sh` (automatically builds for AMD64)  
**Manual Fix**: Add `--platform linux/amd64` to your Docker build command

