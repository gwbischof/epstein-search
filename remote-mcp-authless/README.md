# Epstein Search MCP Server (Cloudflare Workers)

This is a Model Context Protocol (MCP) server deployed on Cloudflare Workers that provides search capabilities for the DOJ Epstein Library.

## Features

- **search_epstein_library**: Search the DOJ Epstein Library for public documents, flight logs, and evidence.
- **Edge Deployment**: Runs on Cloudflare Workers for low-latency access.
- **Automatic Pagination**: Handles large result sets via `n` and `skip` parameters.
- **Rich Metadata**: Returns PDF links, page ranges, and highlighted snippets.

## Deployment

The server is currently deployed at:
`https://remote-mcp-server-authless.j78workers.workers.dev/mcp`

To deploy your own instance:
```bash
npm run deploy
```

## Local Development

1. Install dependencies:
```bash
npm install
```

2. Run in development mode:
```bash
npm start
```

3. Run tests:
```bash
npm test
```

## Connecting to the MCP Server

### Using mcp-remote proxy

To connect to this remote MCP server from local clients (like Claude Desktop), use the [mcp-remote](https://www.npmjs.com/package/mcp-remote) proxy:

```json
{
  "mcpServers": {
    "epstein-search": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://remote-mcp-server-authless.j78workers.workers.dev/mcp"
      ]
    }
  }
}
```

### Direct Agent Integration

If you are using the Cloudflare `agents` SDK, you can connect directly to the `/mcp` endpoint.