# epstein-search

> **Content Warning:** This tool searches documents released under the Epstein Files Transparency Act. Results may contain disturbing textual descriptions of sexual abuse. Users must be 18 or older.

Python client, CLI, and MCP server for searching ~1M OCR'd Epstein documents via the vector search API.

## Contributors

⭐ [@CultriX-Github](https://github.com/CultriX-Github) - Thanks for leveling up this tool!

## Installation

```bash
# Install the `es` command globally
uv tool install git+https://git.corroborators.wiki/korroni/epstein-search

# Or install from a local clone
git clone https://git.corroborators.wiki/korroni/epstein-search
uv tool install ./epstein-search
```

## CLI

```bash
# Keyword search (default, returns 20 results)
es "maxwell"
es "Maxwell OR Brunel"
es '"wire transfer"'          # exact phrase
es "island -vacation"         # exclude term
es "maxw*"                    # wildcard prefix

# Semantic vector search (finds by meaning, not keywords)
es "payments to politicians" --vector
es "discussions about underage girls" --vector -n 10

# Fuzzy search (typo-tolerant, catches OCR errors)
es "Maxwel" --fuzzy
es "Ghisliane" --fuzzy --exclude-exact

# Find documents similar to a known document
es --similar EFTA00123456
es --similar EFTA00123456 --chunk 2

# Fetch a single document by ID
es --doc EFTA00123456

# Control output
es "flight logs" -n 100      # number of results
es "epstein" --json           # JSON output
es --version                  # show version
```

### Options

| Flag | Description |
|------|-------------|
| `-n N` | Number of results (default: 20) |
| `-j, --json` | Output as JSON |
| `-V, --version` | Show version |
| `--vector` | Semantic search (by meaning, not keywords) |
| `--fuzzy` | Typo-tolerant trigram search |
| `--exclude-exact` | With `--fuzzy`, hide results that keyword search already finds |
| `--similar EFTA_ID` | Find documents similar to this one |
| `--chunk N` | Chunk index for `--similar` (default: 0) |
| `--doc EFTA_ID` | Fetch a single document by EFTA ID |
| `--vector-url URL` | Custom API URL (default: `VECTOR_URL` env or `https://vector.korroni.cloud`) |

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
| `text_search` | Keyword search — AND, OR, NOT, phrases, wildcards |
| `text_search_count` | Count matching chunks without returning results |
| `vector_search` | Semantic search — finds documents by meaning |
| `fuzzy_search` | Typo-tolerant search — catches OCR errors |
| `fuzzy_search_count` | Count matching chunks for fuzzy queries |
| `similarity_search` | Find documents similar to a given document |
| `get_document` | Fetch a single document by EFTA ID |
| `extract_image` | Download a PDF and extract embedded images |
| `generate_pdf` | Convert markdown to a styled PDF |
| `merge_markdown_to_pdf` | Merge multiple markdown files into one PDF |

## Updating

```bash
# Reinstall from remote
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
from client import SearchClient

vc = SearchClient()  # defaults to https://vector.korroni.cloud

# Keyword search
for r in vc.text_search("Maxwell flight", limit=10):
    print(r["efta_id"], r["headline"])

# Semantic vector search
for r in vc.search("payments to politicians", limit=10):
    print(r["efta_id"], r["score"], r["text"][:100])

# Fuzzy search (typo-tolerant)
for r in vc.fuzzy_search("Maxwel", limit=10):
    print(r["efta_id"], r["similarity"], r["text"][:100])

# Find similar documents
for r in vc.similarity_search("EFTA00123456", limit=10):
    print(r["efta_id"], r["score"], r["text"][:100])

# Fetch a single document
doc = vc.get_document("EFTA00123456")
print(doc["text"])

# Count matching documents
print(vc.text_search_count("Maxwell"))
print(vc.fuzzy_search_count("Maxwel"))

# Custom server URL
vc = SearchClient(url="http://localhost:8000", api_key="your-key")
```

## Search Syntax

### Keyword Search (`text_search`)

| Pattern | Example | Description |
|---------|---------|-------------|
| Plain terms | `Maxwell flight` | AND — both must appear |
| Exact phrase | `"wire transfer"` | Matches exact phrase |
| OR | `Maxwell OR Brunel` | Either term |
| NOT | `island -vacation` | Exclude term |
| Wildcard | `maxw*` | Prefix match |

### Vector Search

Phrase queries as descriptive statements, not questions:
- Good: `"recruiting underage girls from schools"`, `"payments to silence victims"`
- Bad: `"did Epstein recruit from schools?"`, `"were victims paid?"`

### Fuzzy Search

Catches OCR errors and misspellings using trigram matching:
- `"Maxwel"` finds `"Maxwell"`
- `"Ghisliane"` finds `"Ghislaine"`

## Disclaimer

This software is provided for research and educational purposes only. The author takes no responsibility for how this tool is used. Users are solely responsible for ensuring their use complies with all applicable laws and regulations. The author makes no warranties about the accuracy, completeness, or reliability of the data accessed through this tool.

## License

MIT - See [LICENSE](LICENSE) for full terms.
