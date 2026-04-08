# Reproducible Workflow: Fuseki Taxonomy Graph Completion from GBIF Backbone

## 1) Background and Purpose

UCE taxonomic enrichment depends on graph neighborhoods in Fuseki (accepted links, synonyms, subordinate taxa, vernacular names). Missing graph entities reduce expansion quality. This preprocessing stage cross-references Fuseki graph contents with a pinned GBIF Backbone release and inserts missing taxon graph nodes/triples for the target branch.

## 2) Required Resources

1. Target Fuseki dataset endpoint (query + update).
2. Pinned GBIF Backbone archive containing `Taxon.tsv` and `VernacularName.tsv`.
3. Seed GBIF taxon IDs defining the taxonomic branch of interest.
4. Fixed RDF mapping policy from GBIF fields to predicates used by UCE taxon expansion.

Use the provider documentation in `../references/references.md` for acquisition.

## 3) Data Contract

Input:

- Fuseki graph state,
- GBIF Backbone authority tables,
- seed taxon identifier set.

Output:

- Updated Fuseki graph with missing subjects/triples inserted for the target branch,
- machine-readable run report with branch, missing-set, and insertion statistics.

## 4) Procedure (Implementation-Agnostic)

1. Freeze run invariants:
   - GBIF Backbone release,
   - seed ID set,
   - endpoint target,
   - RDF mapping policy.
2. Build expected branch from seeds using authority relations:
   - accepted usages,
   - synonym relations,
   - relevant subordinate taxa,
   - vernacular names.
3. Query Fuseki for existing subjects in this expected branch.
4. Compute missing subjects as set difference.
5. Generate RDF triples for missing subjects using the fixed mapping policy.
6. Apply updates in controlled insertion batches.
7. Re-query coverage and produce post-check status.

## 5) Verification and Acceptance

A run is accepted if:

- run report is generated,
- post-check confirms expected missing-set reduction to target threshold,
- endpoint and seed metadata in report match the frozen run configuration.

## 6) Deliverables

- Run report (dry-run and/or apply/post-check according to operation mode).
- Updated Fuseki dataset state for the target taxonomic branch.
