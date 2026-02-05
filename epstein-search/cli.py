#!/usr/bin/env python3
"""
CLI for the DOJ Epstein Library search.

Usage:
    es "search query"
    es "maxwell" -n 100
    es "flight logs" --json
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
    es "maxwell"
    es "flight logs" -n 100
    es "epstein" --json > results.json
        """
    )
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="epstein-search 0.1.0"
    )
    parser.add_argument(
        "-n",
        type=int,
        default=50,
        help="Number of results (default: 50, use 0 for all)"
    )
    parser.add_argument(
        "-s", "--skip",
        type=int,
        default=0,
        help="Skip first N results (default: 0)"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    if not args.query:
        parser.print_help()
        sys.exit(1)

    client = EpsteinClient()
    n = args.n if args.n > 0 else None
    results = client.search(args.query, n=n, skip=args.skip)

    if args.json:
        output = [r.raw for r in results if r.raw]
        print(json.dumps(output, indent=2))
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
