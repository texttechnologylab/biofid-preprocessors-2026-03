# Fuseki GBIF Graph Completion Module

Purpose:

- Complete missing taxon graph nodes/triples in a Fuseki dataset by cross-referencing a pinned GBIF Backbone release, so UCE taxon expansion uses coherent synonym/subordinate/vernacular neighborhoods.

Contents:

- `scripts/fuseki_backbone_patch.py`: main graph-completion script.
- `scripts/biofid_fuseki_fix.py`: GBIF-side diagnostic/report helper.
- `scripts/fuseki_replicate_enriched_request.py`: enrichment behavior replication helper.
- `docs/reproducible_workflow.md`: implementation-agnostic procedure.
- `docs/report_section_overleaf.tex`: Overleaf-ready report section.
- `references/references.md`: external authoritative resources.
