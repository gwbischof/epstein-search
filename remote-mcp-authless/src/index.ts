import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { McpAgent } from "agents/mcp";
import { z } from "zod";
import { EpsteinClient } from "./client.js";

// Define our MCP agent with tools
export class MyMCP extends McpAgent {
	server = new McpServer({
		name: "Epstein Search MCP",
		version: "1.0.0",
	});

	private client = new EpsteinClient();

	async init() {
		// Epstein Library Search Tool
		this.server.tool(
			"search_epstein_library",
			`Search the DOJ Epstein Library for public documents, flight logs, and related evidence.
Supports advanced search patterns:
- Basic search: "flight logs" (matches documents containing these terms)
- Exact phrase: "\\"flight logs\\"" (matches exact phrase)
- Wildcard *: "fl*ght", "maxw*" (matches any characters)
- Wildcard ?: "flight?" (matches single character)
- Required terms: "+flight +logs" (both terms must appear)`,
			{
				query: z.string().describe("Search terms or exact phrases (e.g., 'flight logs', 'Maxwell')"),
				n: z.number().optional().default(10).describe("Number of results to return"),
				skip: z.number().optional().default(0).describe("Number of results to skip"),
			},
			async ({ query, n, skip }) => {
				try {
					const results = await this.client.search(query, n, skip);
					
					if (results.length === 0) {
						return {
							content: [{ type: "text", text: `No documents found matching: "${query}"` }],
						};
					}

					const formattedResults = results.map(r => {
						let text = `File: ${r.filename}\nURL: ${r.url}\n`;
						if (r.startPage) text += `Pages: ${r.startPage}-${r.endPage}\n`;
						if (r.highlights && r.highlights.length > 0) {
							text += `Highlights:\n${r.highlights.map(h => `- ${h.replace(/<em>/g, "").replace(/<\/em>/g, "")}`).join("\n")}\n`;
						}
						return text;
					}).join("\n---\n\n");

					return {
						content: [
							{
								type: "text",
								text: `Found ${results.length} documents for query "${query}":\n\n${formattedResults}`,
							},
						],
					};
				} catch (error) {
					return {
						isError: true,
						content: [
							{
								type: "text",
								text: `Error searching Epstein Library: ${error instanceof Error ? error.message : String(error)}`,
							},
						],
					};
				}
			},
		);

		// Epstein Library Count Tool
		this.server.tool(
			"count_epstein_library",
			`Get the total number of documents matching a query in the DOJ Epstein Library.
Supports advanced search patterns:
- Basic search: "flight logs" (matches documents containing these terms)
- Exact phrase: "\\"flight logs\\"" (matches exact phrase)
- Wildcard *: "fl*ght", "maxw*" (matches any characters)
- Wildcard ?: "flight?" (matches single character)
- Required terms: "+flight +logs" (both terms must appear)`,
			{
				query: z.string().describe("Search terms or exact phrases (e.g., 'flight logs', 'Maxwell')"),
			},
			async ({ query }) => {
				try {
					const count = await this.client.count(query);
					return {
						content: [
							{
								type: "text",
								text: `Found ${count} documents matching query "${query}"`,
							},
						],
					};
				} catch (error) {
					return {
						isError: true,
						content: [
							{
								type: "text",
								text: `Error counting Epstein Library results: ${error instanceof Error ? error.message : String(error)}`,
							},
						],
					};
				}
			},
		);

		// Epstein Library Document Metadata Tool
		this.server.tool(
			"get_epstein_document_metadata",
			"Get detailed metadata for a specific document in the Epstein Library, including file size, word count, and download URL.",
			{
				filename: z.string().describe("The exact filename of the document (e.g., 'EFTA02185794.pdf')"),
			},
			async ({ filename }) => {
				try {
					const metadata = await this.client.getMetadata(filename);
					
					if (!metadata) {
						// Fallback: Check epsteinfilez.com for EFTA documents
						const eftaMatch = filename.match(/^(EFTA\d+)\.pdf$/i);
						if (eftaMatch) {
							const baseName = eftaMatch[1];
							const fallbackUrl = `https://epsteinfilez.com/?q=${baseName}&page=1`;
							
							try {
								const response = await fetch(fallbackUrl, {
									headers: {
										"User-Agent": "Mozilla/5.0 (compatible; EpsteinSearchMCP/1.0)"
									}
								});

								if (response.ok) {
									const text = await response.text();
									// If the page doesn't say "No documents found" or "0 results found", assume we found something
									if (!text.includes("No documents found") && !text.includes("0 results found")) {
										return {
											content: [{
												type: "text",
												text: `Document not found in DOJ Library, but a potential match was found on EpsteinFilez:\n${fallbackUrl}`
											}],
										};
									}
								}
							} catch (e) {
								// Silently fail fallback and return original error
								console.error("Fallback fetch failed:", e);
							}
						}

						return {
							content: [{ type: "text", text: `Document not found: "${filename}"` }],
						};
					}

					return {
						content: [
							{
								type: "text",
								text: `Metadata for ${metadata.filename}:\n` +
									  `URL: ${metadata.url}\n` +
									  `Document ID: ${metadata.documentId}\n` +
									  `File Size: ${metadata.fileSize} bytes\n` +
									  `Total Words: ${metadata.totalWords}\n` +
									  `Total Characters: ${metadata.totalCharacters}\n` +
									  `Content Type: ${metadata.contentType}\n` +
									  `Processed At: ${metadata.processedAt}\n` +
									  `Indexed At: ${metadata.indexedAt}`,
							},
						],
					};
				} catch (error) {
					return {
						isError: true,
						content: [
							{
								type: "text",
								text: `Error getting document metadata: ${error instanceof Error ? error.message : String(error)}`,
							},
						],
					};
				}
			},
		);
	}
}

export default {
	fetch(request: Request, env: Env, ctx: ExecutionContext) {
		const url = new URL(request.url);

		if (url.pathname.startsWith("/mcp")) {
			return MyMCP.serve("/mcp").fetch(request, env, ctx);
		}

		return new Response("Not found", { status: 404 });
	},
};