"""
Python client for querying the DOJ Epstein Library search API.

The DOJ exposes a JSON API at /multimedia-search that powers the Epstein Library search.
This client provides a clean interface to query it.
"""

import requests
from io import BytesIO
from typing import Optional
from dataclasses import dataclass


@dataclass
class Record:
    """A record from the DOJ Epstein Library."""
    # Core identifiers
    document_id: str
    filename: str
    url: str
    key: Optional[str] = None
    bucket: Optional[str] = None

    # Document info
    content_type: Optional[str] = None
    file_size: Optional[int] = None
    total_words: Optional[int] = None
    total_characters: Optional[int] = None

    # Page info
    start_page: Optional[int] = None
    end_page: Optional[int] = None

    # Chunk info
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None
    chunk_size: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    is_chunked: Optional[bool] = None

    # Timestamps
    processed_at: Optional[str] = None
    indexed_at: Optional[str] = None
    source: Optional[str] = None

    # Search result fields
    score: Optional[float] = None
    highlights: Optional[list[str]] = None
    raw: dict = None

    def __repr__(self):
        pages = f" (pages {self.start_page}-{self.end_page})" if self.start_page else ""
        return f"Record({self.filename}{pages})"


# Alias for backwards compatibility
SearchResult = Record


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
        self.session.cookies.set("justiceGovAgeVerified", "true", domain=".justice.gov")


    def search(self, query: str, n: Optional[int] = None, skip: int = 0) -> list[Record]:
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
            List of Record objects

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
                highlights = hit.get("highlight", {}).get("content", [])
                result = Record(
                    document_id=source.get("documentId", ""),
                    filename=source.get("ORIGIN_FILE_NAME", ""),
                    url=source.get("ORIGIN_FILE_URI", ""),
                    key=source.get("key"),
                    bucket=source.get("bucket"),
                    content_type=source.get("contentType"),
                    file_size=source.get("fileSize"),
                    total_words=source.get("totalWords"),
                    total_characters=source.get("totalCharacters"),
                    start_page=source.get("startPage"),
                    end_page=source.get("endPage"),
                    chunk_index=source.get("chunkIndex"),
                    total_chunks=source.get("totalChunks"),
                    chunk_size=source.get("chunkSize"),
                    char_start=source.get("charStart"),
                    char_end=source.get("charEnd"),
                    is_chunked=source.get("isChunked"),
                    processed_at=source.get("processedAt"),
                    indexed_at=source.get("indexedAt"),
                    source=source.get("source"),
                    score=hit.get("_score"),
                    highlights=highlights if highlights else None,
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

    def text(self, query: str, n: int = 1, skip: int = 0) -> list[tuple[Record, str]]:
        """
        Search for documents and extract their text content in memory.

        Args:
            query: Search term or filename (e.g., "trump", "EFTA02185794.pdf")
            n: Number of documents to extract text from (default: 1)
            skip: Number of results to skip (default: 0)

        Returns:
            List of (Record, text) tuples
        """
        import pdfplumber

        results = self.search(query, n=n, skip=skip)
        if not results:
            raise FileNotFoundError(f"No results for: {query}")

        out = []
        for r in results:
            response = self.session.get(r.url)
            response.raise_for_status()
            with pdfplumber.open(BytesIO(response.content)) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            out.append((r, text))
        return out


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
