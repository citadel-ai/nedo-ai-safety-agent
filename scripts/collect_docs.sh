#!/bin/bash

# Quick wrapper script for PDF downloader
# Makes it easier to run common download tasks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  📚 Official PDF Document Collector${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check for API credentials
if [ -z "$GOOGLE_API_KEY" ] || [ -z "$GOOGLE_CSE_ID" ]; then
    echo -e "${RED}❌ Error: Google API credentials not found${NC}"
    echo ""
    echo "Please set the following environment variables:"
    echo "  export GOOGLE_API_KEY=\"your-api-key\""
    echo "  export GOOGLE_CSE_ID=\"your-cse-id\""
    echo ""
    echo "Or add them to your .env file:"
    echo "  echo 'GOOGLE_API_KEY=your-api-key' >> .env"
    echo "  echo 'GOOGLE_CSE_ID=your-cse-id' >> .env"
    echo ""
    exit 1
fi

# Show menu
echo "What would you like to do?"
echo ""
echo "  1) Download ALL categories (up to 50 PDFs each)"
echo "  2) Download IMMIGRATION documents only"
echo "  3) Download TAX documents only"
echo "  4) Download HEALTHCARE documents only"
echo "  5) Download HOUSING documents only"
echo "  6) Download EMPLOYMENT documents only"
echo "  7) Test run (5 PDFs per category, dry run)"
echo "  8) Custom (specify categories)"
echo "  9) List available categories"
echo "  0) Exit"
echo ""

read -p "Enter your choice [1-9, 0]: " choice

case $choice in
    1)
        echo -e "\n${YELLOW}📥 Downloading ALL categories...${NC}\n"
        python scripts/download_official_pdfs.py
        ;;
    2)
        echo -e "\n${YELLOW}📥 Downloading IMMIGRATION documents...${NC}\n"
        python scripts/download_official_pdfs.py --categories immigration
        ;;
    3)
        echo -e "\n${YELLOW}📥 Downloading TAX documents...${NC}\n"
        python scripts/download_official_pdfs.py --categories tax
        ;;
    4)
        echo -e "\n${YELLOW}📥 Downloading HEALTHCARE documents...${NC}\n"
        python scripts/download_official_pdfs.py --categories healthcare
        ;;
    5)
        echo -e "\n${YELLOW}📥 Downloading HOUSING documents...${NC}\n"
        python scripts/download_official_pdfs.py --categories housing
        ;;
    6)
        echo -e "\n${YELLOW}📥 Downloading EMPLOYMENT documents...${NC}\n"
        python scripts/download_official_pdfs.py --categories employment
        ;;
    7)
        echo -e "\n${YELLOW}🧪 Test run (dry run, 5 PDFs per category)...${NC}\n"
        python scripts/download_official_pdfs.py --max-pdfs 5 --dry-run
        ;;
    8)
        echo -e "\n${YELLOW}Available categories: immigration tax healthcare housing employment${NC}"
        read -p "Enter categories (space-separated): " categories
        echo -e "\n${YELLOW}📥 Downloading: $categories${NC}\n"
        python scripts/download_official_pdfs.py --categories $categories
        ;;
    9)
        echo ""
        python scripts/download_official_pdfs.py --list-categories
        echo ""
        exit 0
        ;;
    0)
        echo -e "\n${GREEN}👋 Goodbye!${NC}\n"
        exit 0
        ;;
    *)
        echo -e "\n${RED}❌ Invalid choice${NC}\n"
        exit 1
        ;;
esac

# If we got here, download completed
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅ Download Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "📊 Summary:"
echo "  Documents: $(find docs_for_rag -name '*.pdf' 2>/dev/null | wc -l) PDFs"
echo "  Total size: $(du -sh docs_for_rag 2>/dev/null | cut -f1)"
echo "  Download log: docs_for_rag/download_log.json"
echo ""
echo "💡 Next steps:"
echo "  1. Review downloaded PDFs:"
echo "     ls -lh docs_for_rag/*/"
echo ""
echo "  2. Update document inventory:"
echo "     vi docs_for_rag/README.md"
echo ""
echo "  3. Rebuild vector database:"
echo "     ./scripts/rebuild_vectordb.sh"
echo ""
echo "  4. Test your chatbot:"
echo "     uv run uvicorn app.server:app --reload"
echo ""

