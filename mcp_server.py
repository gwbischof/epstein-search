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

@mcp.tool()
def vector_search(query: str, n: int = 20, dataset: int | None = None) -> list[dict]:
    """
    Semantic search over DOJ Epstein Library documents using vector embeddings.
    Unlike keyword search, this finds documents by meaning — useful for concepts,
    paraphrases, and questions that don't match exact keywords.

    Args:
        query: Natural language query (e.g. "payments to politicians",
               "discussions about underage girls", "flight manifest entries").
        n: Maximum number of results to return (default: 20, max: 100).
        dataset: Filter to a specific dataset number (optional).

    Returns:
        A list of matching text chunks with efta_id, dataset, text, and
        similarity score (0-1, higher is more relevant).
    """
    headers = {"Content-Type": "application/json"}
    if VECTOR_API_KEY:
        headers["X-API-Key"] = VECTOR_API_KEY
    payload = {"query": query, "limit": min(n, 100)}
    if dataset is not None:
        payload["dataset"] = dataset
    resp = requests.post(f"{VECTOR_URL}/vector_search", json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["results"]

@mcp.tool()
def similarity_search(efta_id: str, chunk_index: int = 0, n: int = 20, dataset: int | None = None) -> list[dict]:
    """
    Find documents similar to a given document chunk using vector embeddings.
    Uses the existing embedding of the source chunk — no re-encoding needed.

    Args:
        efta_id: The EFTA ID of the source document (e.g. "EFTA00123456").
        chunk_index: Which chunk of the document to use as the query vector (default: 0).
        n: Maximum number of results to return (default: 20, max: 100).
        dataset: Filter to a specific dataset number (optional).

    Returns:
        A list of similar text chunks with efta_id, dataset, text, and
        similarity score (0-1, higher is more relevant).
    """
    headers = {"Content-Type": "application/json"}
    if VECTOR_API_KEY:
        headers["X-API-Key"] = VECTOR_API_KEY
    payload = {"efta_id": efta_id, "chunk_index": chunk_index, "limit": min(n, 100)}
    if dataset is not None:
        payload["dataset"] = dataset
    resp = requests.post(f"{VECTOR_URL}/similarity_search", json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["results"]

@mcp.tool()
def fuzzy_search(query: str, n: int = 20, dataset: int | None = None, exclude_exact: bool = False) -> list[dict]:
    """
    Fuzzy trigram search over DOJ Epstein Library documents — typo-tolerant matching.
    Finds documents even when the query contains OCR errors or misspellings.
    For example, "Maxwel" finds "Maxwell", "fligth" finds "flight".

    Args:
        query: Search terms (e.g. "Maxwel", "fligth logs").
        n: Maximum number of results to return (default: 20, max: 100).
        dataset: Filter to a specific dataset number (optional).
        exclude_exact: If True, exclude documents that keyword search already finds,
                       showing only fuzzy-only matches (default: False).

    Returns:
        A list of matching documents with efta_id, dataset, word_count,
        similarity score (0-1), and headline snippet.
    """
    headers = {"Content-Type": "application/json"}
    if VECTOR_API_KEY:
        headers["X-API-Key"] = VECTOR_API_KEY
    payload = {"query": query, "limit": min(n, 100)}
    if dataset is not None:
        payload["dataset"] = dataset
    if exclude_exact:
        payload["exclude_exact"] = True
    resp = requests.post(f"{VECTOR_URL}/fuzzy_search", json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["results"]

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
