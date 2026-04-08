# BioFID Dataset GNFinder Preprocessing Protocol (eschar-4)

## Scope
This document describes how the preprocessed dataset `biofid-preprocessed-eschar-4` was prepared from raw XMI corpus data for import into UCE.

- Source corpus root (raw): `.dev/storage/corpora/biofid-production`
- Output corpus root (preprocessed): `.dev/storage/corpora/biofid-preprocessed-eschar-4`
- Main preprocessing script: `dev/preprocess_taxon_xmi.py`

## Objective
Normalize GNFinder taxon annotations in XMI before importer execution, with strict script behavior aligned to professor guidance:
1. Resolve abbreviated genus forms (for example `C. muricata`) by reverse local genus backtracking in document order.
2. Verify resolved/full names with `gnverifier -s 11 -M`.
3. Write verified identifier lists to `identifier` (GBIF species URLs), while preserving original mention surface text (`value`) and original spans.

## Executables and Resources
- Script:
  - `dev/preprocess_taxon_xmi.py`
- Executables:
  - `gnfinder`: `/mnt/d/OneDrive/workspace/uni/hiwi/ttlab/projects/uce/gnfinder`
  - `gnverifier`: `/home/dater/.local/bin/gnverifier`
- Input corpus structure expected by script:
  - `<corpus-root>/corpusConfig.json`
  - `<corpus-root>/input/*.xmi(.bz2|.gz)`

## Command Pattern Used
```bash
python3 dev/preprocess_taxon_xmi.py \
  --corpus-root ./.dev/storage/corpora/biofid-production \
  --output-root ./.dev/storage/corpora/biofid-preprocessed-eschar-4 \
  --report ./.dev/storage/aux/preprocess-production-cleanrun-report.json \
  --unresolved-report ./.dev/storage/aux/preprocess-production-cleanrun-unresolved.jsonl \
  --gnfinder-bin /mnt/d/OneDrive/workspace/uni/hiwi/ttlab/projects/uce/gnfinder \
  --gnverifier-bin /home/dater/.local/bin/gnverifier \
  --gnverifier-sources 11
```

## Artifacts Produced
- Preprocessed corpus directory:
  - `.dev/storage/corpora/biofid-preprocessed-eschar-4`
- Processing reports:
  - `.dev/storage/aux/preprocess-production-cleanrun-report.json`
  - `.dev/storage/aux/preprocess-production-cleanrun-unresolved.jsonl`
  - `.dev/storage/aux/eschar_preprocess_multi_report.json`

## Notes
- The script preserves mention text and offsets; it adjusts identifier/canonical resolution metadata for import-time taxon enrichment.
- The output corpus keeps standard importer shape (`corpusConfig.json` + `input/`).
