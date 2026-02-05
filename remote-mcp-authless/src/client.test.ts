/// <reference types="vitest/globals" />
import { EpsteinClient } from "./client";

describe("EpsteinClient", () => {
    let client: EpsteinClient;

    beforeEach(() => {
        client = new EpsteinClient();
        // Reset fetch mock
        vi.stubGlobal("fetch", vi.fn());
    });

    it("should fetch search results correctly", async () => {
        const mockResponse = {
            hits: {
                total: { value: 1, relation: "eq" },
                hits: [
                    {
                        _id: "test-id",
                        _score: 1.0,
                        _source: {
                            documentId: "doc-1",
                            ORIGIN_FILE_NAME: "test.pdf",
                            ORIGIN_FILE_URI: "https://example.com/test.pdf",
                            startPage: 1,
                            endPage: 5
                        },
                        highlight: {
                            content: ["<em>match</em>"]
                        }
                    }
                ]
            }
        };

        vi.mocked(fetch).mockResolvedValue({
            ok: true,
            json: async () => mockResponse,
        } as Response);

        const results = await client.search("test", 10, 0);

        expect(results).toHaveLength(1);
        expect(results[0].filename).toBe("test.pdf");
        expect(results[0].url).toBe("https://example.com/test.pdf");
        expect(results[0].highlights).toContain("<em>match</em>");
        
        expect(fetch).toHaveBeenCalledWith(
            expect.stringContaining("keys=test"),
            expect.objectContaining({
                headers: expect.objectContaining({
                    "Referer": "https://www.justice.gov/epstein/search"
                })
            })
        );
    });

    it("should handle pagination (multiple pages)", async () => {
        // Mock first page with 10 results, second with 5
        const firstPageHits = Array.from({ length: 10 }, (_, i) => ({
            _id: `id-${i}`,
            _score: 1.0,
            _source: {
                documentId: `doc-${i}`,
                ORIGIN_FILE_NAME: `file-${i}.pdf`,
                ORIGIN_FILE_URI: `https://example.com/file-${i}.pdf`
            }
        }));

        const secondPageHits = Array.from({ length: 5 }, (_, i) => ({
            _id: `id-${i + 10}`,
            _score: 1.0,
            _source: {
                documentId: `doc-${i + 10}`,
                ORIGIN_FILE_NAME: `file-${i + 10}.pdf`,
                ORIGIN_FILE_URI: `https://example.com/file-${i + 10}.pdf`
            }
        }));

        vi.mocked(fetch)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({ hits: { total: 15, hits: firstPageHits } }),
            } as Response)
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({ hits: { total: 15, hits: secondPageHits } }),
            } as Response);

        const results = await client.search("test", 15, 0);

        expect(results).toHaveLength(15);
        expect(fetch).toHaveBeenCalledTimes(2);
        expect(fetch).toHaveBeenLastCalledWith(
            expect.stringContaining("page=1"),
            expect.any(Object)
        );
    });

    it("should handle skip parameter correctly", async () => {
        const hits = Array.from({ length: 10 }, (_, i) => ({
            _id: `id-${i}`,
            _score: 1.0,
            _source: {
                documentId: `doc-${i}`,
                ORIGIN_FILE_NAME: `file-${i}.pdf`,
                ORIGIN_FILE_URI: `https://example.com/file-${i}.pdf`
            }
        }));

        vi.mocked(fetch).mockResolvedValue({
            ok: true,
            json: async () => ({ hits: { total: 10, hits: hits } }),
        } as Response);

        // Skip 5, get 2
        const results = await client.search("test", 2, 5);

        expect(results).toHaveLength(2);
        expect(results[0].documentId).toBe("doc-5");
        expect(results[1].documentId).toBe("doc-6");
    });
});
