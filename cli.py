#!/usr/bin/env python3
"""
CLI for the DOJ Epstein Library search.

Usage:
    python cli.py "search query"
    python cli.py "maxwell" --limit 50
    python cli.py "flight logs" --json
"""

import argparse
import json
import sys
from urllib.parse import quote
from client import EpsteinClient


def encode_url(url: str) -> str:
    """Encode spaces in URL to make it clickable."""
    return url.replace(" ", "%20")


def main():
    parser = argparse.ArgumentParser(
        description="Search the DOJ Epstein Library",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python cli.py "maxwell"
    python cli.py "flight logs" --limit 50
    python cli.py "epstein" --json > results.json
    python cli.py "EFTA00420915" --limit 1
        """
    )
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="epstein-search 0.1.0"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10,
        help="Maximum number of results (default: 10, use 0 for all)"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--urls-only", "-u",
        action="store_true",
        help="Only output PDF URLs (one per line)"
    )

    args = parser.parse_args()

    if not args.query:
        parser.print_help()
        sys.exit(1)

    client = EpsteinClient()

    limit = args.limit if args.limit > 0 else None
    results = client.search(args.query, limit=limit)

    if args.json:
        output = [r.raw for r in results if r.raw]
        print(json.dumps(output, indent=2))
    elif args.urls_only:
        for r in results:
            print(encode_url(r.url))
    else:
        for r in results:
            print(encode_url(r.url))
            if r.raw:
                highlights = r.raw.get("highlight", {}).get("content", [])
                for h in highlights:
                    text = h.replace("\n", " ").strip()
                    print(f"  {text}")
            print()


if __name__ == "__main__":
    main()
