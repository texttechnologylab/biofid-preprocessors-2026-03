#!/usr/bin/env python3
from __future__ import annotations

import argparse
import bz2
import gzip
import json
import re
from pathlib import Path


GN_VERIFIED_RE = re.compile(r'<gnfinder:VerifiedTaxon\b([^>]*)/>')
GN_RAW_RE = re.compile(r'<gnfinder:Taxon\b([^>]*)/>')
GA_RE = re.compile(r'<type10:Taxon\b([^>]*)/>')
ATTR_RE = re.compile(r'([A-Za-z0-9_:-]+)="(.*?)"')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect GNFinder/Gazetteer taxon identifiers directly in XMI.")
    parser.add_argument("--xmi", required=True, type=Path, help="Path to .xmi, .xmi.bz2, or .xmi.gz")
    parser.add_argument("--term", required=True, help="Taxon surface form to inspect, e.g. Acosta")
    return parser.parse_args()


def read_text(path: Path) -> str:
    if path.suffix == ".bz2":
        with bz2.open(path, "rt", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    return path.read_text(encoding="utf-8", errors="replace")


def attrs(blob: str) -> dict[str, str]:
    return {k: v for k, v in ATTR_RE.findall(blob)}


def split_identifier(raw: str) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[|\s]+", raw.strip())
    return [p for p in parts if p]


def collect(pattern: re.Pattern[str], xml: str, term: str) -> list[dict]:
    out: list[dict] = []
    term_fold = term.casefold()
    for m in pattern.finditer(xml):
        a = attrs(m.group(1))
        value = (a.get("value") or "").strip()
        if value.casefold().rstrip(",") != term_fold.rstrip(","):
            continue
        identifier = a.get("identifier", "")
        out.append(
            {
                "begin": int(a.get("begin", "-1")),
                "end": int(a.get("end", "-1")),
                "value": value,
                "identifier": identifier,
                "identifierLinks": split_identifier(identifier),
                "recordId": a.get("recordId"),
                "matchedName": a.get("matchedName"),
                "matchedCanonicalFull": a.get("matchedCanonicalFull"),
                "taxonomicStatus": a.get("taxonomicStatus"),
            }
        )
    return out


def summarize(rows: list[dict]) -> dict:
    identifiers = {}
    for row in rows:
        key = row["identifier"]
        identifiers[key] = identifiers.get(key, 0) + 1
    return {
        "count": len(rows),
        "distinctIdentifierValues": len(identifiers),
        "identifierFrequencies": identifiers,
        "tokenCounts": sorted({len(r["identifierLinks"]) for r in rows}),
    }


def main() -> int:
    args = parse_args()
    xml = read_text(args.xmi)

    gn_verified = collect(GN_VERIFIED_RE, xml, args.term)
    gn_raw = collect(GN_RAW_RE, xml, args.term)
    gazetteer = collect(GA_RE, xml, args.term)

    report = {
        "xmi": str(args.xmi),
        "term": args.term,
        "gnfinderVerifiedSummary": summarize(gn_verified),
        "gnfinderRawSummary": summarize(gn_raw),
        "gazetteerSummary": summarize(gazetteer),
        "examples": {
            "gnfinderVerifiedFirst": gn_verified[:2],
            "gazetteerFirst": gazetteer[:2],
        },
    }
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

