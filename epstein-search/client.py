"""
Python client for querying the DOJ Epstein Library search API.

The DOJ exposes a JSON API at /multimedia-search that powers the Epstein Library search.
This client provides a clean interface to query it.
"""

import requests
from typing import Optional
from dataclasses import dataclass


@dataclass
class SearchResult:
    """A single search result from the DOJ Epstein Library."""
    document_id: str
    filename: str
    url: str
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None
    content_type: Optional[str] = None
    text: Optional[str] = None
    score: Optional[float] = None
    raw: dict = None

    def __repr__(self):
        pages = f" (pages {self.start_page}-{self.end_page})" if self.start_page else ""
        return f"SearchResult({self.filename}{pages})"


@dataclass
class DocumentMetadata:
    """Metadata for a document in the Epstein Library."""
    document_id: str
    filename: str
    url: str
    file_size: Optional[int] = None
    total_words: Optional[int] = None
    total_characters: Optional[int] = None
    content_type: Optional[str] = None
    processed_at: Optional[str] = None
    indexed_at: Optional[str] = None


class EpsteinClient:
    """
    Client for the DOJ Epstein Library search API.

    Usage:
        client = EpsteinClient()
        results = client.search("flight logs", limit=10)

        for result in results:
            print(result.filename, result.url)
    """

    BASE_URL = "https://www.justice.gov"
    SEARCH_ENDPOINT = "/multimedia-search"

    def __init__(self, session: Optional[requests.Session] = None):
        """
        Initialize the client.

        Args:
            session: Optional requests.Session for custom configuration.
                     If not provided, a new session will be created.
        """
        self.session = session or requests.Session()
        self._setup_session()

    def _setup_session(self):
        """Configure the session with required headers and cookies."""
        # Browser-like headers
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.justice.gov/epstein/search",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        })


    def search(self, query: str, n: Optional[int] = None, skip: int = 0) -> list[SearchResult]:
        """
        Search the Epstein Library.

        Supports advanced search patterns:
        - Basic search: "flight logs" (matches documents containing these terms)
        - Exact phrase: '"flight logs"' (matches exact phrase)
        - Wildcard *: "fl*ght", "maxw*" (matches any characters)
        - Wildcard ?: "flight?" (matches single character)
        - Required terms: "+flight +logs" (both terms must appear)

        Args:
            query: Search terms (e.g., "flight logs", "Maxwell")
            n: Number of results to return.
               None = return all results (may be slow for large result sets)
               Default API page size is 10.
            skip: Number of results to skip (default: 0)

        Returns:
            List of SearchResult objects

        Raises:
            requests.HTTPError: If the request fails
        """
        url = f"{self.BASE_URL}{self.SEARCH_ENDPOINT}"
        results = []
        page = 0
        fetched = 0
        fetch_limit = (skip + n) if n else None

        while True:
            params = {"keys": query, "page": page}
            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            hits_data = data.get("hits", {})
            hits = hits_data.get("hits", [])

            for hit in hits:
                source = hit.get("_source", {})
                result = SearchResult(
                    document_id=source.get("documentId", ""),
                    filename=source.get("ORIGIN_FILE_NAME", ""),
                    url=source.get("ORIGIN_FILE_URI", ""),
                    start_page=source.get("startPage"),
                    end_page=source.get("endPage"),
                    chunk_index=source.get("chunkIndex"),
                    total_chunks=source.get("totalChunks"),
                    content_type=source.get("contentType"),
                    text=source.get("text", source.get("content")),
                    score=hit.get("_score"),
                    raw=hit,
                )
                fetched += 1
                if fetched > skip:
                    results.append(result)

                if fetch_limit and fetched >= fetch_limit:
                    return results

            # Check if more pages
            total_info = hits_data.get("total", {})
            total = total_info.get("value", 0) if isinstance(total_info, dict) else total_info
            if (page + 1) * 10 >= total or not hits:
                break

            page += 1

        return results

    def count(self, query: str) -> int:
        """
        Get the total number of results for a query.

        Args:
            query: Search terms

        Returns:
            Total number of matching documents
        """
        url = f"{self.BASE_URL}{self.SEARCH_ENDPOINT}"
        params = {"keys": query, "page": 0}
        response = self.session.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        total_info = data.get("hits", {}).get("total", {})
        return total_info.get("value", 0) if isinstance(total_info, dict) else total_info

    def get_metadata(self, filename: str) -> Optional[DocumentMetadata]:
        """
        Get metadata for a specific document by filename.

        Args:
            filename: The exact filename to look up (e.g., "EFTA02185794.pdf")

        Returns:
            DocumentMetadata object or None if not found
        """
        url = f"{self.BASE_URL}{self.SEARCH_ENDPOINT}"
        # Search for the exact filename
        params = {"keys": f'"{filename}"', "page": 0}
        response = self.session.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        hits = data.get("hits", {}).get("hits", [])

        if not hits:
            return None

        # Find the best match (exact filename match preferred)
        hit = next((h for h in hits if h.get("_source", {}).get("ORIGIN_FILE_NAME") == filename), hits[0])
        source = hit.get("_source", {})

        return DocumentMetadata(
            document_id=source.get("documentId", ""),
            filename=source.get("ORIGIN_FILE_NAME", ""),
            url=source.get("ORIGIN_FILE_URI", ""),
            file_size=source.get("fileSize"),
            total_words=source.get("totalWords"),
            total_characters=source.get("totalCharacters"),
            content_type=source.get("contentType"),
            processed_at=source.get("processedAt"),
            indexed_at=source.get("indexedAt"),
        )

def main():
    """Example usage."""
    client = EpsteinClient()

    # Get 50 results
    print("Searching for 'flight logs' (n=50)...")
    results = client.search("flight logs", n=50)
    print(f"Got {len(results)} results\n")

    for r in results[:5]:
        print(f"  {r.filename}")
        print(f"    {r.url}\n")


if __name__ == "__main__":
    main()
