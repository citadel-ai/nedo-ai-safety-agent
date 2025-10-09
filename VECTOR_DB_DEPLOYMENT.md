# Vector Database Deployment Strategy

## 🎯 Overview

ChromaDB vector database should **NOT be committed to Git**. Instead, we build it from source documents that ARE version controlled.

---

## 📂 Project Structure

```
nedo-ai-safety-agent/
├── docs_for_rag/              ✅ Commit to Git
│   ├── README.md              # Document inventory
│   ├── immigration/
│   │   ├── visa_renewal_en.pdf
│   │   ├── visa_renewal_ja.pdf
│   │   └── residence_card.pdf
│   ├── tax/
│   ├── healthcare/
│   └── .gitkeep
├── scripts/
│   └── ingest_documents.py    ✅ Commit to Git
├── chroma_db/                 ❌ DON'T commit (.gitignore)
│   ├── chroma.sqlite3
│   └── collection_id/
└── .gitignore                 # chroma_db/ listed
```

---

## 🔄 Deployment Options

### Option 1: Build on Startup (Flexible) ⭐ RECOMMENDED for Dev

**When to use:**
- Development/testing
- Documents change frequently
- Small document set (<100 PDFs)

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy source documents
COPY docs_for_rag/ /app/docs_for_rag/
COPY scripts/ /app/scripts/

# Copy application
COPY app/ /app/app/
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN pip install uv && uv sync

# Build ChromaDB on container startup
CMD ["sh", "-c", "python scripts/ingest_documents.py && uvicorn app.server:app --host 0.0.0.0 --port 8080"]
```

**Startup time:** +30s-2min (depending on doc count)

---

### Option 2: Build During Docker Build (Fast Startup) ⭐⭐ RECOMMENDED for Production

**When to use:**
- Production deployments
- Documents don't change often
- Want fast startup

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync

# Copy source documents and scripts
COPY docs_for_rag/ /app/docs_for_rag/
COPY scripts/ /app/scripts/

# Build ChromaDB during image build (cached!)
RUN python scripts/ingest_documents.py

# Copy application code
COPY app/ /app/app/

# Start server immediately (ChromaDB ready)
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Startup time:** Instant! (ChromaDB pre-built)

**Image size:** +50-100MB (worth it!)

**Updating docs:** Rebuild Docker image

---

### Option 3: Cloud Storage + Download (Enterprise) 🏢

**When to use:**
- Very large document set (1000+ PDFs)
- Frequent updates
- Multiple environments
- Want to decouple docs from code

**Architecture:**
```
GCS Bucket: gs://nedo-helpdesk-docs/
├── documents/
│   ├── immigration/
│   └── tax/
└── vector_db/           # Pre-built ChromaDB
    └── chroma_db.tar.gz
```

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

# Install gcloud SDK
RUN apt-get update && apt-get install -y google-cloud-sdk

WORKDIR /app
COPY app/ /app/app/
COPY scripts/ /app/scripts/

# Download and extract ChromaDB on startup
CMD ["sh", "-c", "\
    gsutil -m rsync -r gs://nedo-helpdesk-docs/vector_db/ ./chroma_db/ && \
    uvicorn app.server:app --host 0.0.0.0 --port 8080"]
```

**Advantages:**
- Update docs without rebuilding
- Share DB across deployments
- Centralized management

---

## 📝 Document Management Best Practices

### Adding New Documents

```bash
# 1. Add PDF to docs_for_rag/
cp new_guide.pdf docs_for_rag/immigration/

# 2. Update docs inventory
echo "- new_guide.pdf - Immigration guide for students" >> docs_for_rag/README.md

# 3. Commit to Git
git add docs_for_rag/immigration/new_guide.pdf
git add docs_for_rag/README.md
git commit -m "Add student immigration guide"

# 4. Rebuild ChromaDB
python scripts/ingest_documents.py

# 5. Test
python -c "from app.real_vector_db import get_vector_db; print(get_vector_db().get_collection_info())"
```

### Updating Existing Documents

```bash
# 1. Replace file
cp updated_visa_guide.pdf docs_for_rag/immigration/visa_renewal.pdf

# 2. Clear ChromaDB
rm -rf chroma_db/

# 3. Rebuild
python scripts/ingest_documents.py

# 4. Commit changes
git add docs_for_rag/immigration/visa_renewal.pdf
git commit -m "Update visa renewal guide (2025 version)"
```

---

## 🐳 Docker Deployment Examples

### Development
```bash
# Build with startup ingestion
docker build -f Dockerfile.dev -t nedo-helpdesk:dev .
docker run -p 8080:8080 nedo-helpdesk:dev

# Startup time: ~2 minutes (builds ChromaDB)
```

### Production
```bash
# Build with pre-built ChromaDB
docker build -t nedo-helpdesk:prod .
docker run -p 8080:8080 nedo-helpdesk:prod

# Startup time: ~5 seconds (ChromaDB ready!)
```

