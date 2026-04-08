#!/usr/bin/env python3
"""Preprocess GNFinder taxon annotations in XMI files.

Guided strictly by the professor's detect_abbreviated_taxa.sh intent:
1) resolve abbreviated genus in sequence using reverse first-letter backtracking
2) verify resolved names using gnverifier -s 11 -M
3) write all verified identifiers back to taxon.identifier

The original span value (e.g. "C. muricata") is preserved.
Only dataset-wide orchestration differs from the single-document shell script.
"""

from __future__ import annotations

import argparse
import bz2
import csv
import gzip
import html
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


# Process both GN node shapes seen across corpora/import variants.
GN_TAXON_RE = re.compile(r"<(?P<tag>gnfinder:(?:VerifiedTaxon|Taxon))\b(?P<attrs>[^>]*)/>")
ATTR_RE = re.compile(r'([A-Za-z0-9_:-]+)="(.*?)"')
ABBREV_RE = re.compile(r"^(?P<initial>[A-Z])\.\s+(?P<rest>[A-Za-z][A-Za-z.\-]*(?:\s+[A-Za-z][A-Za-z.\-]*)*)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-root", required=True, type=Path, help="Corpus root with input/ and corpusConfig.json")
    parser.add_argument("--output-root", type=Path, default=None, help="Output corpus root; defaults to in-place")
    parser.add_argument("--limit-files", type=int, default=0, help="Optional cap on number of XMI files")
    parser.add_argument("--report", type=Path, default=None, help="Optional JSON report output path")
    parser.add_argument("--unresolved-report", type=Path, default=None, help="Optional JSONL report for unresolved taxa")
    parser.add_argument("--dry-run", action="store_true", help="Analyze only, do not write files")
    parser.add_argument("--only-term", default="", help="Optional: process only GNFinder taxa matching this value")
    parser.add_argument("--gnfinder-bin", type=Path, help="Path to gnfinder binary")
    parser.add_argument("--gnfinder-timeout", type=float, default=180.0, help="Timeout for one gnfinder file call")
    parser.add_argument("--gnverifier-bin", type=Path, help="Path to gnverifier binary")
    parser.add_argument("--gnverifier-sources", default="11", help="Data-source ids passed to gnverifier --sources")
    parser.add_argument("--gnverifier-timeout", type=float, default=180.0, help="Timeout for one gnverifier batch call")
    return parser.parse_args()


def read_text(path: Path) -> str:
    if path.suffix == ".bz2":
        with bz2.open(path, "rt", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".bz2":
        with bz2.open(path, "wt", encoding="utf-8") as fh:
            fh.write(content)
        return
    if path.suffix == ".gz":
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            fh.write(content)
        return
    path.write_text(content, encoding="utf-8")


def parse_attrs(blob: str) -> dict[str, str]:
    return {k: html.unescape(v) for k, v in ATTR_RE.findall(blob)}


def attr_blob(attrs: dict[str, str]) -> str:
    # Keep deterministic order for stable diffs.
    keys = sorted(attrs.keys())
    return " ".join(f'{k}="{html.escape(str(attrs[k]), quote=True)}"' for k in keys)


def normalize_name(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"[\s,;:.]+$", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.casefold()


def parse_genus(value: str) -> str:
    token = re.split(r"\s+", (value or "").strip())[0]
    token = re.sub(r"[^A-Za-z-]", "", token)
    if token and token[:1].isupper() and "." not in token:
        return token
    return ""


def extract_sofa_text(xml_text: str) -> str:
    m = re.search(r"<cas:Sofa\b[^>]*\bsofaString=\"(.*?)\"", xml_text, flags=re.DOTALL)
    if not m:
        return ""
    return html.unescape(m.group(1))


def run_gnfinder_genera_positions(sofa_text: str, gnfinder_bin: Path, timeout: float) -> list[tuple[int, str]]:
    if not sofa_text.strip():
        return []

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=True) as tf:
        tf.write(sofa_text)
        tf.flush()
        cmd = [str(gnfinder_bin), "-U", "-f", "csv", tf.name]
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=True)

    out: list[tuple[int, str]] = []
    reader = csv.DictReader(proc.stdout.splitlines())
    for row in reader:
        name = (row.get("Name") or "").strip()
        if not name:
            continue
        genus = re.split(r"\s+", name)[0]
        genus = re.sub(r"[^A-Za-z-]", "", genus)
        if not genus or "." in genus or not genus[:1].isupper():
            continue
        try:
            start = int((row.get("Start") or "").strip())
        except ValueError:
            continue
        out.append((start, genus))
    return out


