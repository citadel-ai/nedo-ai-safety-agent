# Automated PDF Downloader

This script automatically searches and downloads relevant PDF documents from official Japanese government websites for your RAG system.

## 🎯 What It Does

- **Searches Google** for PDFs from official Japanese domains
- **Filters** by domain type (go.jp, ac.jp, ed.jp, lg.jp, or.jp)
- **Downloads** PDFs to `docs_for_rag/` organized by category
- **Tracks** downloaded files to avoid duplicates
- **Logs** metadata for audit and management

## 🏛️ Supported Domains

| Domain | Type | Examples |
|--------|------|----------|
| `go.jp` | Government | Ministry websites, immigration services |
| `ac.jp` | Academic | Universities, research institutions |
| `ed.jp` | Educational | Schools, educational organizations |
| `lg.jp` | Local Government | City halls, prefectural offices |
| `or.jp` | Non-profit | NGOs, public service organizations |

## 📚 Categories

The script covers these topics:
- **Immigration**: Visa, residence cards, work permits
- **Tax**: Income tax, resident tax, deductions
- **Healthcare**: National health insurance, medical procedures
- **Housing**: Rental contracts, moving procedures
- **Employment**: Labor laws, employment contracts, benefits

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Ensure you have Google Custom Search API credentials
export GOOGLE_API_KEY="your-api-key"
export GOOGLE_CSE_ID="your-cse-id"
```

### 2. List Available Categories

```bash
python scripts/download_official_pdfs.py --list-categories
```

### 3. Dry Run (Preview)

```bash
# See what would be downloaded without actually downloading
python scripts/download_official_pdfs.py --dry-run
```

### 4. Download All Categories

```bash
# Download up to 50 PDFs per category
python scripts/download_official_pdfs.py
```

### 5. Download Specific Categories

```bash
# Download only immigration and tax PDFs
python scripts/download_official_pdfs.py --categories immigration tax

# Download only healthcare PDFs
python scripts/download_official_pdfs.py --categories healthcare
```

### 6. Limit Number of PDFs

```bash
# Download only 10 PDFs per category
python scripts/download_official_pdfs.py --max-pdfs 10
```

## 📖 Usage Examples

### Example 1: Quick Test
```bash
# Download 5 immigration PDFs as a test
python scripts/download_official_pdfs.py --categories immigration --max-pdfs 5
```

### Example 2: Full Download
```bash
# Download all categories with default limits
python scripts/download_official_pdfs.py
```

### Example 3: Update Existing Collection
```bash
# The script automatically skips already-downloaded files
python scripts/download_official_pdfs.py --categories immigration
```

### Example 4: Preview Before Download
```bash
# Dry run to see what would be downloaded
python scripts/download_official_pdfs.py --dry-run --categories tax healthcare
```

## 📁 Output Structure

After running, your `docs_for_rag/` directory will look like:

```
docs_for_rag/
├── README.md
├── download_log.json              # Audit log of all downloads
├── immigration/
│   ├── visa_renewal_guide_2024.pdf
│   ├── residence_card_procedures.pdf
│   └── work_permit_application.pdf
├── tax/
│   ├── income_tax_filing_guide.pdf
│   ├── resident_tax_payment.pdf
│   └── tax_deduction_handbook.pdf
├── healthcare/
│   ├── national_health_insurance_guide.pdf
│   └── hospital_procedures.pdf
├── housing/
│   └── rental_contract_guide.pdf
└── employment/
    ├── labor_law_handbook.pdf
    └── employment_rights.pdf
