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
        default=0,
        help="Number of results (default: 0 = all)"
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
    parser.add_argument(
        "-e", "--events",
        action="store_true",
        help="Extract events with timestamps from PDFs using AI"
    )
    parser.add_argument(
        "-m", "--model",
        type=str,
        default=None,
        help="OpenRouter model ID for --events (default: deepseek/deepseek-chat-v3-0324:free)"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=10,
        help="Number of parallel workers for --events (default: 10)"
    )

    args = parser.parse_args()

    if not args.query:
        parser.print_help()
        sys.exit(1)

    client = EpsteinClient()
    queries = [q.strip() for q in args.query.split("|")]

    if args.count:
        if len(queries) > 1:
            print("Error: --count does not support OR queries", file=sys.stderr)
            sys.exit(1)
        print(client.count(args.query))
        return

    n = args.n if args.n > 0 else None

    if args.events:
        results = client.search(queries, n=n or 1, skip=args.skip)
        if args.json:
            print("[", flush=True)
            first = True
            for r in client._extract_events(results, model=args.model, query=args.query, workers=args.workers):
                if r.events:
                    entry = {"filename": r.filename, "url": encode_url(r.url), "events": [e.model_dump() for e in r.events]}
                    if not first:
                        print(",", flush=True)
                    print(json.dumps(entry, indent=2), end="", flush=True)
                    first = False
            print("\n]", flush=True)
        else:
            for r in client._extract_events(results, model=args.model, query=args.query, workers=args.workers):
                print(f"\n--- {r.filename} " + "-" * (55 - len(r.filename)))
                print(encode_url(r.url))
                if r.events:
                    for e in r.events:
                        loc = f" @ {e.location}" if e.location else ""
                        print(f"  [{e.timestamp}]{loc} {e.summary}")
        return

    if args.text:
        results = client.search(queries, n=n or 1, skip=args.skip)
        for r in client._extract_text(results):
            print(f"\n\n--- {r.filename} " + "-" * (55 - len(r.filename)))
            print(encode_url(r.url) + "\n")
            print(r.text)
        return

    results = client.search(queries, n=n, skip=args.skip)

    if args.json:
        print("[", flush=True)
        first = True
        for r in results:
            if r.raw:
                raw = r.raw.copy()
                src = raw.get("_source", {})
                if "ORIGIN_FILE_URI" in src:
                    raw["_source"] = {**src, "ORIGIN_FILE_URI": encode_url(src["ORIGIN_FILE_URI"])}
                if not first:
                    print(",", flush=True)
                print(json.dumps(raw, indent=2), end="", flush=True)
                first = False
        print("\n]", flush=True)
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
