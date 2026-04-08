#!/usr/bin/env python3
"""Patch Fuseki taxon graph from GBIF backbone.zip for selected seed IDs.

This script uses Taxon.tsv + VernacularName.tsv from backbone.zip as the only source
and inserts missing taxon triples into Fuseki for a focused ID set and their
related accepted/synonym/subordinate branch.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import urllib.parse
import urllib.request
import zipfile

BIOFID_BASE = "https://www.biofid.de/bio-ontologies/gbif/"
GBIF_SPECIES_BASE = "https://www.gbif.org/species/"
csv.field_size_limit(1024 * 1024 * 64)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backbone-zip", required=True, help="Path to GBIF backbone.zip")
    ap.add_argument("--seed-id", action="append", required=True, help="GBIF taxon ID seed (repeatable)")
    ap.add_argument("--endpoint-query", default="http://localhost:8030/biofid-search/sparql")
    ap.add_argument("--endpoint-update", default="http://localhost:8030/biofid-search/update")
    ap.add_argument("--apply", action="store_true", help="Apply INSERT updates to Fuseki")
    ap.add_argument("--report", required=True, help="Output JSON report")
    return ap.parse_args()


def norm(value: str) -> str:
    return (value or "").strip()


def row_subject(tid: str) -> str:
    return f"<{BIOFID_BASE}{tid}>"


def triple_uri(s: str, p: str, o: str) -> str:
    return f"{s} <{p}> <{o}> ."


def triple_lit(s: str, p: str, lit: str) -> str:
    escaped = lit.replace("\\", "\\\\").replace('"', '\\"')
    return f'{s} <{p}> "{escaped}" .'


def sparql_select(endpoint: str, query: str) -> dict:
    url = endpoint + "?query=" + urllib.parse.quote(query, safe="")
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def sparql_update(endpoint: str, update: str) -> None:
    data = urllib.parse.urlencode({"update": update}).encode("utf-8")
    req = urllib.request.Request(endpoint, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
    with urllib.request.urlopen(req, timeout=120):
        pass


def existing_subjects(endpoint: str, ids: list[str]) -> set[str]:
    values = " ".join(f"<{BIOFID_BASE}{i}>" for i in ids)
    q = f"SELECT ?s WHERE {{ VALUES ?s {{ {values} }} ?s ?p ?o }}"
    rows = sparql_select(endpoint, q).get("results", {}).get("bindings", [])
    return {r["s"]["value"] for r in rows if "s" in r}


def iter_tsv_rows(z: zipfile.ZipFile, entry_name: str):
    with z.open(entry_name) as f:
        txt = io.TextIOWrapper(f, encoding="utf-8", errors="replace", newline="")
        reader = csv.DictReader(txt, delimiter="\t")
        for row in reader:
            yield row


def collect_branch_streaming(z: zipfile.ZipFile, seeds: set[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    seed_canonicals: set[str] = set()
    accepted_ids: set[str] = set()

    # Pass 1: direct seeds, collect canonical and accepted IDs.
    for row in iter_tsv_rows(z, "Taxon.tsv"):
        tid = norm(row.get("taxonID"))
        if tid not in seeds:
            continue
        out[tid] = row
        canonical = norm(row.get("canonicalName"))
        if canonical:
            seed_canonicals.add(canonical)
        acc = norm(row.get("acceptedNameUsageID"))
        if acc:
            accepted_ids.add(acc)

    # Pass 2: rows with same canonical as seeds, and direct accepted rows.
    for row in iter_tsv_rows(z, "Taxon.tsv"):
        tid = norm(row.get("taxonID"))
        if not tid:
            continue
        canonical = norm(row.get("canonicalName"))
        if canonical and canonical in seed_canonicals:
            out[tid] = row
            acc = norm(row.get("acceptedNameUsageID"))
            if acc:
                accepted_ids.add(acc)
        if tid in accepted_ids:
            out[tid] = row

    accepted_union = set(accepted_ids)
    for tid, row in out.items():
        if norm(row.get("taxonomicStatus")).lower() == "accepted":
            accepted_union.add(tid)

    # Pass 3: synonyms + subordinate children of accepted branch.
    for row in iter_tsv_rows(z, "Taxon.tsv"):
        tid = norm(row.get("taxonID"))
        if not tid:
            continue
        acc = norm(row.get("acceptedNameUsageID"))
        parent = norm(row.get("parentNameUsageID"))
        rank = norm(row.get("taxonRank")).lower()
        status = norm(row.get("taxonomicStatus")).lower()
        if acc and acc in accepted_union and status == "synonym":
            out[tid] = row
        if parent and parent in accepted_union and rank in {"subspecies", "variety", "varietas", "form", "forma"}:
            out[tid] = row

    return out


def build_triples(rows: dict[str, dict], vernacular_by_taxon: dict[str, list[str]]) -> list[str]:
    triples: list[str] = []

    for tid, row in rows.items():
        s = row_subject(tid)
        triples.append(triple_uri(s, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://rs.tdwg.org/dwc/terms/Taxon"))
        triples.append(triple_uri(s, "http://rs.tdwg.org/dwc/terms/taxonID", f"{GBIF_SPECIES_BASE}{tid}"))

        scientific = norm(row.get("scientificName"))
        if scientific:
            triples.append(triple_lit(s, "http://rs.tdwg.org/dwc/terms/scientificName", scientific))
        canonical = norm(row.get("canonicalName"))
        if canonical:
            triples.append(triple_lit(s, "http://rs.tdwg.org/dwc/terms/cleanedScientificName", canonical))
        status = norm(row.get("taxonomicStatus")).lower()
        if status:
            triples.append(triple_lit(s, "http://rs.tdwg.org/dwc/terms/taxonomicStatus", status))
        rank = norm(row.get("taxonRank")).lower()
        if rank:
            triples.append(triple_lit(s, "http://rs.tdwg.org/dwc/terms/taxonRank", rank))

        parent = norm(row.get("parentNameUsageID"))
        if parent:
            triples.append(triple_uri(s, "http://rs.tdwg.org/dwc/terms/parentNameUsageID", f"{BIOFID_BASE}{parent}"))
        accepted = norm(row.get("acceptedNameUsageID"))
        if accepted:
            triples.append(triple_uri(s, "http://rs.tdwg.org/dwc/terms/acceptedNameUsageID", f"{BIOFID_BASE}{accepted}"))

        for col, pred in [
            ("kingdom", "http://rs.tdwg.org/dwc/terms/kingdom"),
            ("phylum", "http://rs.tdwg.org/dwc/terms/phylum"),
            ("class", "http://rs.tdwg.org/dwc/terms/class"),
            ("order", "http://rs.tdwg.org/dwc/terms/order"),
            ("family", "http://rs.tdwg.org/dwc/terms/family"),
            ("genus", "http://rs.tdwg.org/dwc/terms/genus"),
        ]:
            val = norm(row.get(col))
            if val:
                triples.append(triple_lit(s, pred, val))

        for vern in vernacular_by_taxon.get(tid, []):
            triples.append(triple_lit(s, "http://rs.tdwg.org/dwc/terms/vernacularName", vern))

    return triples


def chunked(seq: list[str], size: int) -> list[list[str]]:
    return [seq[i:i + size] for i in range(0, len(seq), size)]


def main() -> int:
    args = parse_args()
    seeds = {norm(s) for s in args.seed_id if norm(s)}

    with zipfile.ZipFile(args.backbone_zip) as z:
        branch = collect_branch_streaming(z, seeds)
        wanted_vernacular_ids = set(branch.keys())
        vernacular_by_taxon: dict[str, list[str]] = {}
        for vrow in iter_tsv_rows(z, "VernacularName.tsv"):
            tid = norm(vrow.get("taxonID"))
            if tid not in wanted_vernacular_ids:
                continue
            v = norm(vrow.get("vernacularName"))
            if not v:
                continue
            vernacular_by_taxon.setdefault(tid, []).append(v)

    branch_ids = sorted(branch.keys())
    existing = existing_subjects(args.endpoint_query, branch_ids)
    missing_ids = [tid for tid in branch_ids if f"{BIOFID_BASE}{tid}" not in existing]

    missing_rows = {tid: branch[tid] for tid in missing_ids}
    triples = build_triples(missing_rows, vernacular_by_taxon)

    applied_chunks = 0
    if args.apply and triples:
        for group in chunked(triples, 400):
            update = "INSERT DATA {\n" + "\n".join(group) + "\n}"
            sparql_update(args.endpoint_update, update)
            applied_chunks += 1

    report = {
        "seeds": sorted(seeds),
        "branchIdsCount": len(branch_ids),
        "branchIds": branch_ids,
        "missingIdsCount": len(missing_ids),
        "missingIds": missing_ids,
        "triplesPrepared": len(triples),
        "applied": bool(args.apply),
        "appliedChunks": applied_chunks,
        "endpointQuery": args.endpoint_query,
        "endpointUpdate": args.endpoint_update,
    }
    with open(args.report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=True)
        fh.write("\n")
    print(json.dumps(report, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