```

## 📊 Download Log

The script maintains `docs_for_rag/download_log.json` with metadata:

```json
[
  {
    "url": "https://www.moj.go.jp/isa/content/visa_guide.pdf",
    "title": "在留資格更新申請ガイド",
    "domain": "go.jp",
    "category": "immigration",
    "filename": "immigration/visa_guide.pdf",
    "file_size": 1048576,
    "download_date": "2025-10-08T17:30:00",
    "search_query": "visa renewal procedures 在留資格 更新",
    "sha256": "abc123..."
  }
]
```

## 🔧 Configuration

### Environment Variables

```bash
# Required
export GOOGLE_API_KEY="your-google-api-key"
export GOOGLE_CSE_ID="your-custom-search-engine-id"
```

### Script Constants

Edit `scripts/download_official_pdfs.py` to customize:

```python
MAX_PDFS_PER_CATEGORY = 50      # Max PDFs per category
MAX_FILE_SIZE_MB = 20           # Max file size (MB)
TIMEOUT_SECONDS = 30            # Download timeout
```

### Add Custom Search Queries

Edit `SEARCH_TOPICS` in the script:

```python
SEARCH_TOPICS = {
    "immigration": [
        "visa renewal procedures 在留資格 更新",
        "your custom query here",  # Add more
    ],
    # ...
}
```

## 🔍 Google Custom Search Setup

### 1. Get API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable **Custom Search API**
3. Create credentials (API Key)
4. Copy the API key

### 2. Create Custom Search Engine

1. Go to [Programmable Search Engine](https://programmablesearchengine.google.com/)
2. Click "Add" to create new search engine
3. Configure:
   - **Sites to search**: Leave empty (search entire web)
   - **Language**: Japanese + English
   - Enable "Search the entire web"
4. Copy the **Search engine ID** (CSE ID)

### 3. Set Environment Variables

```bash
# Add to your .env file
GOOGLE_API_KEY="AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
GOOGLE_CSE_ID="a1b2c3d4e5f6g7h8i"
```

## 🛠️ Troubleshooting

### Error: "Missing Google API credentials"

```bash
# Make sure environment variables are set
echo $GOOGLE_API_KEY
echo $GOOGLE_CSE_ID

# Or set them temporarily
export GOOGLE_API_KEY="your-key"
export GOOGLE_CSE_ID="your-cse-id"
```

### Error: "No results found"

- Check your Google Custom Search quota (100 queries/day free)
- Verify your CSE ID is correct
- Try a dry run first to see search results
- Check internet connectivity

### Error: "Download failed"

- Some PDFs may be protected or behind authentication
- Check file size limits (default: 20MB)
- Verify the URL is accessible in a browser
- Check download timeout (default: 30s)

### Too Many Duplicates

```bash
# Clear download log to start fresh
rm docs_for_rag/download_log.json

# Or manually edit the JSON file
```

## 📈 API Usage & Costs

### Google Custom Search API

- **Free Tier**: 100 queries/day
- **Paid Tier**: $5 per 1000 queries

### Estimated Usage

```
1 category = ~7 queries (7 search queries)
5 categories = ~35 queries
All categories = ~49 queries

You can run ~2 full downloads per day on free tier
```

### Optimize Usage

```bash
# Download one category at a time
python scripts/download_official_pdfs.py --categories immigration

