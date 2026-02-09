from dataclasses import fields
from mcp.server.fastmcp import FastMCP
from client import EpsteinClient

mcp = FastMCP("epstein-search")

def _parse_queries(query: str) -> list[str]:
    """Split query on | for OR support."""
    queries = [q.strip() for q in query.split("|")]
    return [q for q in queries if q]

def _record_to_dict(r) -> dict:
    """Convert a Record to a dict with all metadata."""
    d = {}
    for f in fields(r):
        if f.name == "raw":
            continue
        d[f.name] = getattr(r, f.name)
    return d

@mcp.tool()
def search(query: str, n: int = 10, skip: int = 0) -> list[dict]:
    """
    Search the DOJ Epstein Library for documents matching a query.

    Args:
        query: Search terms. Supports exact phrases ("flight logs"),
               wildcards (maxw*), required terms (+flight +logs),
               and OR queries with | ("pizza | flights").
        n: Maximum number of results to return (default: 10, 0 for all).
        skip: Number of results to skip for pagination (default: 0).

    Returns:
        A list of matching document records with metadata and text highlights.
    """
    client = EpsteinClient()
    queries = _parse_queries(query)
    results = []
    for record in client.search(queries, n=n or None, skip=skip):
        results.append(_record_to_dict(record))
    return results

@mcp.tool()
def count(query: str) -> int:
    """
    Count the total number of documents matching a query in the DOJ Epstein Library.

    Args:
        query: Search terms (same syntax as search, but does not support OR queries with |).

    Returns:
        The total number of matching documents.
    """
    client = EpsteinClient()
    return client.count(query)

@mcp.tool()
def extract_text(query: str, n: int = 1, skip: int = 0) -> list[dict]:
    """
    Search the DOJ Epstein Library, download the matching PDFs, and extract
    the full text content from each document.

    Args:
        query: Search terms (same syntax as search).
        n: Maximum number of documents to process (default: 1, 0 for all).
        skip: Number of results to skip (default: 0).

    Returns:
        A list of records with all metadata plus the full extracted text.
    """
    client = EpsteinClient()
    queries = _parse_queries(query)
    records = client.search(queries, n=n or None, skip=skip)
    results = []
    for record in client._extract_text(records):
        results.append(_record_to_dict(record))
    return results

@mcp.tool()
def extract_image(
    query: str,
    n: int = 1,
    skip: int = 0,
    page: int | None = None,
    output_dir: str = "temp",
) -> list[dict]:
    """
    Search the DOJ Epstein Library, download matching PDFs, and extract
    embedded images from each document.

    Args:
        query: Search terms (same syntax as search).
        n: Maximum number of documents to process (default: 1, 0 for all).
        skip: Number of results to skip (default: 0).
        page: Page number (1-indexed) to extract images from. If omitted, extracts from all pages.
        output_dir: Directory to save extracted images (default: "temp").

    Returns:
        A list of records with metadata and extracted image info. Each image
        entry has path, page, width, height, size, and format fields.
    """
    client = EpsteinClient()
    queries = _parse_queries(query)
    records = client.search(queries, n=n or None, skip=skip)
    results = []
    for record in client._extract_images(records, page=page, output_dir=output_dir):
        results.append(_record_to_dict(record))
    return results

def main():
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
