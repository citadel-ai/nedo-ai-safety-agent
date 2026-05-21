"""Google Maps search tool via Vertex AI's Maps grounding.

Wraps ``google.genai.Client`` behind a standard LangChain ``BaseTool`` so
the places-finding node can call it like any other tool.

Note: the ``us-central1`` region is required for Maps grounding to return
results; other regions silently return empty data.
"""

import re
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from ..utils.config import Config
from ..utils.logging_config import get_logger

logger = get_logger(__name__)

# Constants
VERTEX_REGION = "us-central1"  # Required for Google Maps grounding
MODEL_NAME = "gemini-2.5-flash"
MAX_PLACES = 10


def _extract_address_from_segment(segment_text: str) -> str:
    """
    Extract address from grounding support segment text.

    The segment typically contains place name and address like:
    "**Shinjuku City Office (新宿区役所)**
        *   **Address:** 1-chōme-4-1 Kabukichō, Shinjuku City, Tokyo 160-8484, Japan"

    Returns the address string or empty string if not found.
    """
    # Try to find "Address:" pattern (case insensitive)
    address_match = re.search(
        r"\*\*Address:\*\*\s*(.+?)(?:\n|$)", segment_text, re.IGNORECASE
    )
    if address_match:
        return address_match.group(1).strip()

    # Try alternative pattern without markdown bold
    address_match = re.search(r"Address:\s*(.+?)(?:\n|$)", segment_text, re.IGNORECASE)
    if address_match:
        return address_match.group(1).strip()

    # Try to find anything that looks like an address (has commas and contains Japan)
    # Split by lines and look for address-like strings
    lines = segment_text.split("\n")
    for line in lines:
        line = line.strip()
        # Skip title lines (usually has ** markers)
        if "**" in line or not line:
            continue
        # Check if it looks like an address (has commas and is substantial)
        if "," in line and len(line) > 20:
            # Clean up markdown artifacts
            line = re.sub(r"\*+", "", line)
            line = line.strip("- \t")
            return line

    return ""


class GoogleMapsSearchInput(BaseModel):
    """Input schema for Google Maps search."""

    query: str = Field(
        description="What to search for (e.g., 'immigration offices', 'city halls')"
    )
    location: str = Field(description="Location to search near (e.g., 'Tokyo, Japan')")


class GoogleMapsSearchTool(BaseTool):
    """
    Search for places using Google Maps grounding via Vertex AI.

    This tool uses the official Google GenAI SDK with GoogleMaps tool to get
    real place data including place IDs, names, and Google Maps URIs.
    """

    name: str = "google_maps_search"
    description: str = (
        "Search for real places using Google Maps. Returns place names, IDs, and links."
    )
    args_schema: type[BaseModel] = GoogleMapsSearchInput

    def _run(self, query: str, location: str) -> list[dict[str, Any]]:
        """
        Search for places using Google Maps grounding.

        Args:
            query: What to search for (e.g., "immigration offices")
            location: Where to search (e.g., "Tokyo, Japan")

        Returns:
            List of places with name, address, place_id, and maps_url
        """
        try:
            logger.info(f"Google Maps search: '{query}' near '{location}'")

            # Initialize Vertex AI client (must use us-central1 for Maps grounding)
            client = genai.Client(
                vertexai=True,
                project=Config.GOOGLE_CLOUD_PROJECT,
                location=VERTEX_REGION,
            )

            # Build search prompt
            prompt = f"Find 3-5 specific {query} near {location}. List their exact names and addresses."

            # Call Gemini with Google Maps tool
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[
                        types.Tool(google_maps=types.GoogleMaps(enable_widget=False))
                    ]
                ),
            )

            # Extract places from response
            places = self._extract_places_from_response(response)

            logger.info(f"Returning {len(places)} places")
            return places

        except Exception as e:
            logger.error(f"Google Maps search failed: {e}", exc_info=True)
            return []  # Return empty list on error (resilient tool)

    def _extract_places_from_response(self, response) -> list[dict[str, Any]]:
        """
        Extract place data from Gemini API response.

        Args:
            response: Gemini API response with grounding metadata

        Returns:
            List of place dictionaries
        """
        places = []

        # Validate response structure
        if not hasattr(response, "candidates") or not response.candidates:
            logger.warning("No candidates in response")
            return places

        candidate = response.candidates[0]

        # Get grounding metadata
        if (
            not hasattr(candidate, "grounding_metadata")
            or not candidate.grounding_metadata
        ):
            logger.warning("No grounding_metadata in candidate")
            return places

        grounding_meta = candidate.grounding_metadata

        # Check for grounding chunks
        if (
            not hasattr(grounding_meta, "grounding_chunks")
            or not grounding_meta.grounding_chunks
        ):
            logger.warning("No grounding_chunks in metadata")
            return places

        logger.info(
            f"Found {len(grounding_meta.grounding_chunks)} grounding chunks"
        )

        # Build address lookup from grounding supports
        chunk_to_address = self._extract_addresses_from_supports(grounding_meta)

        # Extract place data from chunks
        for idx, chunk in enumerate(grounding_meta.grounding_chunks[:MAX_PLACES]):
            place = self._extract_place_from_chunk(chunk, idx, chunk_to_address)
            if place:
                places.append(place)

        return places

    def _extract_addresses_from_supports(self, grounding_meta) -> dict[int, str]:
        """
        Build a mapping of chunk index to address from grounding supports.

        Args:
            grounding_meta: Grounding metadata containing supports

        Returns:
            Dictionary mapping chunk index to address string
        """
        chunk_to_address = {}

        if (
            not hasattr(grounding_meta, "grounding_supports")
            or not grounding_meta.grounding_supports
        ):
            return chunk_to_address

        for support in grounding_meta.grounding_supports:
            if not hasattr(support, "grounding_chunk_indices") or not hasattr(
                support, "segment"
            ):
                continue

            segment_text = (
                support.segment.text if hasattr(support.segment, "text") else ""
            )
            address = _extract_address_from_segment(segment_text)

            if address:
                # Map this address to all chunks it supports
                for chunk_idx in support.grounding_chunk_indices:
                    chunk_to_address[chunk_idx] = address

        return chunk_to_address

    def _extract_place_from_chunk(
        self, chunk, chunk_idx: int, chunk_to_address: dict[int, str]
    ) -> dict[str, Any] | None:
        """
        Extract place data from a single grounding chunk.

        Args:
            chunk: Grounding chunk with Maps data
            chunk_idx: Index of this chunk
            chunk_to_address: Mapping of chunk indices to addresses

        Returns:
            Place dictionary or None if invalid
        """
        if not hasattr(chunk, "maps") or not chunk.maps:
            return None

        maps_data = chunk.maps

        # Extract required fields
        place_id = getattr(maps_data, "place_id", None)
        title = getattr(maps_data, "title", None)
        uri = getattr(maps_data, "uri", None)

        if not place_id or not title:
            return None

        # Get address or use fallback
        address = chunk_to_address.get(chunk_idx, "Address available in Google Maps")

        return {
            "name": title,
            "address": address,
            "place_id": place_id,
            "maps_url": uri
            or f"https://www.google.com/maps/place/?q=place_id:{place_id}",
        }

    async def _arun(self, query: str, location: str) -> list[dict[str, Any]]:
        """Async version - just calls sync version for now."""
        return self._run(query, location)


# Create singleton instance
google_maps_search = GoogleMapsSearchTool()
