/**
 * TypeScript client for the DOJ Epstein Library search API.
 */

export interface EpsteinSource {
    documentId: string;
    ORIGIN_FILE_NAME: string;
    ORIGIN_FILE_URI: string;
    key?: string;
    contentType?: string;
    fileSize?: number;
    totalWords?: number;
    totalCharacters?: number;
    startPage?: number;
    endPage?: number;
    chunkIndex?: number;
    totalChunks?: number;
    processedAt?: string;
    indexedAt?: string;
    text?: string;
    content?: string;
}

export interface EpsteinHit {
    _index: string;
    _type: string;
    _id: string;
    _score: number;
    _source: EpsteinSource;
    highlight?: {
        content: string[];
    };
}

export interface EpsteinSearchResponse {
    hits: {
        total: number | { value: number; relation: string };
        max_score: number | null;
        hits: EpsteinHit[];
    };
}

export interface SearchResult {
    documentId: string;
    filename: string;
    url: string;
    startPage?: number;
    endPage?: number;
    chunkIndex?: number;
    totalChunks?: number;
    contentType?: string;
    text?: string;
    score: number;
    highlights?: string[];
    raw: EpsteinHit;
}

export interface DocumentMetadata {
    documentId: string;
    filename: string;
    url: string;
    fileSize?: number;
    totalWords?: number;
    totalCharacters?: number;
    contentType?: string;
    processedAt?: string;
    indexedAt?: string;
}

export class EpsteinClient {
    private static BASE_URL = "https://www.justice.gov";
    private static SEARCH_ENDPOINT = "/multimedia-search";

    /**
     * Search the Epstein Library.
     * 
     * Supports advanced search patterns:
     * - Basic search: "flight logs" (matches documents containing these terms)
     * - Exact phrase: "\"flight logs\"" (matches exact phrase)
     * - Wildcard *: "fl*ght", "maxw*" (matches any characters)
     * - Wildcard ?: "flight?" (matches single character)
     * - Required terms: "+flight +logs" (both terms must appear)
     * 
     * @param query Search terms
     * @param n Number of results to return (default: 10)
     * @param skip Number of results to skip (default: 0)
     */
    async search(query: string, n: number = 10, skip: number = 0): Promise<SearchResult[]> {
        const results: SearchResult[] = [];
        let fetched = 0;
        let page = Math.floor(skip / 10);
        const limit = n > 0 ? n : Number.MAX_SAFE_INTEGER;
        const fetchLimit = skip + limit;

        // Skip items within the first page if skip > 0
        let itemsToSkipInFirstPage = skip % 10;

        while (true) {
            const url = new URL(EpsteinClient.SEARCH_ENDPOINT, EpsteinClient.BASE_URL);
            url.searchParams.set("keys", query);
            url.searchParams.set("page", page.toString());

            const response = await fetch(url.toString(), {
                headers: {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                    "Referer": "https://www.justice.gov/epstein/search",
                }
            });

            if (!response.ok) {
                throw new Error(`DOJ API error: ${response.status} ${response.statusText}`);
            }

            const data = (await response.json()) as EpsteinSearchResponse;
            const hits = data.hits.hits || [];

            if (hits.length === 0) {
                break;
            }

            for (const hit of hits) {
                fetched++;
                
                // Handle skipping
                if (itemsToSkipInFirstPage > 0) {
                    itemsToSkipInFirstPage--;
                    continue;
                }

                if (fetched <= skip) {
                    continue;
                }

                const source = hit._source;
                results.push({
                    documentId: source.documentId,
                    filename: source.ORIGIN_FILE_NAME,
                    url: source.ORIGIN_FILE_URI,
                    startPage: source.startPage,
                    endPage: source.endPage,
                    chunkIndex: source.chunkIndex,
                    totalChunks: source.totalChunks,
                    contentType: source.contentType,
                    text: source.text || source.content,
                    score: hit._score,
                    highlights: hit.highlight?.content,
                    raw: hit,
                });

                if (results.length >= limit) {
                    return results;
                }
            }

            const totalInfo = data.hits.total;
            const total = typeof totalInfo === "number" ? totalInfo : totalInfo.value;

            if ((page + 1) * 10 >= total) {
                break;
            }

            page++;
        }

        return results;
    }

    /**
     * Get the total number of results for a query.
     * 
     * @param query Search terms
     */
    async count(query: string): Promise<number> {
        const url = new URL(EpsteinClient.SEARCH_ENDPOINT, EpsteinClient.BASE_URL);
        url.searchParams.set("keys", query);
        url.searchParams.set("page", "0");

        const response = await fetch(url.toString(), {
            headers: {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Referer": "https://www.justice.gov/epstein/search",
            }
        });

        if (!response.ok) {
            throw new Error(`DOJ API error: ${response.status} ${response.statusText}`);
        }

        const data = (await response.json()) as EpsteinSearchResponse;
        const totalInfo = data.hits.total;
        return typeof totalInfo === "number" ? totalInfo : totalInfo.value;
    }

    /**
     * Get metadata for a specific document by filename.
     * 
     * @param filename The filename to look up (e.g., "EFTA02185794.pdf")
     */
    async getMetadata(filename: string): Promise<DocumentMetadata | null> {
        const url = new URL(EpsteinClient.SEARCH_ENDPOINT, EpsteinClient.BASE_URL);
        // Search for the exact filename
        url.searchParams.set("keys", `"${filename}"`);
        url.searchParams.set("page", "0");

        const response = await fetch(url.toString(), {
            headers: {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Referer": "https://www.justice.gov/epstein/search",
            }
        });

        if (!response.ok) {
            throw new Error(`DOJ API error: ${response.status} ${response.statusText}`);
        }

        const data = (await response.json()) as EpsteinSearchResponse;
        const hits = data.hits.hits || [];

        if (hits.length === 0) {
            return null;
        }

        // Find the best match (exact filename match preferred)
        const hit = hits.find(h => h._source.ORIGIN_FILE_NAME === filename) || hits[0];
        const source = hit._source;

        return {
            documentId: source.documentId,
            filename: source.ORIGIN_FILE_NAME,
            url: source.ORIGIN_FILE_URI,
            fileSize: source.fileSize,
            totalWords: source.totalWords,
            totalCharacters: source.totalCharacters,
            contentType: source.contentType,
            processedAt: source.processedAt,
            indexedAt: source.indexedAt,
        };
    }
}
