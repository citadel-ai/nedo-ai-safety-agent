# RAG Documents Inventory

This directory contains source documents that are ingested into the ChromaDB vector database for Retrieval-Augmented Generation (RAG).

## 📁 Current Documents

### Immigration
- `test_asei.txt` - Test document for ASEI (currently for testing)

### Status
**Total Documents:** 1  
**Last Updated:** October 3, 2025

---

## 📝 Adding New Documents

### Step 1: Add Document
```bash
# Place PDF in appropriate category folder
cp your_document.pdf docs_for_rag/immigration/
```

### Step 2: Update This README
```markdown
### Immigration
- `test_asei.txt` - Test document for ASEI
- `your_document.pdf` - Brief description here
```

### Step 3: Rebuild ChromaDB
```bash
# Clear existing database
rm -rf chroma_db/

# Rebuild from all documents
python scripts/ingest_documents.py

# Verify
python -c "from app.real_vector_db import get_vector_db; print(get_vector_db().get_collection_info())"
```

### Step 4: Commit to Git
```bash
git add docs_for_rag/immigration/your_document.pdf
git add docs_for_rag/README.md
git commit -m "Add immigration document: your_document.pdf"
git push
```

---

## 📂 Recommended Folder Structure

```
docs_for_rag/
├── README.md (this file)
├── immigration/
│   ├── visa_renewal_en.pdf
│   ├── visa_renewal_ja.pdf
│   ├── residence_card_en.pdf
│   └── work_permit.pdf
├── tax/
│   ├── income_tax_guide.pdf
│   ├── resident_tax.pdf
│   └── nenkin_pension.pdf
├── healthcare/
│   ├── national_health_insurance.pdf
│   └── hospital_guide.pdf
├── housing/
│   ├── rental_contract_guide.pdf
│   └── moving_procedures.pdf
└── employment/
    ├── labor_laws.pdf
    └── unemployment_benefits.pdf
```

---

## 🎯 Document Guidelines

### What to Include ✅
- Official government documents (translated if available)
- Multilingual guides (English + Japanese)
- Step-by-step procedures
- Recent updates (within last 2 years)
- Frequently asked questions from users

### What NOT to Include ❌
- Copyrighted materials without permission
- Personal information
- Outdated documents (>3 years old)
- Duplicate content
- Very large files (>50MB per PDF)

---

## 🔄 Document Sources

### Recommended Official Sources
1. **Immigration Services Agency of Japan**
   - https://www.isa.go.jp/en/
   - Visa procedures, status of residence

2. **Ministry of Health, Labour and Welfare**
   - https://www.mhlw.go.jp/english/
   - Healthcare, labor laws, pensions

3. **National Tax Agency**
   - https://www.nta.go.jp/english/
   - Tax filing, deductions

4. **Local Government Websites**
   - Tokyo, Osaka, Fukuoka city guides
   - Ward office procedures

5. **CLAIR (Council of Local Authorities for International Relations)**
   - http://www.clair.or.jp/e/
   - Life in Japan guides

---

## 📊 Current Status

| Category | Documents | Status |
|----------|-----------|--------|
| Immigration | 1 (test) | 🚧 Need more |
| Tax | 0 | ❌ Empty |
| Healthcare | 0 | ❌ Empty |
| Housing | 0 | ❌ Empty |
| Employment | 0 | ❌ Empty |

**Total:** 1 document (test only)

---

## 🎯 Next Steps

1. ✅ Create category folders
2. ⏳ Gather official government PDFs
3. ⏳ Add multilingual documents (EN + JP)
4. ⏳ Update ingestion script if needed
5. ⏳ Test hybrid search with real documents

---

## 🔧 Technical Details

### Document Processing
- **Tool:** `scripts/ingest_documents.py`
- **Chunking:** RecursiveCharacterTextSplitter (chunk_size=1000, overlap=200)
- **Embeddings:** Google Gecko (text-embedding-004) or Sentence Transformers
- **Storage:** ChromaDB (local vector database)

### File Format Support
- ✅ PDF (recommended)
- ✅ TXT (plain text)
- ⏳ DOCX (requires python-docx)
- ⏳ HTML (requires beautifulsoup4)

---

## 🐛 Troubleshooting

### Error: "No documents found in docs_for_rag/"
```bash
# Check if documents exist
ls -R docs_for_rag/

# Make sure they're not in .gitignore
cat .gitignore | grep docs_for_rag
```

### Error: "Failed to load PDF"
```bash
# Install PDF support
pip install pypdf

# Or use uv
uv pip install pypdf
```

### Error: "ChromaDB collection already exists"
```bash
# Clear ChromaDB
rm -rf chroma_db/

# Rebuild
python scripts/ingest_documents.py
```

---

**Maintained by:** NEDO AI Safety Agent Team  
**Contact:** [Your contact info]  
**Last Review:** October 3, 2025

