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
        self.session.headers.update({
            "Accept": "application/json",
        })

    def search(self, query: str, limit: Optional[int] = None) -> list[SearchResult]:
        """
        Search the Epstein Library.

        Args:
            query: Search terms (e.g., "flight logs", "Maxwell")
            limit: Maximum number of results to return.
                   None = return all results (may be slow for large result sets)
                   Default API page size is 10.

        Returns:
            List of SearchResult objects

        Raises:
            requests.HTTPError: If the request fails
        """
        url = f"{self.BASE_URL}{self.SEARCH_ENDPOINT}"
        results = []
        page = 0

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
                results.append(result)

                if limit and len(results) >= limit:
                    return results[:limit]

            # Check if more pages
            total_info = hits_data.get("total", {})
            total = total_info.get("value", 0) if isinstance(total_info, dict) else total_info
            if (page + 1) * 10 >= total or not hits:
                break

            page += 1

        return results

def main():
    """Example usage."""
    client = EpsteinClient()

    # Get 50 results
    print("Searching for 'flight logs' (limit=50)...")
    results = client.search("flight logs", limit=50)
    print(f"Got {len(results)} results\n")

    for r in results[:5]:
        print(f"  {r.filename}")
        print(f"    {r.url}\n")

if __name__ == "__main__":
    main()
