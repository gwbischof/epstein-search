#!/usr/bin/env python3
"""
CLI for searching the Epstein Library via the vector API.

Usage:
    es "search query"
    es "maxwell" -n 100
    es "flight logs" --json
    es --doc EFTA00123456
"""

import argparse
import json
import sys
from client import SearchClient


def main():
    parser = argparse.ArgumentParser(
        description="Search the Epstein Library",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    es "maxwell"                          # keyword search (default)
    es "flight logs" -n 100
    es "flight logs" --vector             # semantic search
    es "Maxwel" --fuzzy                   # typo-tolerant search
    es --similar EFTA00123456             # find similar docs
    es --doc EFTA00123456                 # fetch a single document
    es "epstein" --json > results.json
        """
    )
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument(
        "--version", "-V",
        action="version",
        version="epstein-search 0.2.0"
    )
    parser.add_argument(
        "-n",
        type=int,
        default=20,
        help="Number of results (default: 20)"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--vector",
        action="store_true",
        help="Use semantic vector search instead of keyword search"
    )
    parser.add_argument(
        "--vector-url",
        type=str,
        default=None,
        help="Vector search API URL (default: VECTOR_URL env or https://vector.korroni.cloud)"
    )
    parser.add_argument(
        "--fuzzy",
        action="store_true",
        help="Use fuzzy trigram search (typo-tolerant matching)"
    )
    parser.add_argument(
        "--exclude-exact",
        action="store_true",
        help="With --fuzzy, hide documents that keyword search already finds"
    )
    parser.add_argument(
        "--similar",
        type=str,
        default=None,
        metavar="EFTA_ID",
        help="Find documents similar to this EFTA ID"
    )
    parser.add_argument(
        "--chunk",
        type=int,
        default=0,
        help="Chunk index for --similar (default: 0)"
    )
    parser.add_argument(
        "--doc",
        type=str,
        default=None,
        metavar="EFTA_ID",
        help="Fetch a single document by EFTA ID"
    )

    args = parser.parse_args()
    vc = SearchClient(url=args.vector_url)

    if args.doc:
        try:
            doc = vc.get_document(args.doc)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        if args.json:
            print(json.dumps(doc, indent=2))
        else:
            print(f"{doc['efta_id']}  (dataset {doc['dataset']}, {doc['word_count']} words, {doc['pages']} pages, v{doc['version']})")
            print(f"  {doc.get('url', '')}")
            if doc.get("text"):
                print()
                print(doc["text"])
        return

    if not args.query:
        parser.print_help()
        sys.exit(1)

    if args.similar:
        results = vc.similarity_search(args.similar, chunk_index=args.chunk, limit=args.n)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"Documents similar to {args.similar} (chunk {args.chunk}):\n")
            for r in results:
                print(f"{r['efta_id']}  (dataset {r['dataset']}, score {r['score']:.3f})")
                text = r["text"][:200].replace("\n", " ")
                print(f"  {text}...")
                print()
        return

    if args.fuzzy:
        results = vc.fuzzy_search(args.query, limit=args.n, exclude_exact=args.exclude_exact)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                text = r.get("text", "")[:200].replace("\n", " ")
                print(f"{r['efta_id']}  (dataset {r['dataset']}, {r['similarity']:.1%} match)")
                print(f"  {text}...")
                print()
        return

    if args.vector:
        results = vc.search(args.query, limit=args.n)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"{r['efta_id']}  (dataset {r['dataset']}, score {r['score']:.3f})")
                text = r["text"][:200].replace("\n", " ")
                print(f"  {text}...")
                print()
        return

    # Default: keyword search
    results = vc.text_search(args.query, limit=args.n)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            headline = r.get("headline", "").replace("<b>", "").replace("</b>", "")
            print(f"{r['efta_id']}  (dataset {r['dataset']}, {r['word_count']} words)")
            print(f"  {headline}")
            print()


if __name__ == "__main__":
    main()