### With Volume (Persistent DB)
```bash
# Use volume for ChromaDB
docker run -v $(pwd)/chroma_db:/app/chroma_db -p 8080:8080 nedo-helpdesk:prod

# ChromaDB persists across container restarts
```

---

## ☁️ Cloud Run Deployment

### Option 1: Baked-In ChromaDB

```bash
# Build image with ChromaDB
gcloud builds submit --tag gcr.io/PROJECT_ID/nedo-helpdesk

# Deploy
gcloud run deploy nedo-helpdesk \
  --image gcr.io/PROJECT_ID/nedo-helpdesk \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --timeout 300
```

### Option 2: GCS-Backed

```bash
# Upload docs to GCS
gsutil -m rsync -r docs_for_rag/ gs://PROJECT_ID-docs/

# Deploy with GCS Fuse
gcloud run deploy nedo-helpdesk \
  --image gcr.io/PROJECT_ID/nedo-helpdesk \
  --execution-environment gen2 \
  --add-volume name=docs,type=cloud-storage,bucket=PROJECT_ID-docs \
  --add-volume-mount volume=docs,mount-path=/app/docs_for_rag
```

---

## 🔄 Update Workflows

### Scenario 1: Add New Document

```bash
# Developer workflow:
1. Add PDF to docs_for_rag/
2. git commit
3. git push

# CI/CD builds new Docker image
# ChromaDB rebuilt with new document
# Deploy automatically
```

### Scenario 2: Emergency Document Update

```bash
# Without rebuilding Docker:

# 1. Update GCS bucket
gsutil cp updated_doc.pdf gs://PROJECT_ID-docs/immigration/

# 2. Rebuild ChromaDB
python scripts/rebuild_chroma_gcs.py

# 3. Upload to GCS
gsutil -m rsync -r chroma_db/ gs://PROJECT_ID-docs/vector_db/

# 4. Restart Cloud Run service (pulls new DB)
gcloud run services update nedo-helpdesk --region us-central1
```

---

## 📊 Size Estimates

### ChromaDB Size by Document Count

| Documents | Pages | Embeddings | ChromaDB Size | Git LFS Cost/mo |
|-----------|-------|------------|---------------|-----------------|
| 10 PDFs | 500 | 500 | ~5 MB | Free |
| 50 PDFs | 2,500 | 2,500 | ~25 MB | Free |
| 100 PDFs | 5,000 | 5,000 | ~50 MB | Free |
| 500 PDFs | 25,000 | 25,000 | ~250 MB | $5 |
| 1000 PDFs | 50,000 | 50,000 | ~500 MB | $5 |

**Storage breakdown:**
- SQLite metadata: ~1KB per document
- Vectors (768 dim): ~3KB per chunk
- HNSW index: ~30% overhead
- Total: ~5-10KB per chunk

---

## ⚠️ What NOT to Do

### ❌ Don't Commit ChromaDB to Git
```bash
# BAD: Direct commit
git add chroma_db/
git commit -m "Add vector database"
# → Binary files, merge conflicts, bloated repo
```

### ❌ Don't Share ChromaDB Files Directly
```bash
# BAD: Zip and share
tar -czf chroma_db.tar.gz chroma_db/
# Send to colleague
# → Version mismatch, sync issues, no audit trail
```

### ❌ Don't Mix Development and Production Data
```bash
# BAD: Same ChromaDB for dev and prod
# → Test data in production, confusion, errors
```

---

## ✅ Recommended Workflow

### Development
```bash
# Local development
1. Clone repo (includes docs_for_rag/)
2. python scripts/ingest_documents.py
3. Develop and test
4. ChromaDB in .gitignore (not committed)
```

### Staging
```bash
# Staging environment
1. Docker build (includes ingest step)
2. Deploy to staging Cloud Run
3. Test with production-like data
```

### Production
```bash
# Production deployment
1. Docker build (ChromaDB baked in)
2. Deploy to production Cloud Run
3. Fast startup, immutable
4. Update docs → rebuild image
```

---

## 🎯 Recommendation

**For Your Project:**

1. ✅ Keep docs in `docs_for_rag/` (commit to Git)
2. ✅ Add ChromaDB to `.gitignore`
3. ✅ Build ChromaDB during Docker build (fast startup)
4. ✅ For large updates: Use GCS + volume mount
5. ✅ Document inventory in `docs_for_rag/README.md`

**This gives you:**
- Version-controlled source documents
- Reproducible builds
- Fast deployments
- Easy collaboration
- No binary files in Git

---

## 📚 Additional Resources

- [ChromaDB Deployment Docs](https://docs.trychroma.com/deployment)
- [Cloud Run Volume Mounts](https://cloud.google.com/run/docs/configuring/services/cloud-storage-volume-mounts)
- [Git LFS](https://git-lfs.github.com/) (if you really need it)
- [Docker Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)

---

**Last Updated:** October 3, 2025  
**Status:** ✅ ChromaDB excluded from Git, built from source documents

