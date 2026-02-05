# epstein-search

Python and CLI client for the DOJ Epstein Library search API.

## Installation

```bash
# Install the `es` command globally
uv tool install git+https://github.com/gwbischof/epstein-search

# Or install from a local clone
git clone https://github.com/gwbischof/epstein-search
uv tool install ./epstein-search
```

## CLI

```bash
# Basic search (returns 50 results by default)
es "maxwell"

# Specify number of results
es "flight logs" -n 100

# Output as JSON
es "epstein" --json > results.json

# Check version
es --version
```

Options:
- `-n` - Number of results (default: 50, use 0 for all)
- `--json, -j` - Output results as JSON
- `--version, -v` - Show version

## Python Usage

```bash
# Install as a library
uv add git+https://github.com/gwbischof/epstein-search
```

```python
from client import EpsteinClient

client = EpsteinClient()

# Get 10 results
results = client.search("Maxwell", n=10)

# Get 100 results
results = client.search("flight logs", n=100)

# Skip first 50, get next 100
results = client.search("flight logs", n=100, skip=50)

# Get ALL results (no limit - may be slow for broad queries)
results = client.search("Trump")

for r in results:
    print(r.filename, r.url)
```

## API Endpoint

The client queries the DOJ's search API:

```
GET https://www.justice.gov/multimedia-search?keys={query}&page={page}
```

Returns JSON with Elasticsearch-style results.

## Search Syntax

### Supported

| Pattern | Example | Description |
|---------|---------|-------------|
| Basic search | `flight logs` | Matches documents containing these terms |
| Exact phrase | `"flight logs"` | Matches exact phrase |
| Wildcard `*` | `fl*ght`, `maxw*` | Matches any characters |
| Wildcard `?` | `flight?` | Matches single character |
| Required terms | `+flight +logs` | Both terms must appear |

### Not Supported

| Pattern | Example | Notes |
|---------|---------|-------|
| Boolean AND/OR/NOT | `flight AND logs` | Does not work |
| Exclude terms | `flight -private` | Does not work |
| Regex | `/flight.*/` | Treated as literal text |
| Fuzzy search | `maxwell~` | Does not expand to catch typos |
| Field filters | `source:DataSet9` | Not supported |
| Date range | - | Not supported |

Note: There is no automatic typo correction. `epstein` returns 589k results while `epstien` (typo) returns only 428. Use wildcards like `epst?in` to catch spelling variations.

## Response Structure

Each search result contains:

```json
{
  "_source": {
    "documentId": "a6ac544f",
    "ORIGIN_FILE_NAME": "EFTA02185794.pdf",
    "ORIGIN_FILE_URI": "https://www.justice.gov/epstein/files/DataSet 10/EFTA02185794.pdf",
    "key": "DataSet 10/EFTA02185794.pdf",
    "contentType": "application/pdf",
    "fileSize": 49404,
    "totalWords": 186,
    "totalCharacters": 927,
    "startPage": 1,
    "endPage": 1,
    "chunkIndex": 0,
    "totalChunks": 1,
    "processedAt": "2026-01-30T15:54:42Z",
    "indexedAt": "2026-01-30T15:54:42Z"
  },
  "highlight": {
    "content": [
      "...text snippet with <em>matched</em> terms..."
    ]
  }
}
```

### Fields

| Field | Description |
|-------|-------------|
| `documentId` | Unique document identifier |
| `ORIGIN_FILE_NAME` | PDF filename (e.g., `EFTA02185794.pdf`) |
| `ORIGIN_FILE_URI` | Full URL to download the PDF |
| `key` | Dataset path (e.g., `DataSet 10/EFTA02185794.pdf`) |
| `contentType` | MIME type (usually `application/pdf`) |
| `fileSize` | File size in bytes |
| `totalWords` | Word count in document |
| `totalCharacters` | Character count |
| `startPage`, `endPage` | Page range for this chunk |
| `chunkIndex`, `totalChunks` | Chunk info (large docs are split) |
| `processedAt`, `indexedAt` | Timestamps |
| `highlight.content` | Text snippets with `<em>` tags around matches |

## SearchResult Object

The client parses results into `SearchResult` objects:

```python
@dataclass
class SearchResult:
    document_id: str
    filename: str
    url: str
    start_page: Optional[int]
    end_page: Optional[int]
    chunk_index: Optional[int]
    total_chunks: Optional[int]
    content_type: Optional[str]
    text: Optional[str]
    score: Optional[float]
    raw: dict  # Full API response for this hit
```

## Notes

- The API returns 10 results per page; the client automatically paginates
- Full document text is not returned, only highlighted snippets
- Download the PDF from `url` to get full content
- Large documents are chunked; the same PDF may appear multiple times with different `chunkIndex` values
- No authentication required (just needs `Referer` header)

## Legal Considerations

This client accesses the DOJ's public search API for documents released under the Epstein Files Transparency Act.

### Considerations

| Factor | Status |
|--------|--------|
| Data is public records | ✅ Released under Epstein Files Transparency Act |
| API is publicly accessible | ✅ No authentication required |
| robots.txt | ✅ `/multimedia-search` is not disallowed |
| Age verification | ✅ DOJ prompts when opening PDF links |
| Bot protection | ⚠️ Client uses browser-like headers |

### robots.txt

The DOJ's robots.txt disallows `/search/` but does **not** disallow `/multimedia-search` (the endpoint this client uses).

### Best practices

1. **Rate limit your requests** - Don't hammer the server
2. **Identify your client** - The client sets a browser-like User-Agent
3. **Credit the source** - Data comes from the U.S. Department of Justice
4. **Research/journalism use** - This tool is intended for legitimate research

### Disclaimer

This is not legal advice. If you have concerns about your specific use case, consult an attorney. This client simply provides programmatic access to the same public API that the DOJ's own website uses.

## Disclaimer

This software is provided for research and educational purposes only. The author takes no responsibility for how this tool is used. Users are solely responsible for ensuring their use complies with all applicable laws and regulations. The author makes no warranties about the accuracy, completeness, or reliability of the data accessed through this tool.

## License

MIT - See [LICENSE](LICENSE) for full terms.
