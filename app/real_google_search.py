"""Real Google Search implementation using multiple search APIs."""

import asyncio
import logging
import os
from typing import Any

import aiohttp

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class RealGoogleSearch:
    """Real Google Search implementation with multiple fallback options."""

    def __init__(self):
        logger.info("🔍 GOOGLE SEARCH INIT DEBUG - Initializing RealGoogleSearch:")

        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID")
        self.timeout = 10

        logger.info(f"   GOOGLE_API_KEY set: {bool(self.google_api_key)}")
        if self.google_api_key:
            logger.info(f"   GOOGLE_API_KEY length: {len(self.google_api_key)} chars")
            logger.info(f"   GOOGLE_API_KEY prefix: {self.google_api_key[:10]}...")

        logger.info(f"   GOOGLE_CSE_ID set: {bool(self.google_cse_id)}")
        if self.google_cse_id:
            logger.info(f"   GOOGLE_CSE_ID value: {self.google_cse_id}")

        logger.info(f"   Timeout: {self.timeout} seconds")

    async def search(
        self, query: str, num_results: int = 5, site_filter: str | None = None
    ) -> list[str]:
        """
        Perform Google search with fallback options.

        Args:
            query: Search query
            num_results: Number of results to return
            site_filter: Optional site filter (e.g., "site:gov.go.jp")

        Returns:
            List of search result snippets
        """
        # Debug: Log original input
        logger.info("🔍 GOOGLE SEARCH DEBUG - Original Input:")
        logger.info(f"   Query: '{query}'")
        logger.info(f"   Num results: {num_results}")
        logger.info(f"   Site filter: {site_filter}")

        # Add Japan-specific context to query
        enhanced_query = self._enhance_query_for_japan(query, site_filter)

        # Debug: Log enhanced query
        logger.info("🔍 GOOGLE SEARCH DEBUG - Enhanced Query:")
        logger.info(f"   Enhanced: '{enhanced_query}'")

        # Try different search methods in order of preference (no SerpAPI)
        search_methods = [
            self._search_with_google_custom_search,
            self._search_with_googlesearch_python,
            self._fallback_to_mock,
        ]

        logger.info("🔍 GOOGLE SEARCH DEBUG - Available Methods:")
        for i, method in enumerate(search_methods, 1):
            logger.info(f"   {i}. {method.__name__}")

        for method_num, method in enumerate(search_methods, 1):
            try:
                logger.info(
                    f"🔍 GOOGLE SEARCH DEBUG - Trying Method {method_num}: {method.__name__}"
                )
                results = await method(enhanced_query, num_results)

                # Debug: Log results
                logger.info(
                    f"🔍 GOOGLE SEARCH DEBUG - Method {method.__name__} Results:"
                )
                logger.info("   Success: True")
                logger.info(f"   Result count: {len(results)}")
                for i, result in enumerate(results[:3], 1):  # Show first 3 results
                    logger.info(
                        f"   Result {i}: {result[:100]}{'...' if len(result) > 100 else ''}"
                    )

                if results:
                    logger.info(
                        f"✅ Google search successful with {method.__name__}: {len(results)} results"
                    )
                    return results
                else:
                    logger.warning(f"⚠️ Method {method.__name__} returned empty results")

            except Exception as e:
                logger.warning(f"❌ Search method {method.__name__} failed: {e}")
                logger.info(
                    f"🔍 GOOGLE SEARCH DEBUG - Exception details: {type(e).__name__}: {e!s}"
                )
                continue

        # If all methods fail, return empty list
        logger.error("❌ All Google search methods failed")
        logger.info("🔍 GOOGLE SEARCH DEBUG - Final Output: Empty list")
        return []

    def _enhance_query_for_japan(
        self, query: str, site_filter: str | None = None
    ) -> str:
        """Enhance query with Japan-specific terms (site filters temporarily disabled for debugging)."""
        import logging

        logger = logging.getLogger(__name__)

        enhanced_query = query

        # TEMP: Disabled site filters - they're too restrictive and returning 0 results
        # Just add Japan context if needed
        if (
            "japan" not in query.lower()
            and "japanese" not in query.lower()
            and "日本" not in query
        ):
            enhanced_query = f"{enhanced_query} Japan"

        logger.info(f"🔍 _enhance_query_for_japan: '{query}' → '{enhanced_query}'")
        return enhanced_query

    async def _search_with_google_custom_search(
        self, query: str, num_results: int
    ) -> list[str]:
        """Search using Google Custom Search API."""
        logger.info("🔍 CSE DEBUG - Checking API configuration:")
        logger.info(f"   GOOGLE_API_KEY set: {bool(self.google_api_key)}")
        logger.info(f"   GOOGLE_CSE_ID set: {bool(self.google_cse_id)}")
        logger.info(f"   GOOGLE_CSE_ID value: {self.google_cse_id}")

        if not self.google_api_key or not self.google_cse_id:
            raise ValueError("GOOGLE_API_KEY or GOOGLE_CSE_ID not configured")

        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_api_key,
            "cx": self.google_cse_id,
            "q": f"{query} -filetype:pdf -filetype:xlsx -filetype:xls -filetype:doc -filetype:docx",  # Exclude document files
            "num": min(num_results, 10),  # API limit
            "gl": "jp",
            "hl": "en",
        }

        logger.info("🔍 CSE DEBUG - API Request:")
        logger.info(f"   URL: {url}")
        logger.info(f"   Query param: {params['q']}")
        logger.info(f"   Num results: {params['num']}")
        logger.info(f"   Location: {params['gl']}")
        logger.info(f"   Language: {params['hl']}")

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as session:
            async with session.get(url, params=params) as response:
                logger.info("🔍 CSE DEBUG - API Response:")
                logger.info(f"   Status: {response.status}")

                if response.status != 200:
                    response_text = await response.text()
                    logger.error(f"🔍 CSE DEBUG - Error Response Body: {response_text}")
                    raise Exception(f"Google CSE API returned status {response.status}")

                data = await response.json()
                logger.info("🔍 CSE DEBUG - Response Data:")
                logger.info(f"   Items count: {len(data.get('items', []))}")
                logger.info(f"   Search info: {data.get('searchInformation', {})}")

                snippets = []
                for i, item in enumerate(data.get("items", [])[:num_results]):
                    if "snippet" in item:
                        snippet = item["snippet"]
                        snippets.append(snippet)
                        logger.info(f"🔍 CSE DEBUG - Item {i + 1}:")
                        logger.info(f"   Title: {item.get('title', 'N/A')}")
                        logger.info(f"   Link: {item.get('link', 'N/A')}")
                        logger.info(
                            f"   Snippet: {snippet[:100]}{'...' if len(snippet) > 100 else ''}"
                        )

                logger.info(f"🔍 CSE DEBUG - Final snippets: {len(snippets)} items")
                return snippets

    async def _search_with_googlesearch_python(
        self, query: str, num_results: int
    ) -> list[str]:
        """Search using googlesearch-python library (free but rate-limited)."""
        logger.info("🔍 GOOGLESEARCH-PYTHON DEBUG - Starting search:")
        logger.info(f"   Query: {query}")
        logger.info(f"   Num results: {num_results}")

        try:
            from googlesearch import search

            logger.info("🔍 GOOGLESEARCH-PYTHON DEBUG - Package imported successfully")

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()

            logger.info("🔍 GOOGLESEARCH-PYTHON DEBUG - Executing search...")
            # Add document filtering to the query
            filtered_query = f"{query} -filetype:pdf -filetype:xlsx -filetype:xls -filetype:doc -filetype:docx"

            # Note: googlesearch-python doesn't return snippets directly
            # This is a simplified implementation
            urls = await loop.run_in_executor(
                None,
                lambda: list(
                    search(filtered_query, num_results=num_results, lang="en")
                ),
            )

            logger.info("🔍 GOOGLESEARCH-PYTHON DEBUG - Search completed:")
            logger.info(f"   URLs found: {len(urls)}")
            for i, url in enumerate(urls[:3], 1):  # Show first 3 URLs
                logger.info(f"   URL {i}: {url}")

            # For now, return the URLs as "snippets" - in a real implementation,
            # you'd want to fetch and extract snippets from these URLs
            snippets = [f"Search result: {url}" for url in urls[:num_results]]
            logger.info(
                f"🔍 GOOGLESEARCH-PYTHON DEBUG - Final snippets: {len(snippets)} items"
            )
            return snippets

        except ImportError as e:
            logger.error(f"🔍 GOOGLESEARCH-PYTHON DEBUG - Import error: {e}")
            raise ValueError("googlesearch-python package not installed")
        except Exception as e:
            logger.error(f"🔍 GOOGLESEARCH-PYTHON DEBUG - Search error: {e}")
            raise Exception(f"googlesearch-python search failed: {e}")

    async def _fallback_to_mock(self, query: str, num_results: int) -> list[str]:
        """Fallback to mock search results."""
        logger.info("🔍 MOCK FALLBACK DEBUG - Starting fallback:")
        logger.info(f"   Query: {query}")
        logger.info(f"   Num results: {num_results}")

        from app.vector_db import mock_google_search

        logger.warning("⚠️ Using mock Google search as fallback")
        logger.info("🔍 MOCK FALLBACK DEBUG - Calling mock_google_search function")

        # Run mock search in thread pool
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, mock_google_search, query)

        logger.info("🔍 MOCK FALLBACK DEBUG - Mock search results:")
        logger.info(f"   Raw results count: {len(results)}")
        for i, result in enumerate(results[:3], 1):  # Show first 3 results
            logger.info(
                f"   Mock result {i}: {result[:100]}{'...' if len(result) > 100 else ''}"
            )

        final_results = results[:num_results]
        logger.info(
            f"🔍 MOCK FALLBACK DEBUG - Final results: {len(final_results)} items"
        )
        return final_results