# Wait a day, then download next category
python scripts/download_official_pdfs.py --categories tax
```

## 🔄 Workflow Integration

### Step 1: Download PDFs

```bash
python scripts/download_official_pdfs.py --categories immigration tax
```

### Step 2: Review Downloads

```bash
# Check what was downloaded
ls -lh docs_for_rag/*/

# Review download log
cat docs_for_rag/download_log.json | jq '.[] | {title, filename, file_size}'
```

### Step 3: Update Documentation

```bash
# Update docs_for_rag/README.md with new documents
vi docs_for_rag/README.md
```

### Step 4: Rebuild Vector Database

```bash
# Clear old ChromaDB
rm -rf chroma_db/

# Rebuild with new documents
python scripts/ingest_documents.py

# Or use the helper script
./scripts/rebuild_vectordb.sh
```

### Step 5: Test

```bash
# Start server
uv run uvicorn app.server:app --reload

# Test in browser
# Ask: "How do I renew my visa?"
```

## 🎯 Best Practices

### 1. Start Small

```bash
# Test with one category first
python scripts/download_official_pdfs.py --categories immigration --max-pdfs 5
```

### 2. Use Dry Run

```bash
# Always preview before large downloads
python scripts/download_official_pdfs.py --dry-run
```

### 3. Review Before Ingestion

- Manually check a few PDFs to ensure quality
- Remove any irrelevant or duplicate files
- Check for Japanese vs English versions

### 4. Manage API Quota

```bash
# Spread downloads over multiple days
# Day 1: immigration + tax
# Day 2: healthcare + housing
# Day 3: employment
```

### 5. Version Control

```bash
# Commit source PDFs to Git
git add docs_for_rag/immigration/*.pdf
git add docs_for_rag/download_log.json
git commit -m "Add immigration PDFs from official sources"

# But NOT the vector database
# (chroma_db/ is in .gitignore)
```

## 📝 Maintenance

### Update Search Queries

Edit the script to add more targeted queries:

```python
SEARCH_TOPICS = {
    "immigration": [
        "visa renewal procedures 在留資格 更新",
        "student visa application 留学ビザ 申請",  # Add this
        "working holiday visa ワーキングホリデー",  # And this
    ],
}
```

### Remove Outdated PDFs

```bash
# Check document dates
ls -lt docs_for_rag/immigration/

# Remove old documents (>2 years old)
find docs_for_rag/ -name "*.pdf" -mtime +730 -delete
```

### Re-download Category

```bash
# Remove category from log
jq 'del(.[] | select(.category == "immigration"))' docs_for_rag/download_log.json > temp.json
mv temp.json docs_for_rag/download_log.json

# Download fresh
python scripts/download_official_pdfs.py --categories immigration
```

## 🚀 Advanced Usage

### Custom Domains

Edit the script to add more domains:

```python
OFFICIAL_DOMAINS = [
    "go.jp",    # Government
    "ac.jp",    # Academic
    "ed.jp",    # Educational
    "lg.jp",    # Local government
    "or.jp",    # Non-profit
    "metro.tokyo.jp",  # Add specific sites
]
```

### Parallel Downloads

The script downloads sequentially to respect rate limits. For faster downloads (at your own risk):

```python
# In download_category(), use asyncio.gather()
tasks = [self.download_pdf(pdf, session) for pdf in pdfs_to_download]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### Integration with CI/CD

```yaml
# .github/workflows/update-docs.yml
name: Update RAG Documents

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:

jobs:
  download-pdfs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Download PDFs
        env:
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
          GOOGLE_CSE_ID: ${{ secrets.GOOGLE_CSE_ID }}
        run: |
          python scripts/download_official_pdfs.py --max-pdfs 10
      - name: Commit new PDFs
        run: |
          git add docs_for_rag/
          git commit -m "Update RAG documents [automated]"
          git push
```

## 📊 Statistics

After running, check statistics:

```bash
# Total PDFs
find docs_for_rag -name "*.pdf" | wc -l

# PDFs per category
for dir in docs_for_rag/*/; do
  echo "$(basename $dir): $(find $dir -name '*.pdf' | wc -l) PDFs"
done

# Total size
du -sh docs_for_rag/

# Average file size
find docs_for_rag -name "*.pdf" -exec ls -l {} \; | awk '{sum+=$5; count++} END {print "Average:", sum/count/1024, "KB"}'
```

## 🆘 Support

### Common Questions

**Q: Can I download PDFs from non-Japanese sites?**  
A: Yes, edit `OFFICIAL_DOMAINS` to include other domains.

**Q: How do I avoid duplicate downloads?**  
A: The script automatically tracks downloads in `download_log.json`.

**Q: Can I resume an interrupted download?**  
A: Yes, just run the script again. It will skip already-downloaded files.

**Q: How do I delete all downloads and start fresh?**  
A: Delete `download_log.json` and the category folders, then run again.

---

**Created:** October 8, 2025  
**Author:** NEDO AI Safety Agent Team  
**License:** Apache 2.0

