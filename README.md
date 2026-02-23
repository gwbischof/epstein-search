# epstein-search

> **Content Warning:** This tool searches documents released under the Epstein Files Transparency Act. Results may contain disturbing textual descriptions of sexual abuse. Users must be 18 or older.

Python and CLI client for the DOJ Epstein Library search API.

## Contributors

⭐ [@CultriX-Github](https://github.com/CultriX-Github) - Thanks for leveling up this tool!

## Installation

The easiest way to install this tool may be to ask your AI coding agent to do it for you. It can install and use the CLI based on the instructions in this README.

```bash
# Install the `es` command globally
uv tool install git+https://git.corroborators.wiki/korroni/epstein-search

# Or install from a local clone
git clone https://git.corroborators.wiki/korroni/epstein-search
uv tool install ./epstein-search
```

## CLI

```bash
# Basic search (returns 50 results by default)
es "maxwell"

# OR search (results interleaved, deduplicated by document)
es "pizza | flights" -n 10

# Combine AND (+) with OR (|): docs with (epstein AND dog) OR (pizza AND cat)
es "+epstein +dog | +pizza +cat" -n 10

# Multiple OR terms
es "pizza | flights | maxwell" -n 15

# Specify number of results
es "flight logs" -n 100

# Verbose output (show all metadata)
es "trump" -n 5 -v

# Get total count without fetching results
es "epstein" -c

# Extract full text from matching PDFs (downloaded and processed in memory)
es "flight logs" -t -n 1

# Skip first 10 results
es "maxwell" -s 10

# Output as JSON
es "epstein" --json > results.json

# Semantic vector search (finds by meaning, not keywords)
es "payments to politicians" --vector
es "discussions about underage girls" --vector -n 10
es "threats and intimidation" --vector --json

# Check version
es --version
```

Options:
- `|` - OR operator: `"pizza | flights"` runs separate queries, interleaves results round-robin, and deduplicates by document. Works with or without spaces around `|`.
- `-n` - Number of results (default: 50, use 0 for all)
- `-s, --skip` - Skip first N results (default: 0)
- `-v, --verbose` - Show all metadata fields for each result
- `-t, --text` - Download PDFs in memory and extract full text
- `-c, --count` - Only show total result count (fast, single API call)
- `-j, --json` - Output results as JSON
- `-V, --version` - Show version
- `--vector` - Use semantic vector search instead of keyword search
- `--keyword` - Use keyword search via vector API (supports AND, OR, NOT, phrases, wildcards). Returns chunk-level results with `chunk_index` and `total_chunks`
- `--fuzzy` - Use fuzzy trigram search via vector API (typo-tolerant matching)
- `--exclude-exact` - With `--fuzzy`, hide documents that keyword search already finds
- `--similar EFTA_ID` - Find documents similar to this EFTA ID (via vector API)
- `--chunk N` - Chunk index for `--similar` (default: 0)
- `--vector-url` - Custom vector search API URL (default: `VECTOR_URL` env or `https://vector.korroni.cloud`)

## MCP Server

An MCP server that gives AI assistants (Claude Code, Claude Desktop, etc.) direct access to search ~1M Epstein documents.

### Setup

```bash
# Clone the repo
git clone https://git.corroborators.wiki/korroni/epstein-search
cd epstein-search

# Install the MCP server into Claude Code
claude mcp add -s user epstein-search \
  -e VECTOR_API_KEY=your-api-key \
  -- uvx --from /path/to/epstein-search epstein-search-mcp
```

Replace `/path/to/epstein-search` with the actual path to your clone, and `your-api-key` with a vector search API key.

To update, `git pull` and restart Claude Code. To change settings, remove and re-add:

```bash
claude mcp remove -s user epstein-search
```

### Tools

| Tool | Description |
|------|-------------|
| `text_search` | Keyword search — supports AND, OR, NOT, phrases, wildcards |
| `text_search_count` | Count chunks matching a keyword query (without returning results) |
| `vector_search` | Semantic search — finds documents by meaning, not keywords |
| `fuzzy_search` | Typo-tolerant search — catches OCR errors and misspellings |
| `fuzzy_search_count` | Count chunks matching a fuzzy query (without returning results) |
| `similarity_search` | Find documents similar to a given document |
| `extract_text` | Download a PDF and extract its full text |
| `extract_image` | Download a PDF and extract embedded images |
| `generate_pdf` | Convert markdown to a styled PDF |
| `merge_markdown_to_pdf` | Merge multiple markdown files into one PDF |

## Updating

```bash
# Reinstall from GitHub
uv tool install --force --reinstall epstein-search --from git+https://git.corroborators.wiki/korroni/epstein-search

# Or from a local clone
uv tool install --force --reinstall epstein-search --from /path/to/epstein-search
```

## Python Usage

```bash
# Install as a library
uv add git+https://git.corroborators.wiki/korroni/epstein-search
```

```python
from client import EpsteinClient, VectorClient

client = EpsteinClient()

# search() is a generator — iterate or collect with list()
for r in client.search("Maxwell", n=10):
    print(r.filename, r.url)

# OR search — pass a list of queries (interleaved, deduplicated by document)
for r in client.search(["pizza", "flights"], n=10):
    print(r.filename, r.url)

# AND + OR: docs with (epstein AND dog) OR (pizza AND cat)
for r in client.search(["+epstein +dog", "+pizza +cat"], n=10):
    print(r.filename, r.url)

# Skip first 50, get next 100
for r in client.search("flight logs", n=100, skip=50):
    print(r.filename)

# Get ALL results (no limit - may be slow for broad queries)
for r in client.search("Trump"):
    print(r.filename)

# Get total count for a query (without fetching all results)
count = client.count("Maxwell")
print(f"Total results: {count}")

# Semantic vector search (finds by meaning, not exact keywords)
vc = VectorClient()  # defaults to https://vector.korroni.cloud
for r in vc.search("payments to politicians", limit=10):
    print(r["efta_id"], r["score"], r["text"][:100])

# Keyword search via vector API
for r in vc.text_search("Maxwell flight", limit=10):
    print(r["efta_id"], r["headline"])

# Fuzzy search (typo-tolerant)
for r in vc.fuzzy_search("Maxwel", limit=10):
    print(r["efta_id"], r["similarity"], r["text"][:100])

# Count matching documents
print(vc.text_search_count("Maxwell"))
print(vc.fuzzy_search_count("Maxwel"))

# Custom server URL
vc = VectorClient(url="http://localhost:8000", api_key="your-key")
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
| Boolean AND/NOT | `flight AND logs` | Does not work (use `|` for OR via CLI) |
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

## Record Object

The client parses results into `Record` objects:

```python
@dataclass
class Record:
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
    text: Optional[str] = None        # Populated when text=True
    raw: dict = None                   # Full API response for this hit
```

## Notes

- The API returns 10 results per page; the client automatically paginates
- By default only highlighted snippets are returned; use `text=True` to download and extract full PDF text
- You can also download the PDF directly from `url`
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
