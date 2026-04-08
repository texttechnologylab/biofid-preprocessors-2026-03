# BioFID Fuseki TDB Preprocessing Protocol (biofid-search)

## Scope
This document describes the Fuseki-side patch workflow used to repair/complete taxonomy triples for enrichment behavior.

- Target TDB root: `.dev/storage/tdb/biofid-search`
- Main patch script: `dev/fuseki_backbone_patch.py`
- Fuseki dataset endpoint name: `biofid-search`

## Objective
Backfill missing taxon graph entries in Fuseki from GBIF backbone data for the relevant seed branch (including accepted/synonym/subordinate relationships and vernacular names), without hardcoding UI test strings.

## Executables and Resources
- Script:
  - `dev/fuseki_backbone_patch.py`
- Resource archive:
  - `/mnt/d/OneDrive/workspace/uni/hiwi/ttlab/projects/uce/backbone.zip`
- Required files inside `backbone.zip`:
  - `Taxon.tsv`
  - `VernacularName.tsv`
- Fuseki endpoints used:
  - Query: `http://localhost:8030/biofid-search/sparql`
  - Update: `http://localhost:8030/biofid-search/update`

## Workflow
1. Run dry-run report to detect missing branch IDs/triples.
2. Apply INSERT updates in chunks.
3. Run post-check report to verify no expected IDs remain missing for the target branch.

## Command Pattern Used
Dry-run:
```bash
python3 dev/fuseki_backbone_patch.py \
  --backbone-zip /mnt/d/OneDrive/workspace/uni/hiwi/ttlab/projects/uce/backbone.zip \
  --seed-id 2722926 --seed-id 7485234 --seed-id 7687340 \
  --seed-id 7865185 --seed-id 8045926 --seed-id 8258636 \
  --report ./.dev/storage/aux/fuseki_backbone_patch_carex_dryrun.json
```

Apply:
```bash
python3 dev/fuseki_backbone_patch.py \
  --backbone-zip /mnt/d/OneDrive/workspace/uni/hiwi/ttlab/projects/uce/backbone.zip \
  --seed-id 2722926 --seed-id 7485234 --seed-id 7687340 \
  --seed-id 7865185 --seed-id 8045926 --seed-id 8258636 \
  --apply \
  --report ./.dev/storage/aux/fuseki_backbone_patch_carex_apply.json
```

Post-check:
```bash
python3 dev/fuseki_backbone_patch.py \
  --backbone-zip /mnt/d/OneDrive/workspace/uni/hiwi/ttlab/projects/uce/backbone.zip \
  --seed-id 2722926 --seed-id 7485234 --seed-id 7687340 \
  --seed-id 7865185 --seed-id 8045926 --seed-id 8258636 \
  --report ./.dev/storage/aux/fuseki_backbone_patch_carex_postcheck.json
```

## Artifacts Produced
- `.dev/storage/aux/fuseki_backbone_patch_carex_dryrun.json`
- `.dev/storage/aux/fuseki_backbone_patch_carex_apply.json`
- `.dev/storage/aux/fuseki_backbone_patch_carex_postcheck.json`

## Notes
- The patch is derived from GBIF backbone rows and builds RDF triples with BioFID GBIF ontology subjects (`https://www.biofid.de/bio-ontologies/gbif/<id>`).
- Fuseki endpoint naming remains `biofid-search`.
