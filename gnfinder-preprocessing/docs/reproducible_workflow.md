# Reproducible Workflow: GNFinder Taxonomic Normalization

## 1) Background and Purpose

BioFID OCR corpora already contain taxon mention annotations, but mention detection quality and identifier quality are different concerns. This preprocessing stage improves identifier quality by resolving ambiguous name forms (especially abbreviated genus forms) and validating candidates against a controlled taxonomic authority service before UCE import.

## 2) Required Resources

1. Input corpus snapshot in UIMA XMI form with GNFinder annotation layers (`gnfinder:VerifiedTaxon`, `gnfinder:Taxon`).
2. GNFinder executable (for document-level genus context extraction).
3. GNVerifier executable (for authority validation and identifier resolution).
4. Stable source policy for verification (e.g., a fixed source set).

Use the provider documentation in `../references/references.md` for acquisition.

## 3) Data Contract

Input per document:

- XMI document with GNFinder taxon annotations and character offsets.

Output per document:

- Same XMI structure and mention spans/text.
- Improved identifier-linked fields for resolvable taxa.
- Unresolved taxa retained and recorded in a separate unresolved artifact.

## 4) Procedure (Implementation-Agnostic)

1. Freeze run invariants:
   - corpus snapshot,
   - GNFinder/GNVerifier versions,
   - verification source policy,
   - deterministic file traversal order.
2. Traverse corpus documents in deterministic order.
3. For each taxon annotation:
   - detect ambiguous abbreviated forms,
   - construct ranked full-name candidates from document context,
   - validate candidates via GNVerifier under fixed source policy.
4. For validated candidates:
   - write normalized taxon identifiers and aligned canonical metadata.
5. For unresolved candidates:
   - keep original annotation content unchanged,
   - append unresolved case to unresolved artifact.
6. Emit run-level statistics and unresolved-case artifacts.

## 5) Verification and Acceptance

A run is accepted if:

- all files in the frozen snapshot are processed,
- output corpus shape is complete,
- unresolved artifact is present,
- aggregate counters are internally consistent (processed totals and unresolved totals).

## 6) Deliverables

- Preprocessed corpus snapshot (without changing mention text/spans).
- Aggregate run report.
- Unresolved cases file for curation and audit.
