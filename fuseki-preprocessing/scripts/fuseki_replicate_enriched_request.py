#!/usr/bin/env python3
"""Replicate EnrichedSearchQuery -> JenaSparqlService taxonomy expansion against Fuseki.

This script mirrors getAlternativeNamesOfTaxons():
1) getPossibleSynonymIdsOfTaxon
2) getSubordinateTaxonIds
3) fetch cleanedScientificName / vernacularName for all collected IDs
"""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request


def sparql(endpoint: str, query: str) -> dict:
    url = endpoint + "?query=" + urllib.parse.quote(query, safe="")
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def to_bindings(payload: dict) -> list[dict]:
    return payload.get("results", {}).get("bindings", [])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--endpoint",
        default="http://localhost:8030/biofid-search/sparql",
        help="Fuseki SPARQL endpoint",
    )
    ap.add_argument("biofid_ids", nargs="+", help="BioFID taxon URIs")
    args = ap.parse_args()

    base_ids = list(dict.fromkeys(args.biofid_ids))

    synonym_ids: set[str] = set()
    for url in base_ids:
        q = f"""
PREFIX dwc: <http://rs.tdwg.org/dwc/terms/>
SELECT ?subject
WHERE {{
  ?subject dwc:acceptedNameUsageID <{url}> .
  ?subject dwc:taxonomicStatus ?status .
  FILTER(lcase(str(?status)) = "synonym")
}}
"""
        for b in to_bindings(sparql(args.endpoint, q)):
            v = b.get("subject", {}).get("value")
            if v:
                synonym_ids.add(v)

    subordinate_ids: set[str] = set()
    for url in base_ids:
        q = f"""
PREFIX dwc: <http://rs.tdwg.org/dwc/terms/>
SELECT ?subject ?object
WHERE {{
  ?subject dwc:parentNameUsageID <{url}> .
  ?subject dwc:taxonRank ?object .
  FILTER(lcase(str(?object)) IN ("subspecies", "varietas", "variety", "forma", "form"))
}}
"""
        for b in to_bindings(sparql(args.endpoint, q)):
            v = b.get("subject", {}).get("value")
            if v:
                subordinate_ids.add(v)

    all_ids = list(dict.fromkeys(base_ids + sorted(synonym_ids) + sorted(subordinate_ids)))
    values = "\n".join(f"<{u}>" for u in all_ids)
    q_names = f"""
SELECT ?subject ?predicate ?object
WHERE {{
  VALUES ?subject {{ {values} }}
  ?subject ?predicate ?object .
  FILTER(?predicate IN (<http://rs.tdwg.org/dwc/terms/vernacularName>, <http://rs.tdwg.org/dwc/terms/cleanedScientificName>))
}}
"""
    name_rows = to_bindings(sparql(args.endpoint, q_names))

    out = {
        "endpoint": args.endpoint,
        "inputIds": base_ids,
        "synonymIds": sorted(synonym_ids),
        "subordinateIds": sorted(subordinate_ids),
        "allIdsQueried": all_ids,
        "nameRowsCount": len(name_rows),
        "names": [r.get("object", {}).get("value", "") for r in name_rows],
    }
    print(json.dumps(out, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