def gbif_to_biofid(url: str) -> str:
    if "biofid.de/bio-ontologies/gbif/" in url:
        return url.strip()
    m = re.search(r"/species/(\d+)$", url.strip())
    if m:
        return f"https://www.biofid.de/bio-ontologies/gbif/{m.group(1)}"
    m2 = re.search(r"(\d+)$", url.strip())
    if m2:
        return f"https://www.biofid.de/bio-ontologies/gbif/{m2.group(1)}"
    return url.strip()


def _biofid_links_from_gnverifier_result(item: dict) -> list[str]:
    links: set[str] = set()
    for row in item.get("results", []):
        outlink = str(row.get("outlink") or "").strip()
        if outlink:
            links.add(gbif_to_biofid(outlink))
            continue
        record_id = str(row.get("recordId") or "").strip()
        if record_id.isdigit():
            links.add(f"https://www.biofid.de/bio-ontologies/gbif/{record_id}")
    return sorted(links)


def run_gnverifier_batch(
    names: list[str],
    gnverifier_bin: Path,
    sources: str,
    timeout: float,
) -> dict[str, list[str]]:
    # The professor note uses gnverifier with `-s 11 -M`; we mirror that behavior.
    cmd = [
        str(gnverifier_bin),
        "-s",
        sources,
        "-M",
        "-f",
        "compact",
        "-q",
    ]
    payload = "\n".join(n.strip() for n in names if n.strip()) + "\n"
    proc = subprocess.run(
        cmd,
        input=payload,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=True,
    )

    out: dict[str, list[str]] = {}
    # gnverifier prints one compact JSON object per line; logs may appear on stderr.
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        obj = json.loads(line)
        norm_name = normalize_name(str(obj.get("name") or ""))
        if not norm_name:
            continue
        links = _biofid_links_from_gnverifier_result(obj)
        if links:
            out[norm_name] = links
    return out


def iter_input_files(input_dir: Path):
    for path in sorted(input_dir.iterdir()):
        if path.is_file() and (
            path.name.endswith(".xmi")
            or path.name.endswith(".xmi.gz")
            or path.name.endswith(".xmi.bz2")
        ):
            yield path


def resolve_abbreviation_candidates(
    xml_text: str,
    gnfinder_genus_positions: list[tuple[int, str]] | None = None,
    history_genera_by_initial: dict[str, list[str]] | None = None,
) -> dict[tuple[int, int], list[str]]:
    """Resolve abbreviations to ordered candidate full names.

    Keep script parity (nearest previous matching genus first) but preserve
    alternative candidates so verifier results can select a valid expansion.
    """
    resolved_candidates: dict[tuple[int, int], list[str]] = {}
    entries: list[tuple[int, int, str]] = []
    genera_by_initial: dict[str, list[tuple[int, str]]] = {}
    gnfinder_by_initial: dict[str, list[tuple[int, str]]] = {}

    for idx, m in enumerate(GN_TAXON_RE.finditer(xml_text)):
        attrs = parse_attrs(m.group("attrs"))
        value = (attrs.get("value") or "").strip()
        begin = int(attrs.get("begin", "-1"))
        end = int(attrs.get("end", "-1"))
        entries.append((begin, end, value))

        genus_candidate = parse_genus(value)
        if genus_candidate:
            initial = genus_candidate[:1]
            genera_by_initial.setdefault(initial, []).append((idx, genus_candidate))

    if gnfinder_genus_positions:
        for pos, genus in gnfinder_genus_positions:
            if not genus:
                continue
            gnfinder_by_initial.setdefault(genus[:1], []).append((pos, genus))
        for initial in gnfinder_by_initial:
            gnfinder_by_initial[initial].sort(key=lambda x: x[0])

    for idx, (begin, end, value) in enumerate(entries):
        m = ABBREV_RE.match(value)
        if not m:
            resolved_candidates[(begin, end)] = [value]
            continue

        initial = m.group("initial")
        rest = m.group("rest")
        local = genera_by_initial.get(initial, [])
        options: list[str] = []
        seen: set[str] = set()

        def add_candidate(genus_or_name: str) -> None:
            if not genus_or_name:
                return
            genus = parse_genus(genus_or_name)
            if genus:
                candidate = f"{genus} {rest}"
            else:
                candidate = genus_or_name
            norm = normalize_name(candidate)
            if not norm or norm in seen:
                return
            seen.add(norm)
            options.append(candidate)

        # Nearest previous local genus (script intent), then more previous context.
        previous = [g for pos, g in local if pos < idx]
        for g in reversed(previous[-6:]):
            add_candidate(g)

        # Full-text GNFinder guidance around character positions.
        gn_candidates = gnfinder_by_initial.get(initial, [])
        if gn_candidates:
            prev_gn = [g for pos, g in gn_candidates if pos <= begin]
            for g in reversed(prev_gn[-6:]):
                add_candidate(g)
            next_gn = [g for pos, g in gn_candidates if pos > begin]
            for g in next_gn[:6]:
                add_candidate(g)

        # Future local occurrences as fallback.
        future = [g for pos, g in local if pos > idx]
        for g in future[:6]:
            add_candidate(g)

        # Cross-file memory from already verified names.
        if history_genera_by_initial:
            for g in reversed(history_genera_by_initial.get(initial, [])[-12:]):
                add_candidate(g)

        # Always include original value as a last-resort candidate.
        add_candidate(value)
        resolved_candidates[(begin, end)] = options if options else [value]

    return resolved_candidates


