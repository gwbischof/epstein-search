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
    parser.add_argument(
        "-c", "--count",
        action="store_true",
        help="Only show total result count"
    )
    parser.add_argument(
        "-t", "--text",
        action="store_true",
        help="Download PDFs and extract text"
    )

    args = parser.parse_args()

    if not args.query:
        parser.print_help()
        sys.exit(1)

    client = EpsteinClient()

    if args.count:
        print(client.count(args.query))
        return

    n = args.n if args.n > 0 else None

    if args.text:
        results = client.search(args.query, n=n or 1, skip=args.skip, text=True)
        for r in results:
            print(f"\n\n--- {r.filename} " + "-" * (55 - len(r.filename)))
            print(encode_url(r.url) + "\n")
            print(r.text)
        return

    results = client.search(args.query, n=n, skip=args.skip)

    if args.json:
        output = [r.raw for r in results if r.raw]
        print(json.dumps(output, indent=2))
    elif args.verbose:
        from dataclasses import fields
        for r in results:
            print(f"\n\n--- {r.filename} " + "-" * (55 - len(r.filename)) + "\n")
            field_names = [f.name for f in fields(r) if f.name not in ('raw', 'highlights')]
            max_len = max(len(name) for name in field_names)
            for name in field_names:
                value = getattr(r, name)
                if name == 'url' and value:
                    value = encode_url(value)
                print(f"{name}:{' ' * (max_len - len(name) + 1)}{value}")
            if r.highlights:
                print("highlights:")
                for h in r.highlights:
                    print(f"  {h.replace(chr(10), ' ').strip()}")
    else:
        for r in results:
            print(encode_url(r.url))
            if r.highlights:
                for h in r.highlights:
                    text = h.replace("\n", " ").strip()
                    print(f"  {text}")
            print()


if __name__ == "__main__":
    main()
