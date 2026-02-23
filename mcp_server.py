import os
from dataclasses import fields
from mcp.server.fastmcp import FastMCP
import requests
from client import EpsteinClient
from pdf import generate_pdf as _generate_pdf, merge_markdown_to_pdf as _merge_markdown_to_pdf

mcp = FastMCP("epstein-search")

VECTOR_URL = os.environ.get("VECTOR_URL", "https://vector.korroni.cloud")
VECTOR_API_KEY = os.environ.get("VECTOR_API_KEY", "")

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
def extract_image(
    query: str,
    n: int = 1,
    skip: int = 0,
    page: int | None = None,
    output_dir: str = "temp",
) -> list[dict]:
    """
    Download PDFs from the DOJ Epstein Library and extract embedded images.
    Images are saved to disk.

    Args:
        query: An EFTA document ID (e.g. "EFTA00123456") or search terms.
               Search supports exact phrases ("flight logs"), wildcards (maxw*),
               required terms (+flight +logs), and OR queries with | ("pizza | flights").
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

@mcp.tool()
def text_search(query: str, n: int = 20, offset: int = 0) -> list[dict]:
    """
    Keyword search over ~1M OCR'd Epstein documents. This is the default
    search tool — start here. Use vector_search for meaning-based search,
    or fuzzy_search to catch OCR errors and misspellings.

    Args:
        query: Search terms. Supports:
               - Plain terms: "Maxwell flight" (AND — both must appear)
               - Exact phrase: '"wire transfer"'
               - OR: "Maxwell OR Brunel"
               - NOT: "island -vacation"
               - Wildcard: "maxw*" (prefix match)
        n: Maximum number of results to return (default: 20, max: 100).
        offset: Number of results to skip for pagination (default: 0).

    Returns:
        A list of matching chunks with efta_id, dataset, chunk_index,
        total_chunks, word_count, rank (relevance score), and headline
        (snippet with matched terms).
    """
    headers = {"Content-Type": "application/json"}
    if VECTOR_API_KEY:
        headers["X-API-Key"] = VECTOR_API_KEY
    payload = {"query": query, "limit": min(n, 100), "offset": offset}
    resp = requests.post(f"{VECTOR_URL}/text_search", json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["results"]

@mcp.tool()
def text_search_count(query: str) -> int:
    """
    Count how many document chunks match a keyword query — without returning
    the actual results. Use this to gauge the size of a result set before
    paginating through it with text_search.

    Args:
        query: Search terms (same syntax as text_search).

    Returns:
        The number of matching chunks.
    """
    headers = {"Content-Type": "application/json"}
    if VECTOR_API_KEY:
        headers["X-API-Key"] = VECTOR_API_KEY
    payload = {"query": query}
    resp = requests.post(f"{VECTOR_URL}/text_search/count", json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["count"]

@mcp.tool()
def vector_search(query: str, n: int = 20, offset: int = 0) -> list[dict]:
    """
    Semantic search over Epstein documents using vector embeddings.
    Unlike text_search, this finds documents by meaning — useful for concepts,
    paraphrases, and topics that don't match exact keywords.

    Use this when: you're looking for a concept or situation rather than specific
    words, or when text_search returns irrelevant results because the documents
    use different terminology.

    Tips: phrase queries as descriptive statements, not questions.
    Good: "recruiting underage girls from schools", "payments to silence victims"
    Bad: "did Epstein recruit from schools?", "were victims paid?"

    Args:
        query: Natural language query (e.g. "payments to politicians",
               "discussions about underage girls", "flight manifest entries").
        n: Maximum number of results to return (default: 20, max: 100).
        offset: Number of results to skip for pagination (default: 0).

    Returns:
        A list of matching text chunks with efta_id, dataset, text,
        and similarity score (0-1, higher is more relevant).
    """
    headers = {"Content-Type": "application/json"}
    if VECTOR_API_KEY:
        headers["X-API-Key"] = VECTOR_API_KEY
    payload = {"query": query, "limit": min(n, 100), "offset": offset}
    resp = requests.post(f"{VECTOR_URL}/vector_search", json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["results"]

@mcp.tool()
def similarity_search(efta_id: str, chunk_index: int = 0, n: int = 20, offset: int = 0) -> list[dict]:
    """
    Find documents similar to a given document chunk using vector embeddings.
    Uses the existing embedding of the source chunk — no re-encoding needed.

    Use this as a follow-up after finding an interesting document via
    text_search or vector_search — it finds other documents with similar content.

    Args:
        efta_id: The EFTA ID of the source document (e.g. "EFTA00123456").
        chunk_index: Which chunk of the document to use as the query vector (default: 0).
        n: Maximum number of results to return (default: 20, max: 100).
        offset: Number of results to skip for pagination (default: 0).

    Returns:
        A list of similar text chunks with efta_id, dataset, text,
        and similarity score (0-1, higher is more relevant).
    """
    headers = {"Content-Type": "application/json"}
    if VECTOR_API_KEY:
        headers["X-API-Key"] = VECTOR_API_KEY
    payload = {"efta_id": efta_id, "chunk_index": chunk_index, "limit": min(n, 100), "offset": offset}
    resp = requests.post(f"{VECTOR_URL}/similarity_search", json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["results"]

@mcp.tool()
def fuzzy_search(query: str, n: int = 20, offset: int = 0, exclude_exact: bool = False) -> list[dict]:
    """
    Fuzzy trigram search over Epstein document chunks — typo-tolerant
    matching. Finds documents even when the query or document contains OCR errors
    or misspellings. For example, "Maxwel" finds "Maxwell", "Ghisliane" finds
    "Ghislaine". Uses word_similarity to find the best matching substring within
    each chunk.

    Use this to catch OCR errors and misspellings that text_search misses.
    Many documents are poorly scanned, so names and terms are often garbled.

    Args:
        query: Search terms, can include typos (e.g. "Maxwel", "Ghisliane").
        n: Maximum number of results to return (default: 20, max: 100).
        offset: Number of results to skip for pagination (default: 0).
        exclude_exact: If True, exclude documents that keyword search already finds,
                       showing only fuzzy-only matches (default: False).

    Returns:
        A list of matching chunks with efta_id, dataset, chunk_index,
        total_chunks, text, and similarity (0-1, higher is closer match).
    """
    headers = {"Content-Type": "application/json"}
    if VECTOR_API_KEY:
        headers["X-API-Key"] = VECTOR_API_KEY
    payload = {"query": query, "limit": min(n, 100), "offset": offset}
    if exclude_exact:
        payload["exclude_exact"] = True
    resp = requests.post(f"{VECTOR_URL}/fuzzy_search", json=payload, headers=headers, timeout=180)
    resp.raise_for_status()
    return resp.json()["results"]

@mcp.tool()
def fuzzy_search_count(query: str) -> int:
    """
    Count how many document chunks match a fuzzy/trigram query — without
    returning the actual results. Use this to gauge the size of a fuzzy
    result set before paginating through it with fuzzy_search.

    Args:
        query: Search terms (same syntax as fuzzy_search, typo-tolerant).

    Returns:
        The number of matching chunks.
    """
    headers = {"Content-Type": "application/json"}
    if VECTOR_API_KEY:
        headers["X-API-Key"] = VECTOR_API_KEY
    payload = {"query": query}
    resp = requests.post(f"{VECTOR_URL}/fuzzy_search/count", json=payload, headers=headers, timeout=180)
    resp.raise_for_status()
    return resp.json()["count"]

@mcp.tool()
def get_document(efta_id: str) -> dict:
    """
    Fetch a single document by its EFTA ID from the vector database.
    Returns the full document record including text, metadata, and version.

    Use this when you already know the EFTA ID and want the complete document
    without searching. Faster than extract_text because it reads from the
    database instead of downloading and parsing the PDF.

    Args:
        efta_id: The EFTA document ID (e.g. "EFTA00123456").

    Returns:
        A dict with efta_id, dataset, url, pages, word_count, text, and version.
    """
    headers = {"Content-Type": "application/json"}
    if VECTOR_API_KEY:
        headers["X-API-Key"] = VECTOR_API_KEY
    resp = requests.get(f"{VECTOR_URL}/documents/{efta_id}", headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()

@mcp.tool()
def generate_pdf(markdown_path: str, output_path: str | None = None) -> str:
    """
    Convert a markdown file to a styled PDF.

    Args:
        markdown_path: Path to the markdown file to convert.
        output_path: Path for the output PDF. If omitted, uses the input
                     filename with a .pdf extension.

    Returns:
        The path to the generated PDF file.
    """
    return _generate_pdf(markdown_path, output_path)

@mcp.tool()
def merge_markdown_to_pdf(markdown_paths: list[str], output_path: str) -> str:
    """
    Merge multiple markdown files into a single styled PDF with page breaks
    between each file and page numbers on every page.

    Args:
        markdown_paths: List of paths to markdown files, in the order they
                        should appear in the PDF.
        output_path: Path for the output PDF file.

    Returns:
        The path to the generated PDF file.
    """
    return _merge_markdown_to_pdf(markdown_paths, output_path)

def main():
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
