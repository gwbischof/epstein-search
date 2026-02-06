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
        "--version", "-V",
        action="version",
        version="epstein-search 0.1.0"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print all metadata for each result"
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
    elif args.verbose:
        for r in results:
            if r.raw:
                source = r.raw.get("_source", {})
                filename = source.get('ORIGIN_FILE_NAME', 'unknown')
                print(f"\n\n--- {filename} " + "-" * (55 - len(filename)) + "\n")
                # Find max key length for alignment
                max_len = max(len(k) for k in source.keys()) if source else 0
                for key, value in source.items():
                    print(f"{key}:{' ' * (max_len - len(key) + 1)}{value}")
                score = r.raw.get('_score')
                if score:
                    print(f"{'_score'}:{' ' * (max_len - len('_score') + 1)}{score}")
                highlights = r.raw.get("highlight", {}).get("content", [])
                if highlights:
                    print("highlights:")
                    for h in highlights:
                        text = h.replace("\n", " ").strip()
                        print(f"  {text}")
            else:
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
