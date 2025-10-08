"""
Enhanced Google Search with Full Content Extraction

This module extends the basic Google Search to fetch full page content
instead of just snippets, providing much richer information for RAG.
"""

import asyncio
import logging
import os
import re
from typing import Any
from urllib.parse import urlparse

import aiohttp
import trafilatura
from bs4 import BeautifulSoup

from app.real_google_search import RealGoogleSearch

logger = logging.getLogger(__name__)


class SearchResult:
    """Enhanced search result with full content."""

    def __init__(
        self,
        title: str,
        url: str,
        snippet: str,
        full_content: str | None = None,
        content_length: int = 0,
        extraction_success: bool = False,
        content_type: str = "unknown",
    ):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.full_content = full_content
        self.content_length = content_length
        self.extraction_success = extraction_success
        self.content_type = content_type

    def get_content_for_rag(self, max_length: int = 5000) -> str:
        """Get the best content for RAG, preferring full content over snippet."""
        if self.full_content and len(self.full_content) > len(self.snippet):
            content = self.full_content[:max_length]
            if len(self.full_content) > max_length:
                content += "... [content truncated]"
            return content
        return self.snippet

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/debugging."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet_length": len(self.snippet),
            "full_content_length": len(self.full_content) if self.full_content else 0,
            "extraction_success": self.extraction_success,
            "content_type": self.content_type,
        }


