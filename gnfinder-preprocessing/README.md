# GNFinder Taxonomic Normalization Module

Purpose:

- Normalize GNFinder taxon annotations in BioFID XMI corpora so identifiers are consistently resolved to BioFID/GBIF taxon URIs before UCE import.

Contents:

- `scripts/preprocess_taxon_xmi.py`: main batch normalization script.
- `scripts/biofid_gnfinder_fix.py`: conservative candidate discovery helper (no rewriting).
- `scripts/inspect_taxon_xmi.py`: targeted XMI inspection utility.
- `scripts/gbif_taxon_keys_report.py`: compact GBIF lookup utility.
- `docs/reproducible_workflow.md`: implementation-agnostic procedure.
- `docs/report_section_overleaf.tex`: Overleaf-ready report section.
- `references/references.md`: external authoritative resources.