def process_file(
    path: Path,
    only_term: str,
    gnfinder_bin: Path,
    gnfinder_timeout: float,
    gnverifier_bin: Path,
    gnverifier_sources: str,
    gnverifier_timeout: float,
    gnverifier_cache: dict[str, list[str]],
    history_genera_by_initial: dict[str, list[str]],
    unresolved_entries: list[dict],
) -> tuple[str, dict]:
    xml_text = read_text(path)
    sofa_text = extract_sofa_text(xml_text)
    gnfinder_genus_positions = run_gnfinder_genera_positions(sofa_text, gnfinder_bin, gnfinder_timeout)
    candidate_map = resolve_abbreviation_candidates(
        xml_text,
        gnfinder_genus_positions,
        history_genera_by_initial,
    )

    replacements: list[tuple[int, int, str]] = []
    stats = {
        "file": str(path),
        "gnfinderVerifiedSeen": 0,
        "abbreviationResolvedForLookup": 0,
        "gnfinderGuidedGenusHints": len(gnfinder_genus_positions),
        "identifierExpandedFromGnverifier": 0,
        "verifierMiss": 0,
        "unchanged": 0,
    }

    verifier_inputs: list[str] = []
    verifier_seen: set[str] = set()
    for m in GN_TAXON_RE.finditer(xml_text):
        attrs = parse_attrs(m.group("attrs"))
        value = (attrs.get("value") or "").strip()
        if only_term and normalize_name(value) != normalize_name(only_term):
            continue
        begin = int(attrs.get("begin", "-1"))
        end = int(attrs.get("end", "-1"))
        candidates = candidate_map.get((begin, end), [value])
        if any(normalize_name(c) != normalize_name(value) for c in candidates):
            stats["abbreviationResolvedForLookup"] += 1
        for candidate in candidates:
            norm = normalize_name(candidate)
            if norm and norm not in gnverifier_cache and norm not in verifier_seen:
                verifier_seen.add(norm)
                verifier_inputs.append(candidate)

    if verifier_inputs:
        batch = run_gnverifier_batch(
            verifier_inputs,
            gnverifier_bin,
            gnverifier_sources,
            gnverifier_timeout,
        )
        gnverifier_cache.update(batch)

    for m in GN_TAXON_RE.finditer(xml_text):
        stats["gnfinderVerifiedSeen"] += 1
        attrs = parse_attrs(m.group("attrs"))
        tag = m.group("tag")
        begin = int(attrs.get("begin", "-1"))
        end = int(attrs.get("end", "-1"))
        value = (attrs.get("value") or "").strip()
        if only_term and normalize_name(value) != normalize_name(only_term):
            stats["unchanged"] += 1
            continue

        # Keep original annotation span value unchanged; only lookup enrichment via resolved candidates.
        candidates = candidate_map.get((begin, end), [value])
        target_links: list[str] = []
        resolved = value
        attempted: list[str] = []
        for candidate in candidates:
            attempted.append(candidate)
            gv_links = gnverifier_cache.get(normalize_name(candidate), [])
            if not gv_links:
                continue
            resolved = candidate
            target_links = gv_links
            break

        if target_links:
            stats["identifierExpandedFromGnverifier"] += 1
        else:
            stats["verifierMiss"] += 1
            unresolved_entries.append({
                "file": str(path),
                "tag": tag,
                "begin": begin,
                "end": end,
                "value": value,
                "lookupValue": resolved,
                "attemptedCandidates": attempted[:10],
            })

        if target_links:
            attrs["identifier"] = " ".join(target_links)
            attrs["cardinality"] = str(len(target_links))
            # Keep a stable primary record id for existing importer behavior.
            primary = re.search(r"(\d+)$", target_links[0])
            if primary:
                attrs["recordId"] = primary.group(1)
                attrs["outlink"] = f"https://gbif.org/species/{primary.group(1)}"
            # Metadata alignment to resolved canonical without altering visible span value.
            attrs["matchedCanonicalFull"] = resolved
            genus = parse_genus(resolved)
            if genus:
                bucket = history_genera_by_initial.setdefault(genus[:1], [])
                if genus not in bucket:
                    bucket.append(genus)
        else:
            stats["unchanged"] += 1

        replacements.append((m.start(), m.end(), f"<{tag} {attr_blob(attrs)}/>"))

    if not replacements:
        return xml_text, stats

    out = []
    cursor = 0
    for start, end, repl in replacements:
        out.append(xml_text[cursor:start])
        out.append(repl)
        cursor = end
    out.append(xml_text[cursor:])
    return "".join(out), stats


