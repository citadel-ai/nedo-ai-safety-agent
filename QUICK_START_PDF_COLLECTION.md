# 🚀 Quick Start: Automated PDF Collection

## What Was Created

Three new scripts to help you automatically collect official Japanese government PDFs:

### 1. **`scripts/download_official_pdfs.py`** 📥
The main Python script that searches and downloads PDFs from official Japanese domains.

### 2. **`scripts/collect_docs.sh`** 🎯
Interactive menu-driven wrapper for easy use (recommended for beginners).

### 3. **`scripts/rebuild_vectordb.sh`** 🔄
Helper to rebuild ChromaDB after adding new documents.

---

## 🎯 Easiest Way to Use (Interactive Menu)

```bash
# Run the interactive menu
./scripts/collect_docs.sh
```

You'll see:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📚 Official PDF Document Collector
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

What would you like to do?

  1) Download ALL categories (up to 50 PDFs each)
  2) Download IMMIGRATION documents only
  3) Download TAX documents only
  4) Download HEALTHCARE documents only
  5) Download HOUSING documents only
  6) Download EMPLOYMENT documents only
  7) Test run (5 PDFs per category, dry run)
  8) Custom (specify categories)
  9) List available categories
  0) Exit
```

---

## 📚 What It Searches For

The script targets **official Japanese domains**:

| Domain | Description |
|--------|-------------|
| `go.jp` | Government ministries and agencies |
| `ac.jp` | Academic institutions |
| `ed.jp` | Educational organizations |
| `lg.jp` | Local government offices |
| `or.jp` | Non-profit organizations |

### Categories & Topics

1. **Immigration** (7 search queries)
   - Visa renewal, residence cards, work permits, permanent residence

2. **Tax** (7 search queries)
   - Income tax, resident tax, tax returns, deductions, pension

3. **Healthcare** (6 search queries)
   - National health insurance, medical procedures, hospitals

4. **Housing** (5 search queries)
   - Rental contracts, moving procedures, residence registration

5. **Employment** (6 search queries)
   - Labor laws, employment contracts, unemployment benefits

---

## ⚙️ Setup (One-Time)

### Step 1: Get Google API Credentials

You need a Google Custom Search API key and CSE ID:

#### A. Get API Key
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable **Custom Search API**
3. Create credentials → API Key
4. Copy the API key

#### B. Create Custom Search Engine
1. Go to [Programmable Search Engine](https://programmablesearchengine.google.com/)
2. Create new search engine
3. Configure: Search entire web, Language: Japanese + English
4. Copy the **Search engine ID** (CSE ID)

### Step 2: Set Environment Variables

```bash
# Add to your .env file
echo 'GOOGLE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXX' >> .env
echo 'GOOGLE_CSE_ID=a1b2c3d4e5f6g7h8i' >> .env

# Or export temporarily
export GOOGLE_API_KEY="AIzaSyXXXXXXXXXXXXXXXXXX"
export GOOGLE_CSE_ID="a1b2c3d4e5f6g7h8i"
```

---

## 🚀 Usage Examples

### Example 1: Test Run (Preview)

```bash
# See what would be downloaded without actually downloading
uv run python scripts/download_official_pdfs.py --dry-run --max-pdfs 3
```

### Example 2: Download Immigration PDFs

```bash
# Download up to 50 immigration PDFs
uv run python scripts/download_official_pdfs.py --categories immigration
```

### Example 3: Download Multiple Categories

```bash
# Download immigration + tax PDFs
uv run python scripts/download_official_pdfs.py --categories immigration tax
```

### Example 4: Limit Number of PDFs

```bash
# Download only 10 PDFs per category
uv run python scripts/download_official_pdfs.py --max-pdfs 10
```

### Example 5: Download Everything

```bash
# Download all categories (up to 50 PDFs each)
uv run python scripts/download_official_pdfs.py
```

---

## 📁 What Happens After Download

### 1. PDFs are Organized by Category

```
docs_for_rag/
├── immigration/
│   ├── visa_renewal_guide_2024.pdf
│   ├── residence_card_procedures.pdf
│   └── work_permit_application.pdf
├── tax/
│   ├── income_tax_filing_guide.pdf
│   └── resident_tax_payment.pdf
└── ...
```

### 2. Download Log is Created

```
docs_for_rag/download_log.json
```

This tracks:
- URL of each PDF
- Title, domain, category
- File size, download date
- Search query used
- SHA256 hash (for integrity)

### 3. Rebuild Vector Database

```bash
# After downloading PDFs, rebuild ChromaDB
./scripts/rebuild_vectordb.sh
```

This:
- Clears old ChromaDB
- Ingests all PDFs from `docs_for_rag/`
- Creates embeddings
- Stores in ChromaDB

### 4. Test Your Chatbot

```bash
# Start server
uv run uvicorn app.server:app --reload

