"""
Python client for querying the DOJ Epstein Library search API.

The DOJ exposes a JSON API at /multimedia-search that powers the Epstein Library search.
This client provides a clean interface to query it.
"""

import os
import sys
import requests
from io import BytesIO
from typing import Optional
from dataclasses import dataclass
from pydantic import BaseModel, Field


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
    text: Optional[str] = None
    events: Optional[list] = None  # list[Event] when populated
    raw: dict = None

    def __repr__(self):
        pages = f" (pages {self.start_page}-{self.end_page})" if self.start_page else ""
        return f"Record({self.filename}{pages})"


class Event(BaseModel):
    summary: str = Field(description="Brief summary of what happened")
    timestamp: str = Field(description="When it happened (date, time, or date range as stated in the text)")
    location: str | None = Field(default=None, description="Where it happened, if mentioned in the text")


class EventList(BaseModel):
    events: list[Event] = Field(description="List of events extracted from the document")


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


    def _search_single(self, query: str):
        """Yield all Records for a single query term, handling pagination internally."""
        url = f"{self.BASE_URL}{self.SEARCH_ENDPOINT}"
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
                highlights = hit.get("highlight", {}).get("content", [])
                yield Record(
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

            # Check if more pages
            total_info = hits_data.get("total", {})
            total = total_info.get("value", 0) if isinstance(total_info, dict) else total_info
            if (page + 1) * 10 >= total or not hits:
                break

            page += 1

    def search(self, queries: str | list[str], n: Optional[int] = None, skip: int = 0):
        """
        Search the Epstein Library. Yields Records one at a time.

        Args:
            queries: A single query string, or a list of query strings.
                     Multiple queries are interleaved round-robin and
                     deduplicated by document_id.
            n: Number of results to yield.
               None = yield all results.
            skip: Number of unique results to skip before yielding (default: 0)

        Yields:
            Record objects
        """
        if isinstance(queries, str):
            queries = [queries]

        if len(queries) == 1:
            # Single query — yield directly with skip/n applied
            skipped = 0
            yielded = 0
            for record in self._search_single(queries[0]):
                if skipped < skip:
                    skipped += 1
                    continue
                yield record
                yielded += 1
                if n and yielded >= n:
                    return
        else:
            # Multiple queries — round-robin with dedup
            generators = [self._search_single(q) for q in queries]
            seen = set()
            skipped = 0
            yielded = 0

            while generators:
                exhausted = []
                for i, gen in enumerate(generators):
                    try:
                        record = next(gen)
                    except StopIteration:
                        exhausted.append(i)
                        continue

                    if record.document_id in seen:
                        continue
                    seen.add(record.document_id)

                    if skipped < skip:
                        skipped += 1
                        continue

                    yield record
                    yielded += 1
                    if n and yielded >= n:
                        return

                # Remove exhausted generators in reverse order
                for i in reversed(exhausted):
                    generators.pop(i)

    def _extract_text(self, records: list[Record]):
        """Download PDFs and extract text. Yields each record after processing."""
        import pdfplumber
        records = list(records)
        total = len(records)
        for i, r in enumerate(records, 1):
            print(f"\r\033[KDownloading {i}/{total}: {r.filename}", end="", file=sys.stderr, flush=True)
            response = self.session.get(r.url)
            response.raise_for_status()
            with pdfplumber.open(BytesIO(response.content)) as pdf:
                r.text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            yield r
        print("", file=sys.stderr)

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

    _EVENTS_SYSTEM_PROMPT = (
        "Extract events from legal documents to assist a criminal investigation. "
        "Be objective — report only what the document states. "
        "Focus on interactions between people: meetings, calls, trips, transactions, communications. "
        "Flag suspected code words or euphemisms in quotes. "
        "Format: '[Person] [action] [details]' (10-25 words). "
        "Timestamps: use full dates (MM/DD/YYYY) when available, otherwise the most precise reference in the text. "
        "Include location if mentioned. Require both an actor and a time reference. "
        "Skip boilerplate and procedural language."
    )

    _EVENTS_USER_PROMPT = (
        "Extract events related to '{query}' from the following document. "
        "Focus on events relevant to the search term. "
        "For each event, identify WHO did WHAT and WHEN:\n\n"
    )

    DEFAULT_MODEL = "deepseek/deepseek-chat-v3-0324"

    def _extract_events(self, records: list[Record], model: str | None = None, query: str = "", workers: int = 10):
        """Download PDFs, extract text, and extract events in parallel. Yields each record as completed."""
        import logging
        import pdfplumber
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from agno.agent import Agent
        from agno.models.openrouter import OpenRouter

        # Redirect agno's logger to stderr (it defaults to stdout via Rich, corrupting JSON output)
        agno_logger = logging.getLogger("agno")
        agno_logger.handlers.clear()
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        agno_logger.addHandler(handler)

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise SystemExit("Error: OPENROUTER_API_KEY environment variable is required for --events")

        prompt = self._EVENTS_USER_PROMPT.format(query=query)

        def process(r):
            # Download PDF and extract text
            response = self.session.get(r.url)
            response.raise_for_status()
            with pdfplumber.open(BytesIO(response.content)) as pdf:
                r.text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            if not r.text:
                return r
            # Extract events via LLM
            agent = Agent(
                model=OpenRouter(id=model or self.DEFAULT_MODEL, api_key=api_key),
                instructions=self._EVENTS_SYSTEM_PROMPT,
                output_schema=EventList,
            )
            resp = agent.run(prompt + r.text)
            if resp.content and isinstance(resp.content, EventList):
                r.events = resp.content.events
            return r

        records = list(records)
        total = len(records)
        done = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(process, r): r for r in records}
            for future in as_completed(futures):
                done += 1
                r = future.result()
                print(f"\r\033[KProcessing {done}/{total}: {r.filename}", end="", file=sys.stderr, flush=True)
                yield r
        print("", file=sys.stderr)


def main():
    """Example usage."""
    client = EpsteinClient()

    # Get 5 results
    print("Searching for 'flight logs' (n=5)...")
    for r in client.search("flight logs", n=5):
        print(f"  {r.filename}")
        print(f"    {r.url}\n")


if __name__ == "__main__":
    main()