# Global instance
_google_search_instance: RealGoogleSearch | None = None


def get_google_search() -> RealGoogleSearch:
    """Get or create the global Google search instance."""
    global _google_search_instance

    if _google_search_instance is None:
        _google_search_instance = RealGoogleSearch()

    return _google_search_instance


async def real_google_search(query: str, num_results: int = 5) -> list[str]:
    """Perform real Google search."""
    logger.info("🔍 REAL_GOOGLE_SEARCH DEBUG - Entry point:")
    logger.info(f"   Query: '{query}'")
    logger.info(f"   Num results: {num_results}")

    search_engine = get_google_search()
    logger.info("🔍 REAL_GOOGLE_SEARCH DEBUG - Search engine initialized")

    results = await search_engine.search(query, num_results)

    logger.info("🔍 REAL_GOOGLE_SEARCH DEBUG - Final output:")
    logger.info(f"   Results count: {len(results)}")
    logger.info(f"   Results: {results}")

    return results


def get_search_config() -> dict[str, Any]:
    """Get current search configuration."""
    search_engine = get_google_search()
    return {
        "google_cse_configured": bool(
            search_engine.google_api_key and search_engine.google_cse_id
        ),
        "googlesearch_available": True,  # Always available as fallback
        "mock_fallback": True,
        "recommended_setup": "Use ADK's built-in google_search tool for better quality and no API costs",
    }