def main() -> int:
    args = parse_args()
    input_dir = args.corpus_root / "input"
    if not input_dir.is_dir():
        raise SystemExit(f"input directory missing: {input_dir}")

    output_root = args.output_root or args.corpus_root
    (output_root / "input").mkdir(parents=True, exist_ok=True)

    report_items = []
    unresolved_entries: list[dict] = []
    processed = 0
    gnverifier_cache: dict[str, list[str]] = {}
    history_genera_by_initial: dict[str, list[str]] = {}
    gnfinder_path = args.gnfinder_bin
    gnfinder_enabled = gnfinder_path.exists() or shutil.which(str(gnfinder_path)) is not None
    if not gnfinder_enabled:
        raise SystemExit(f"gnfinder binary not found: {gnfinder_path}")
    gnverifier_path = args.gnverifier_bin
    gnverifier_enabled = gnverifier_path.exists() or shutil.which(str(gnverifier_path)) is not None
    if not gnverifier_enabled:
        raise SystemExit(f"gnverifier binary not found: {gnverifier_path}")

    for src in iter_input_files(input_dir):
        if args.limit_files and processed >= args.limit_files:
            break
        processed += 1
        patched, stats = process_file(
            src,
            args.only_term,
            gnfinder_path,
            args.gnfinder_timeout,
            gnverifier_path,
            args.gnverifier_sources,
            args.gnverifier_timeout,
            gnverifier_cache,
            history_genera_by_initial,
            unresolved_entries,
        )
        report_items.append(stats)

        dst = output_root / "input" / src.name
        if not args.dry_run:
            write_text(dst, patched)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report_items, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    if args.unresolved_report:
        args.unresolved_report.parent.mkdir(parents=True, exist_ok=True)
        with args.unresolved_report.open("w", encoding="utf-8") as fh:
            for entry in unresolved_entries:
                fh.write(json.dumps(entry, ensure_ascii=True) + "\n")

    summary = {
        "processedFiles": processed,
        "dryRun": args.dry_run,
        "outputRoot": str(output_root),
        "report": str(args.report) if args.report else None,
        "unresolvedReport": str(args.unresolved_report) if args.unresolved_report else None,
        "gnfinderEnabled": gnfinder_enabled,
        "gnfinderBin": str(gnfinder_path),
        "gnverifierEnabled": gnverifier_enabled,
        "gnverifierBin": str(gnverifier_path),
        "stats": {
            "gnfinderVerifiedSeen": sum(x["gnfinderVerifiedSeen"] for x in report_items),
            "abbreviationResolvedForLookup": sum(x["abbreviationResolvedForLookup"] for x in report_items),
            "gnfinderGuidedGenusHints": sum(x["gnfinderGuidedGenusHints"] for x in report_items),
            "identifierExpandedFromGnverifier": sum(x["identifierExpandedFromGnverifier"] for x in report_items),
            "verifierMiss": sum(x["verifierMiss"] for x in report_items),
            "unresolvedEntries": len(unresolved_entries),
        },
    }
    print(json.dumps(summary, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