class EnhancedGoogleSearch(RealGoogleSearch):
    """Enhanced Google Search that fetches full page content."""

    def __init__(self):
        super().__init__()
        self.session_timeout = aiohttp.ClientTimeout(
            total=30
        )  # Longer timeout for content fetching
        self.max_content_length = 50000  # Max chars per page
        self.supported_content_types = {
            "text/html",
            "text/plain",
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        # Domain allowlist prioritized (suffix match). Avoid wildcard entries for suffix-check logic
        # TEMP: Disabled for debugging - allow all domains
        self.allowed_domains = set()  # Empty = allow all
        # self.allowed_domains = {'go.jp', 'ac.jp', 'ed.jp', 'lg.jp', 'or.jp'}
        # Simple in-memory TTL cache
        self._cache: dict[str, Any] = {}
        self._cache_ttl_seconds: int = int(
            os.getenv("ENHANCED_SEARCH_TTL_SECONDS", "900")
        )

    async def search_with_full_content(
        self,
        query: str,
        num_results: int = 5,
        site_filter: str | None = None,
        fetch_content: bool = True,
    ) -> list[SearchResult]:
        """
        Perform Google search and fetch full content from results.

        Args:
            query: Search query
            num_results: Number of results to return
            site_filter: Optional site filter
            fetch_content: Whether to fetch full page content

        Returns:
            List of SearchResult objects with full content
        """
        logger.info("🔍 ENHANCED SEARCH DEBUG - Starting enhanced search:")
        logger.info(f"   Query: '{query}'")
        logger.info(f"   Num results: {num_results}")
        logger.info(f"   Fetch content: {fetch_content}")

        # Simplified: bilingual CSE queries (EN + JA), no full-content fetch
        enhanced_query = self._enhance_query_for_japan(query, site_filter)
        logger.info(f"🔍 Enhanced query: '{query}' → '{enhanced_query}'")
        cache_key = f"bilingual|{enhanced_query}|{num_results}"
        # Return cached result if fresh
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            logger.info("🔍 ENHANCED SEARCH DEBUG - Cache hit")
            return cached

        # Run EN and JA structured searches
        logger.info("🔍 Calling EN search...")
        en_results = await self._get_structured_results(enhanced_query, num_results)
        logger.info(f"🔍 EN search returned: {len(en_results)} results")

        logger.info("🔍 Calling JA search...")
        ja_results = await self._get_structured_results_lang(
            enhanced_query, num_results, hl="ja", lr="lang_ja"
        )
        logger.info(f"🔍 JA search returned: {len(ja_results)} results")

        merged: list[SearchResult] = []
        seen = set()
        for r in en_results + ja_results:
            host = urlparse(r.url).hostname or ""
            if self.allowed_domains and not self._is_allowed_domain(host):
                logger.debug(f"🔍 Filtered out (domain): {r.url}")
                continue
            if r.url in seen:
                logger.debug(f"🔍 Filtered out (duplicate): {r.url}")
                continue
            seen.add(r.url)
            merged.append(r)
            logger.info(f"🔍 Added result: {r.title} - {r.url}")

        # Fetch full content if requested
        if fetch_content:
            logger.info(f"🔍 Fetching full content for {len(merged)} results...")
            content_tasks = [self._fetch_page_content(r) for r in merged[:num_results]]
            final_results = await asyncio.gather(*content_tasks)
            logger.info(f"🔍 Content fetch complete for {len(final_results)} results")
        else:
            final_results = merged[:num_results]
            logger.info(
                f"🔍 Returning {len(final_results)} results without content fetch"
            )

        self._set_cache(cache_key, final_results)
        return final_results

    async def _get_structured_results(
        self, query: str, num_results: int
    ) -> list[SearchResult]:
        """Get structured results with URLs and metadata from Google CSE."""
        try:
            if not self.google_api_key or not self.google_cse_id:
                logger.warning(
                    "Google CSE not configured, cannot get structured results"
                )
                return []

            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.google_api_key,
                "cx": self.google_cse_id,
                "q": query,
                "num": min(num_results, 10),
                "gl": "jp",
                "hl": "en",
            }

            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        error_body = await response.text()
                        logger.error(
                            f"❌ Google CSE API returned status {response.status}"
                        )
                        logger.error(f"❌ Error body: {error_body[:500]}")
                        return []

                    data = await response.json()

                    # DEBUG: Show raw response
                    if "items" not in data:
                        logger.warning(
                            f"⚠️ No 'items' in response. Keys: {list(data.keys())}"
                        )
                        if "error" in data:
                            logger.error(f"❌ API Error: {data['error']}")
                        return []

                    logger.info(f"✅ CSE returned {len(data.get('items', []))} items")

                    results = []
                    for item in data.get("items", [])[:num_results]:
                        result = SearchResult(
                            title=item.get("title", "No title"),
                            url=item.get("link", ""),
                            snippet=item.get("snippet", ""),
                            content_type="html",
                        )
                        results.append(result)

                        logger.info(f"🔍 STRUCTURED RESULT - {result.title}")
                        logger.info(f"   URL: {result.url}")
                        logger.info(f"   Snippet: {result.snippet[:100]}...")

                    return results

        except Exception as e:
            logger.error(f"Failed to get structured results: {e}")
            return []

    async def _get_structured_results_lang(
        self, query: str, num_results: int, hl: str = "ja", lr: str = "lang_ja"
    ) -> list[SearchResult]:
        """Get structured results with language hints (e.g., Japanese)."""
        try:
            if not self.google_api_key or not self.google_cse_id:
                logger.warning(
                    "Google CSE not configured, cannot get structured results"
                )
                return []
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.google_api_key,
                "cx": self.google_cse_id,
                "q": query,
                "num": min(num_results, 10),
                "gl": "jp",
                "hl": hl,
                "lr": lr,
                "safe": "active",
            }
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(
                            f"Google CSE API returned status {response.status}"
                        )
                        return []
                    data = await response.json()
                    results: list[SearchResult] = []
                    for item in data.get("items", [])[:num_results]:
                        results.append(
                            SearchResult(
                                title=item.get("title", "No title"),
                                url=item.get("link", ""),
                                snippet=item.get("snippet", ""),
                                content_type="html",
                            )
                        )
                    return results
        except Exception as e:
            logger.error(f"Failed to get structured results: {e}")
            return []

    async def _fetch_page_content(self, result: SearchResult) -> SearchResult:
        """Fetch full content from a search result URL."""
        logger.info(f"🔍 CONTENT FETCH DEBUG - Fetching: {result.url}")

        try:
            # Check if URL is valid
            parsed_url = urlparse(result.url)
            if not parsed_url.scheme or not parsed_url.netloc:
                logger.warning(f"Invalid URL: {result.url}")
                return result
            # Enforce domain allowlist
            hostname = parsed_url.hostname or ""
            if not self._is_allowed_domain(hostname):
                logger.info(
                    f"🔍 CONTENT FETCH DEBUG - Skipping non-allowed domain: {hostname}"
                )
                return result

            # Only extract HTML content - PDFs should go to vector DB
            if result.url.endswith(".pdf"):
                logger.info(
                    f"🔍 CONTENT FETCH DEBUG - Skipping PDF (should be in vector DB): {result.url}"
                )
                result.content_type = "pdf"
                result.full_content = f"PDF document: {result.title}\nURL: {result.url}\n[PDF content should be available in vector database]"
                result.extraction_success = True
                result.content_length = len(result.full_content)

                logger.info("📄 PDF reference created:")
                logger.info(f"   Title: {result.title}")
                logger.info(f"   URL: {result.url}")
                logger.info("   Note: Content should be in vector database")
            else:
                content = await self._extract_html_content(result.url)
                result.content_type = "html"

                if content:
                    result.full_content = content[: self.max_content_length]
                    result.content_length = len(content)
                    result.extraction_success = True

                    logger.info("✅ HTML content extracted successfully:")
                    logger.info(f"   Length: {result.content_length} chars")
                    logger.info(f"   Type: {result.content_type}")
                    logger.info(f"   Preview: {content[:200]}...")
                else:
                    logger.warning(f"⚠️ No HTML content extracted from {result.url}")
                    result.extraction_success = False

            return result

        except Exception as e:
            logger.error(f"❌ Failed to fetch content from {result.url}: {e}")
            result.extraction_success = False
            return result

    async def _extract_html_content(self, url: str) -> str | None:
        """Extract clean text content from HTML page."""
        try:
            # Use aiohttp for async HTTP request
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }

                async with session.get(url, headers=headers) as response:
                    if response.status == 403:
                        logger.warning(
                            f"HTTP 403 (Forbidden) for {url} - Site blocking access, using snippet instead"
                        )
                        return f"Content from {url} is not accessible due to access restrictions. Please visit the site directly for full information."
                    elif response.status != 200:
                        logger.warning(f"HTTP {response.status} for {url}")
                        return f"Content from {url} could not be retrieved (HTTP {response.status}). Please visit the site directly."

                    # Check content type
                    content_type = response.headers.get("content-type", "").lower()
                    if not any(
                        ct in content_type for ct in ["text/html", "text/plain"]
                    ):
                        logger.warning(f"Unsupported content type: {content_type}")
                        return None

                    html_content = await response.text()

            # Use trafilatura for clean text extraction (best for news/articles)
            extracted_text = trafilatura.extract(html_content)

            if extracted_text and len(extracted_text.strip()) > 100:
                return extracted_text.strip()

            # Fallback to BeautifulSoup if trafilatura fails
            logger.info("Trafilatura failed, trying BeautifulSoup fallback")
            return self._extract_with_beautifulsoup(html_content)

        except TimeoutError:
            logger.warning(f"Timeout fetching {url}")
            return None
        except Exception as e:
            logger.error(f"Error extracting HTML from {url}: {e}")
            return None

    def _extract_with_beautifulsoup(self, html_content: str) -> str | None:
        """Fallback content extraction using BeautifulSoup."""
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()

            # Try to find main content areas
            main_content = None
            for selector in [
                "main",
                "article",
                ".content",
                "#content",
                ".main",
                "#main",
            ]:
                main_content = soup.select_one(selector)
                if main_content:
                    break

            if not main_content:
                main_content = soup.body or soup

            # Extract text
            text = main_content.get_text(separator=" ", strip=True)

            # Clean up whitespace
            text = re.sub(r"\s+", " ", text)
            text = re.sub(r"\n\s*\n", "\n\n", text)

            return text.strip() if len(text.strip()) > 100 else None

        except Exception as e:
            logger.error(f"BeautifulSoup extraction failed: {e}")
            return None

    # ----------------------
    # Internal helpers: cache and allowlist
    # ----------------------
    def _is_allowed_domain(self, hostname: str) -> bool:
        try:
            # If no allowed domains specified, allow all
            if not self.allowed_domains:
                return True
            # Allow subdomains of allowed domains
            return any(
                hostname == d or hostname.endswith("." + d)
                for d in self.allowed_domains
            )
        except Exception:
            return False

    def _get_from_cache(self, key: str) -> list[SearchResult] | None:
        entry = self._cache.get(key)
        if not entry:
            return None
        value, expiry = entry
        if expiry < asyncio.get_event_loop().time():
            self._cache.pop(key, None)
            return None
        return value

    def _set_cache(self, key: str, value: list[SearchResult]) -> None:
        expiry = asyncio.get_event_loop().time() + self._cache_ttl_seconds
        self._cache[key] = (value, expiry)

    # PDF extraction removed - PDFs should be processed offline and stored in vector DB


