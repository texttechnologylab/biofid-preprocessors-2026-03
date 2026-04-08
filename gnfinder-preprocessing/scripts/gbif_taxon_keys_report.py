#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve GBIF taxon keys to compact species summaries.")
    parser.add_argument("keys", nargs="+", help="GBIF taxon keys, e.g. 8315399 3096497")
    parser.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds")
    return parser.parse_args()


def fetch_json(url: str, timeout: float) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "uce-taxon-debug/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def summarize(key: str, timeout: float) -> dict:
    data = fetch_json(f"https://api.gbif.org/v1/species/{key}", timeout)
    return {
        "key": data.get("key"),
        "scientificName": data.get("scientificName"),
        "canonicalName": data.get("canonicalName"),
        "authorship": data.get("authorship"),
        "rank": data.get("rank"),
        "taxonomicStatus": data.get("taxonomicStatus"),
        "acceptedKey": data.get("acceptedKey"),
        "accepted": data.get("accepted"),
        "kingdom": data.get("kingdom"),
        "phylum": data.get("phylum"),
        "order": data.get("order"),
        "family": data.get("family"),
        "genus": data.get("genus"),
    }


def main() -> int:
    args = parse_args()
    report = {"queries": [summarize(k, args.timeout) for k in args.keys]}
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

