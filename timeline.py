#!/usr/bin/env python3
"""
Timeline: merge and sort events from appended JSON files.

Usage:
    estl events.json
    estl events.json > sorted.json
"""

import argparse
import json
import sys
from datetime import datetime

from dateutil.parser import parse as dateutil_parse


def parse_concatenated_json(text):
    """Parse concatenated JSON arrays from text."""
    decoder = json.JSONDecoder()
    idx = 0
    results = []
    while idx < len(text):
        ch = text[idx]
        if ch in (' ', '\t', '\n', '\r'):
            idx += 1
            continue
        obj, end = decoder.raw_decode(text, idx)
        results.append(obj)
        idx = end
    return results


def parse_timestamp(ts):
    """Parse a timestamp string into a datetime for sorting."""
    try:
        return dateutil_parse(ts)
    except (ValueError, TypeError):
        return datetime.min


def flatten_events(documents):
    """Flatten document events, attaching filename and url to each event."""
    events = []
    for doc in documents:
        filename = doc.get("filename")
        url = doc.get("url")
        for event in doc.get("events", []):
            flat = dict(event)
            flat["filename"] = filename
            flat["url"] = url
            events.append(flat)
    return events


def main():
    parser = argparse.ArgumentParser(
        description="Merge and sort events from appended JSON files",
    )
    parser.add_argument("file", help="Path to concatenated events JSON file")
    args = parser.parse_args()

    try:
        with open(args.file) as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    all_documents = []
    for chunk in parse_concatenated_json(text):
        if isinstance(chunk, list):
            all_documents.extend(chunk)
        else:
            all_documents.append(chunk)

    events = flatten_events(all_documents)
    events.sort(key=lambda e: parse_timestamp(e.get("timestamp", "")))

    print(json.dumps(events, indent=2))


if __name__ == "__main__":
    main()
