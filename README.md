# BioFID Preprocessors

This repository packages two standalone preprocessing modules used before UCE import/search execution:

- `gnfinder-preprocessing/`: normalization of GNFinder taxon identifiers in XMI corpus files.
- `fuseki-preprocessing/`: GBIF-backed completion of missing taxon nodes/triples in a Fuseki dataset.

Scope policy:

- Included: core scripts, reference links, and reproducible workflow documentation.
- Excluded: runtime logs, temporary outputs, raw corpora, and TDB dataset snapshots.

## Layout

- `gnfinder-preprocessing/scripts/`
- `gnfinder-preprocessing/docs/`
- `gnfinder-preprocessing/references/`
- `fuseki-preprocessing/scripts/`
- `fuseki-preprocessing/docs/`
- `fuseki-preprocessing/references/`

## Reproducibility intention

Both modules are documented with implementation-agnostic workflows that define:

1. background and scientific purpose,
2. required external resources and where to obtain them,
3. stepwise procedure to reproduce equivalent outcomes,
4. expected outputs and verification points.
