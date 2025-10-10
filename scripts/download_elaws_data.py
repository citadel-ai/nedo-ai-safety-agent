#!/usr/bin/env python3
"""
Download structured legal data from e-Gov API

Uses e-Gov法令API to download Japanese laws and regulations in structured format.
This is superior to PDF scraping as it provides clean, structured text with hierarchy.

e-Gov API: https://elaws.e-gov.go.jp/
lawtext tool: https://github.com/yamachig/lawtext

Usage:
    python scripts/download_elaws_data.py --categories immigration
    python scripts/download_elaws_data.py --all
"""

import argparse
import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiohttp

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# e-Gov API endpoints
ELAWS_API_BASE = "https://elaws.e-gov.go.jp/api/1"
ELAWS_SEARCH_URL = f"{ELAWS_API_BASE}/lawlists"
ELAWS_LAWDATA_URL = f"{ELAWS_API_BASE}/lawdata"

DOCS_DIR = Path("docs_for_rag")

# Target laws and regulations for each category
TARGET_LAWS = {
    "immigration": [
        "出入国管理及び難民認定法",  # Immigration Control and Refugee Recognition Act
        "外国人の技能実習の適正な実施及び技能実習生の保護に関する法律",  # Technical Intern Training Act
        "出入国管理及び難民認定法施行規則",  # Immigration Act Enforcement Rules
    ],
    "tax": [
        "所得税法",  # Income Tax Act
        "地方税法",  # Local Tax Act
        "国税通則法",  # General Rules for National Taxes
        "租税特別措置法",  # Special Taxation Measures Act
    ],
    "healthcare": [
        "国民健康保険法",  # National Health Insurance Act
        "健康保険法",  # Health Insurance Act
        "医療法",  # Medical Care Act
    ],
    "housing": [
        "借地借家法",  # Land and Building Lease Act
        "住宅の品質確保の促進等に関する法律",  # Housing Quality Assurance Act
    ],
    "employment": [
        "労働基準法",  # Labor Standards Act
        "労働契約法",  # Labor Contract Act
        "雇用保険法",  # Employment Insurance Act
        "労働者派遣事業の適正な運営の確保及び派遣労働者の保護等に関する法律",  # Worker Dispatching Act
    ],
}


@dataclass
class LawMetadata:
    """Metadata for a law/regulation."""
    law_id: str
    law_number: str
    law_name: str
    law_name_kana: str | None
    promulgation_date: str | None
    category: str


class EGovLawDownloader:
    """Download structured legal data from e-Gov API."""

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None

    async def search_law(self, law_name: str) -> list[dict[str, Any]]:
        """Search for a law by name."""
        try:
            params = {"lawName": law_name}
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(ELAWS_SEARCH_URL, params=params) as response:
                if response.status != 200:
                    logger.warning(f"Search failed for '{law_name}': HTTP {response.status}")
                    return []
                
                # e-Gov API returns XML
                content = await response.text()
                
                # Parse XML response (simplified - would need proper XML parsing)
                # For now, just log that we got a response
                logger.debug(f"Got response for '{law_name}': {len(content)} bytes")
                
                # TODO: Parse XML and extract law IDs
                # For now, return empty list
                return []
        
        except Exception as e:
            logger.error(f"Error searching for '{law_name}': {e}")
            return []

    async def download_law(self, law_id: str, category: str) -> bool:
        """Download law text by ID."""
        try:
            params = {"lawId": law_id}
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(ELAWS_LAWDATA_URL, params=params) as response:
                if response.status != 200:
                    logger.warning(f"Download failed for law ID '{law_id}': HTTP {response.status}")
                    return False
                
                content = await response.text()
                
                # Save XML
                category_dir = DOCS_DIR / category / "structured_laws"
                category_dir.mkdir(parents=True, exist_ok=True)
                
                output_path = category_dir / f"{law_id}.xml"
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(content)
                
                logger.info(f"✅ Saved: {output_path.relative_to(DOCS_DIR)}")
                return True
        
        except Exception as e:
            logger.error(f"Error downloading law ID '{law_id}': {e}")
            return False

    async def close(self):
        """Close the session."""
        if self.session:
            await self.session.close()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download structured legal data from e-Gov API"
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=list(TARGET_LAWS.keys()) + ["all"],
        default=["all"],
        help="Categories to download",
    )
    
    args = parser.parse_args()
    
    categories = list(TARGET_LAWS.keys()) if args.categories == ["all"] else args.categories
    
    logger.info(f"🚀 Downloading structured legal data for: {', '.join(categories)}")
    logger.info("⚠️  NOTE: This is a prototype. Full implementation requires:")
    logger.info("   1. XML parsing (use xml.etree.ElementTree)")
    logger.info("   2. Law ID lookup from search results")
    logger.info("   3. Integration with lawtext for parsing")
    logger.info("   4. Consider using existing law databases")
    
    downloader = EGovLawDownloader()
    
    try:
        for category in categories:
            logger.info(f"\n📚 Category: {category.upper()}")
            law_names = TARGET_LAWS.get(category, [])
            
            for law_name in law_names:
                logger.info(f"🔍 Searching: {law_name}")
                results = await downloader.search_law(law_name)
                
                if results:
                    logger.info(f"   Found {len(results)} results")
                    # Download first result
                    # law_id = results[0]["law_id"]
                    # await downloader.download_law(law_id, category)
                else:
                    logger.info("   No results found")
                
                await asyncio.sleep(1)  # Rate limiting
    
    finally:
        await downloader.close()
    
    logger.info("\n💡 Next steps:")
    logger.info("   1. Implement XML parsing for e-Gov API responses")
    logger.info("   2. Consider using lawtext: https://github.com/yamachig/lawtext")
    logger.info("   3. Or use pre-processed databases like 日本法令データベース")


if __name__ == "__main__":
    asyncio.run(main())