# Global instance
_enhanced_search_instance: EnhancedGoogleSearch | None = None


def get_enhanced_google_search() -> EnhancedGoogleSearch:
    """Get the global enhanced Google search instance."""
    global _enhanced_search_instance

    if _enhanced_search_instance is None:
        _enhanced_search_instance = EnhancedGoogleSearch()

    return _enhanced_search_instance


async def enhanced_google_search(
    query: str, num_results: int = 5, fetch_full_content: bool = True
) -> list[str]:
    """
    Perform enhanced Google search with full content extraction.

    Args:
        query: Search query
        num_results: Number of results to return
        fetch_full_content: Whether to fetch full page content

    Returns:
        List of content strings (full content or snippets)
    """
    search_engine = get_enhanced_google_search()
    results = await search_engine.search_with_full_content(
        query, num_results, fetch_content=fetch_full_content
    )

    # Convert SearchResult objects to strings for compatibility
    content_list = []
    for result in results:
        content = result.get_content_for_rag()
        # Add metadata for better context
        if result.extraction_success and result.full_content:
            content = f"Source: {result.title} ({result.url})\n\n{content}"
        content_list.append(content)

    return content_list


async def get_enhanced_search_results(
    query: str, num_results: int = 5
) -> list[SearchResult]:
    """
    Get enhanced search results as SearchResult objects for detailed analysis.

    Returns:
        List of SearchResult objects with full metadata
    """
    search_engine = get_enhanced_google_search()
    return await search_engine.search_with_full_content(query, num_results)
