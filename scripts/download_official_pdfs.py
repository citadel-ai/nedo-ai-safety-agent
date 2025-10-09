#!/usr/bin/env python3
"""
Automated PDF Downloader for Official Japanese Government Websites

This script searches Google for relevant PDF documents from official Japanese domains
and downloads them to docs_for_rag/ for RAG ingestion.

Supported domains:
- go.jp: Government
- ac.jp: Academic institutions
- ed.jp: Educational institutions
- lg.jp: Local governments
- or.jp: Non-profit organizations

Usage:
    python scripts/download_official_pdfs.py --categories immigration tax
    python scripts/download_official_pdfs.py --all
    python scripts/download_official_pdfs.py --dry-run
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, unquote

import aiohttp
from googleapiclient.discovery import build

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
OFFICIAL_DOMAINS = ["go.jp", "ac.jp", "ed.jp", "lg.jp", "or.jp"]
DOCS_DIR = Path("docs_for_rag")
DOWNLOAD_LOG = DOCS_DIR / "download_log.json"
MAX_PDFS_PER_CATEGORY = 10
MAX_FILE_SIZE_MB = 20
TIMEOUT_SECONDS = 30

# Topic categories and their search queries
SEARCH_TOPICS = {
    "immigration": [
        "visa renewal procedures 在留資格 更新",
        "residence card application 在留カード 申請",
        "work permit Japan 就労ビザ",
        "permanent residence application 永住権 申請",
        "status of residence 在留資格 種類",
        "immigration procedures 入国管理 手続き",
        "foreign national registration 外国人登録",
    ],
    "tax": [
        "income tax filing 所得税 申告",
        "resident tax payment 住民税 納付",
        "tax return guide 確定申告 ガイド",
        "tax deductions 控除 税金",
        "national pension 国民年金",
        "social insurance 社会保険",
        "year-end adjustment 年末調整",
    ],
    "healthcare": [
        "national health insurance 国民健康保険",
        "medical insurance enrollment 医療保険 加入",
        "hospital procedures 病院 手続き",
        "health checkup 健康診断",
        "prescription medication 処方箋",
        "emergency medical care 救急医療",
    ],
    "housing": [
        "rental contract guide 賃貸契約 ガイド",
        "moving procedures 引越し 手続き",
        "residence registration 住民登録",
        "housing assistance 住宅支援",
        "tenant rights 借主 権利",
    ],
    "employment": [
        "labor law Japan 労働法",
        "employment contract 雇用契約",
        "unemployment benefits 失業保険",
        "workers rights 労働者 権利",
        "workplace harassment ハラスメント 職場",
        "maternity leave 産休 育休",
    ],
}


@dataclass
class PDFMetadata:
    """Metadata for downloaded PDF."""
    url: str
    title: str
    domain: str
    category: str
    filename: str
    file_size: int
    download_date: str
    search_query: str
    sha256: str


class OfficialPDFDownloader:
    """Download PDFs from official Japanese government websites."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.max_pdfs_per_category = MAX_PDFS_PER_CATEGORY
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID")
        
        if not self.google_api_key or not self.google_cse_id:
            raise ValueError(
                "Missing Google API credentials. Set GOOGLE_API_KEY and GOOGLE_CSE_ID"
            )
        
        self.service = build("customsearch", "v1", developerKey=self.google_api_key)
        self.downloaded_urls: set[str] = set()
        self.download_log: list[PDFMetadata] = []
        self._load_existing_log()

    def _load_existing_log(self):
        """Load existing download log to avoid duplicates."""
        if DOWNLOAD_LOG.exists():
            try:
                with open(DOWNLOAD_LOG, "r", encoding="utf-8") as f:
                    log_data = json.load(f)
                    self.downloaded_urls = {item["url"] for item in log_data}
                    logger.info(f"📋 Loaded {len(self.downloaded_urls)} previously downloaded PDFs")
            except Exception as e:
                logger.warning(f"Failed to load download log: {e}")

    def _save_log(self):
        """Save download log."""
        if self.dry_run:
            return
        
        try:
            DOCS_DIR.mkdir(parents=True, exist_ok=True)
            with open(DOWNLOAD_LOG, "w", encoding="utf-8") as f:
                json.dump(
                    [asdict(item) for item in self.download_log],
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            logger.info(f"💾 Saved download log to {DOWNLOAD_LOG}")
        except Exception as e:
            logger.error(f"Failed to save download log: {e}")

    def _sanitize_filename(self, url: str, title: str) -> str:
        """Create a safe filename from URL and title."""
        # Try to extract filename from URL
        parsed = urlparse(url)
        url_filename = unquote(parsed.path.split("/")[-1])
        
        if url_filename.endswith(".pdf"):
            # Use URL filename if it's a PDF
            filename = url_filename
        else:
            # Create filename from title
            filename = re.sub(r"[^\w\s-]", "", title).strip()
            filename = re.sub(r"[-\s]+", "_", filename)
            filename = filename[:100]  # Limit length
            filename = f"{filename}.pdf"
        
        # Ensure unique filename by adding hash suffix if needed
        return filename

    def _get_domain_suffix(self, url: str) -> str | None:
        """Extract Japanese domain suffix (go.jp, ac.jp, etc.)."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            for suffix in OFFICIAL_DOMAINS:
                if domain.endswith(suffix):
                    return suffix
            
            return None
        except Exception:
            return None

    async def search_pdfs(
        self,
        query: str,
        category: str,
        num_results: int = 10
    ) -> list[dict[str, Any]]:
        """Search Google for PDFs matching the query."""
        results = []
        
        try:
            # Build search query with PDF filter and domain restrictions
            domain_filter = " OR ".join([f"site:{domain}" for domain in OFFICIAL_DOMAINS])
            search_query = f"{query} filetype:pdf ({domain_filter})"
            
            logger.info(f"🔍 Searching: {search_query[:100]}...")
            
            # Execute search
            response = self.service.cse().list(
                q=search_query,
                cx=self.google_cse_id,
                num=num_results,
            ).execute()
            
            items = response.get("items", [])
            logger.info(f"   Found {len(items)} results")
            
            for item in items:
                url = item.get("link", "")
                title = item.get("title", "Untitled")
                
                # Verify domain
                domain = self._get_domain_suffix(url)
                if not domain:
                    logger.debug(f"   ⏭️  Skipping non-official domain: {url}")
                    continue
                
                # Skip if already downloaded
                if url in self.downloaded_urls:
                    logger.debug(f"   ⏭️  Already downloaded: {title}")
                    continue
                
                results.append({
                    "url": url,
                    "title": title,
                    "domain": domain,
                    "category": category,
                    "search_query": query,
                })
            
        except Exception as e:
            logger.error(f"❌ Search failed for '{query}': {e}")
        
        return results

    async def download_pdf(
        self,
        pdf_info: dict[str, Any],
        session: aiohttp.ClientSession
    ) -> PDFMetadata | None:
        """Download a single PDF file."""
        url = pdf_info["url"]
        title = pdf_info["title"]
        category = pdf_info["category"]
        
        try:
            # Check if already downloaded
            if url in self.downloaded_urls:
                return None
            
            logger.info(f"📥 Downloading: {title[:80]}...")
            logger.info(f"   URL: {url}")
            
            if self.dry_run:
                logger.info("   [DRY RUN] Would download this PDF")
                return None
            
            # Download PDF
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)) as response:
                if response.status != 200:
                    logger.warning(f"   ❌ HTTP {response.status}: {url}")
                    return None
                
                # Check content type
                content_type = response.headers.get("Content-Type", "")
                if "pdf" not in content_type.lower():
                    logger.warning(f"   ❌ Not a PDF: {content_type}")
                    return None
                
                # Check file size
                content_length = response.headers.get("Content-Length")
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > MAX_FILE_SIZE_MB:
                        logger.warning(f"   ❌ File too large: {size_mb:.1f}MB")
                        return None
                
                # Read content
                content = await response.read()
                
                # Calculate hash
                sha256 = hashlib.sha256(content).hexdigest()
                
                # Create category directory
                category_dir = DOCS_DIR / category
                category_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate filename
                filename = self._sanitize_filename(url, title)
                filepath = category_dir / filename
                
                # Handle filename collision
                if filepath.exists():
                    base = filepath.stem
                    suffix = filepath.suffix
                    counter = 1
                    while filepath.exists():
                        filepath = category_dir / f"{base}_{counter}{suffix}"
                        counter += 1
                
                # Save PDF
                with open(filepath, "wb") as f:
                    f.write(content)
                
                file_size = len(content)
                logger.info(f"   ✅ Saved: {filepath.relative_to(DOCS_DIR)} ({file_size / 1024:.1f}KB)")
                
                # Create metadata
                metadata = PDFMetadata(
                    url=url,
                    title=title,
                    domain=pdf_info["domain"],
                    category=category,
                    filename=str(filepath.relative_to(DOCS_DIR)),
                    file_size=file_size,
                    download_date=datetime.now().isoformat(),
                    search_query=pdf_info["search_query"],
                    sha256=sha256,
                )
                
                self.downloaded_urls.add(url)
                self.download_log.append(metadata)
                
                return metadata
                
        except asyncio.TimeoutError:
            logger.warning(f"   ⏱️  Timeout: {url}")
        except Exception as e:
            logger.warning(f"   ❌ Download failed: {e}")
        
        return None

    async def download_category(
        self,
        category: str,
        queries: list[str],
    ) -> int:
        """Download PDFs for a specific category."""
        logger.info(f"\n{'='*80}")
        logger.info(f"📚 Category: {category.upper()}")
        logger.info(f"{'='*80}")
        
        all_pdfs = []
        
        # Search for PDFs using all queries
        for query in queries:
            pdfs = await self.search_pdfs(query, category, num_results=10)
            all_pdfs.extend(pdfs)
            
            # Rate limiting
            await asyncio.sleep(1)
        
        # Remove duplicates by URL
        unique_pdfs = {pdf["url"]: pdf for pdf in all_pdfs}.values()
        logger.info(f"\n📊 Found {len(unique_pdfs)} unique PDFs for {category}")
        
        # Limit to max PDFs
        pdfs_to_download = list(unique_pdfs)[:self.max_pdfs_per_category]
        
        if not pdfs_to_download:
            logger.info(f"   No new PDFs to download for {category}")
            return 0
        
        # Download PDFs
        logger.info(f"📥 Downloading up to {len(pdfs_to_download)} PDFs...\n")
        
        downloaded_count = 0
        async with aiohttp.ClientSession() as session:
            for pdf_info in pdfs_to_download:
                metadata = await self.download_pdf(pdf_info, session)
                if metadata:
                    downloaded_count += 1
                
                # Rate limiting
                await asyncio.sleep(2)
        
        logger.info(f"\n✅ Downloaded {downloaded_count} PDFs for {category}")
        return downloaded_count

    async def download_all(self, categories: list[str] | None = None):
        """Download PDFs for all or specific categories."""
        if categories is None:
            categories = list(SEARCH_TOPICS.keys())
        
        logger.info(f"🚀 Starting PDF download for categories: {', '.join(categories)}")
        logger.info(f"   Dry run: {self.dry_run}")
        logger.info(f"   Max PDFs per category: {self.max_pdfs_per_category}")
        logger.info(f"   Max file size: {MAX_FILE_SIZE_MB}MB")
        logger.info(f"   Official domains: {', '.join(OFFICIAL_DOMAINS)}")
        
        total_downloaded = 0
        
        for category in categories:
            if category not in SEARCH_TOPICS:
                logger.warning(f"⚠️  Unknown category: {category}")
                continue
            
            queries = SEARCH_TOPICS[category]
            count = await self.download_category(category, queries)
            total_downloaded += count
        
        # Save log
        self._save_log()
        
        # Summary
        logger.info(f"\n{'='*80}")
        logger.info(f"🎉 DOWNLOAD COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Total PDFs downloaded: {total_downloaded}")
        logger.info(f"Total PDFs in log: {len(self.download_log)}")
        logger.info(f"Download log: {DOWNLOAD_LOG}")
        logger.info(f"\n💡 Next steps:")
        logger.info(f"   1. Review downloaded PDFs in {DOCS_DIR}")
        logger.info(f"   2. Update {DOCS_DIR / 'README.md'} with new documents")
        logger.info(f"   3. Rebuild ChromaDB: ./scripts/rebuild_vectordb.sh")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download official Japanese government PDFs for RAG"
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=list(SEARCH_TOPICS.keys()) + ["all"],
        default=["all"],
        help="Categories to download (default: all)",
    )
    parser.add_argument(
        "--max-pdfs",
        type=int,
        default=MAX_PDFS_PER_CATEGORY,
        help=f"Max PDFs per category (default: {MAX_PDFS_PER_CATEGORY})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading",
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List available categories and exit",
    )
    
    args = parser.parse_args()
    
    # List categories
    if args.list_categories:
        print("\n📚 Available categories:")
        for category, queries in SEARCH_TOPICS.items():
            print(f"\n  {category}:")
            for query in queries[:3]:  # Show first 3 queries
                print(f"    - {query}")
            if len(queries) > 3:
                print(f"    ... and {len(queries) - 3} more queries")
        return
    
    # Determine categories
    categories = None
    if args.categories != ["all"]:
        categories = args.categories
    
    # Run downloader
    try:
        downloader = OfficialPDFDownloader(dry_run=args.dry_run)
        downloader.max_pdfs_per_category = args.max_pdfs
        asyncio.run(downloader.download_all(categories))
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Download interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Error: {e}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    main()