# Open browser: http://localhost:8000
# Ask: "How do I renew my visa in Japan?"
```

---

## 💡 Pro Tips

### Tip 1: Start Small
```bash
# Download just 5 PDFs per category to test
uv run python scripts/download_official_pdfs.py --max-pdfs 5
```

### Tip 2: Use Dry Run First
```bash
# Preview what will be downloaded
uv run python scripts/download_official_pdfs.py --dry-run
```

### Tip 3: Manage API Quota
- **Free tier**: 100 queries/day
- **1 full download** ≈ 50 queries
- Download 1-2 categories per day to stay within free tier

### Tip 4: Review Before Ingestion
```bash
# Check what was downloaded
ls -lh docs_for_rag/*/

# Open a few PDFs to verify quality
open docs_for_rag/immigration/*.pdf
```

### Tip 5: Avoid Duplicates
The script automatically tracks downloaded files in `download_log.json`.  
Re-running the script will skip already-downloaded PDFs.

---

## 🔧 Troubleshooting

### Error: "Missing Google API credentials"

```bash
# Check if environment variables are set
echo $GOOGLE_API_KEY
echo $GOOGLE_CSE_ID

# If empty, add them to .env or export them
export GOOGLE_API_KEY="your-key"
export GOOGLE_CSE_ID="your-cse-id"
```

### Error: "No results found"

- Check Google Custom Search quota (100/day free)
- Verify CSE ID is correct
- Try a smaller search first

### Too Many Duplicates

```bash
# Clear download log to start fresh
rm docs_for_rag/download_log.json

# Then download again
uv run python scripts/download_official_pdfs.py
```

### PDF Download Fails

- Some PDFs may be protected or require authentication
- Check file size limit (default: 20MB)
- Increase timeout in script if needed

---

## 📊 Expected Results

### Sample Output

```
🚀 Starting PDF download for categories: immigration
   Dry run: False
   Max PDFs per category: 50
   Max file size: 20MB
   Official domains: go.jp, ac.jp, ed.jp, lg.jp, or.jp

================================================================================
📚 Category: IMMIGRATION
================================================================================

🔍 Searching: visa renewal procedures 在留資格 更新 filetype:pdf...
   Found 10 results

🔍 Searching: residence card application 在留カード 申請 filetype:pdf...
   Found 8 results

📊 Found 45 unique PDFs for immigration

📥 Downloading up to 45 PDFs...

📥 Downloading: 在留資格更新申請ガイド...
   URL: https://www.moj.go.jp/isa/content/visa_guide.pdf
   ✅ Saved: immigration/visa_guide.pdf (1.2MB)

📥 Downloading: Residence Card Procedures...
   URL: https://www.isa.go.jp/en/publications/materials/residence_card.pdf
   ✅ Saved: immigration/residence_card.pdf (856KB)

...

✅ Downloaded 45 PDFs for immigration

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎉 DOWNLOAD COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total PDFs downloaded: 45
Total PDFs in log: 45
Download log: docs_for_rag/download_log.json

💡 Next steps:
   1. Review downloaded PDFs in docs_for_rag
   2. Update docs_for_rag/README.md with new documents
   3. Rebuild ChromaDB: ./scripts/rebuild_vectordb.sh
```

---

## 🔄 Complete Workflow

### Full Process from Start to Finish

```bash
# 1. Set up API credentials (one-time)
export GOOGLE_API_KEY="your-key"
export GOOGLE_CSE_ID="your-cse-id"

# 2. Test with dry run
uv run python scripts/download_official_pdfs.py --dry-run --max-pdfs 3

# 3. Download PDFs (start with one category)
uv run python scripts/download_official_pdfs.py --categories immigration --max-pdfs 10

# 4. Review downloads
ls -lh docs_for_rag/immigration/
cat docs_for_rag/download_log.json | jq '.[] | {title, filename}'

# 5. Rebuild vector database
./scripts/rebuild_vectordb.sh

# 6. Test chatbot
uv run uvicorn app.server:app --reload

# 7. Ask a question in the browser
# Example: "How do I renew my visa?"
```

---

## 📖 Additional Documentation

- **Full README**: `scripts/README_PDF_DOWNLOADER.md`
- **Vector DB Deployment**: `VECTOR_DB_DEPLOYMENT.md`
- **Document Inventory**: `docs_for_rag/README.md`

---

## 🎯 Next Steps

1. ✅ Set up Google API credentials
2. ✅ Run a test download (`--dry-run`)
3. ✅ Download one category
4. ✅ Review the PDFs
5. ✅ Rebuild ChromaDB
6. ✅ Test your chatbot
7. ✅ Gradually add more categories

---

**Happy collecting! 🎉**

Questions? Check `scripts/README_PDF_DOWNLOADER.md` for detailed documentation.

