"""
Python client for the epstein-vector search API.
"""

import os
import sys
import tempfile
import requests


class SearchClient:
    """
    Client for the Epstein document search API.

    Usage:
        client = SearchClient()
        results = client.search("payments to politicians", limit=10)
        for r in results:
            print(r["efta_id"], r["score"], r["text"][:100])
    """

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
    ):
        self.url = (url or os.environ.get("VECTOR_URL", "https://vector.korroni.cloud")).rstrip("/")
        self.api_key = api_key or os.environ.get("VECTOR_API_KEY", "")
        self.session = requests.Session()

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """
        Semantic search over Epstein documents.

        Args:
            query: Natural language query.
            limit: Max results (1-100).
            offset: Skip first N results for pagination.

        Returns:
            List of dicts with efta_id, dataset, chunk_index, total_chunks, text, score.
        """
        payload = {"query": query, "limit": min(limit, 100), "offset": offset}
        resp = self.session.post(f"{self.url}/vector_search", json=payload, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()["results"]

    def text_search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """
        Keyword search over Epstein documents.

        Supports AND (default), OR, NOT (-term), exact phrases ("..."), and wildcards (word*).

        Args:
            query: Search terms.
            limit: Max results (1-100).
            offset: Skip first N results for pagination.

        Returns:
            List of dicts with efta_id, dataset, chunk_index, total_chunks, word_count, rank, headline.
        """
        payload = {"query": query, "limit": min(limit, 100), "offset": offset}
        resp = self.session.post(f"{self.url}/text_search", json=payload, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()["results"]

    def text_search_count(self, query: str) -> int:
        """Count documents matching a keyword query."""
        payload = {"query": query}
        resp = self.session.post(f"{self.url}/text_search/count", json=payload, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()["count"]

    def similarity_search(
        self,
        efta_id: str,
        chunk_index: int = 0,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """
        Find documents similar to an existing chunk.

        Args:
            efta_id: Source document ID.
            chunk_index: Which chunk to use as the query vector (default: 0).
            limit: Max results (1-100).
            offset: Skip first N results for pagination.

        Returns:
            List of dicts with efta_id, dataset, chunk_index, total_chunks, text, score.
        """
        payload = {"efta_id": efta_id, "chunk_index": chunk_index, "limit": min(limit, 100), "offset": offset}
        resp = self.session.post(f"{self.url}/similarity_search", json=payload, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()["results"]

    def get_document(self, efta_id: str) -> dict:
        """
        Fetch a single document by EFTA ID.

        Args:
            efta_id: Document ID (e.g. "EFTA00123456").

        Returns:
            Dict with efta_id, dataset, url, pages, word_count, text, version.

        Raises:
            requests.HTTPError: 404 if document not found.
        """
        resp = self.session.get(f"{self.url}/get_document/{efta_id}", headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()

    def extract_images(
        self,
        efta_id: str,
        page: int | None = None,
        output_dir: str = "temp",
    ) -> list[dict]:
        """
        Download a document's PDF and extract embedded images.

        Args:
            efta_id: Document ID (e.g. "EFTA00123456").
            page: Page number (1-indexed) to extract from. None = all pages.
            output_dir: Directory to save images (default: "temp").

        Returns:
            List of dicts with path, page, width, height, size, format.
        """
        import fitz

        doc_record = self.get_document(efta_id)
        url = doc_record.get("url", "")
        if not url:
            return []

        os.makedirs(output_dir, exist_ok=True)

        print(f"Downloading {efta_id}...", end="", file=sys.stderr, flush=True)
        resp = self.session.get(url, timeout=120)
        resp.raise_for_status()

        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.write(resp.content)
        tmp.close()

        images = []
        try:
            pdf = fitz.open(tmp.name)

            if page is not None:
                pages_to_process = [page - 1] if 1 <= page <= len(pdf) else []
            else:
                pages_to_process = range(len(pdf))

            for page_num in pages_to_process:
                p = pdf[page_num]
                imgs = p.get_images(full=True)
                for j, img in enumerate(imgs):
                    xref = img[0]
                    base_image = pdf.extract_image(xref)
                    ext = base_image["ext"]
                    data = base_image["image"]
                    w = base_image["width"]
                    h = base_image["height"]

                    suffix = f"_{j}" if len(imgs) > 1 else ""
                    filename = f"{efta_id}_page{page_num + 1}{suffix}.{ext}"
                    out_path = os.path.join(output_dir, filename)

                    with open(out_path, "wb") as f:
                        f.write(data)

                    images.append({
                        "path": os.path.abspath(out_path),
                        "page": page_num + 1,
                        "width": w,
                        "height": h,
                        "size": len(data),
                        "format": ext,
                    })

            pdf.close()
        finally:
            os.unlink(tmp.name)

        print(" done", file=sys.stderr)
        return images

    def health(self) -> dict:
        resp = self.session.get(f"{self.url}/health", timeout=10)
        resp.raise_for_status()
        return resp.json()
