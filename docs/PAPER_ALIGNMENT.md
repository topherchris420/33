# Paper Integration and Evidence Traceability

This document records how the local Project 33 paper was reviewed against the repository. The source PDF was reviewed from `Downloads/main_tex (2).pdf`; the PDF itself is not committed here, so the paper's statements appear in the record only as the historical claim text preserved in `evidence/archive/notes-v1/` and as the `source` of each requirement.

## Integration boundary

Project 33 remains an inert bench-validation prototype for simulation, CAD review, firmware checks, dashboard logging, and supervised educational testing. The paper's tactical, weaponized, live-test, and advanced guidance framing is not adopted by this repository and does not create a flight-readiness or live-propulsion claim.

No integration work in this repository should:

- enable dashboard launch by default;
- bypass arming, ignition, actuator, or interlock gates;
- add targeting, live-fire, or autonomous guidance behavior;
- replace evidence gaps with estimated performance claims.

## Paper themes and where they live

| Claim | Paper theme | Repository integration |
|-------|-------------|------------------------|
| C1 | Four-bar folding-fin mechanism with over-center locking | Planar loop-closure model, parameter sweep, loop-closure figure |
| C2 | Zero-blocking hardware-timed deployment | esp_timer implementation, synthetic timing fixture, proposed inert timing protocol (P-001) |
| C3 | NACA 4-digit fin profile generation | Parametric generator, STEP export tests, profile figure |
| C4 | Material substitutions and mass reduction | Four-part mass rollup with an explicit exclusion list |
| C5 | Static-margin window | Reference Barrowman script and an independent textbook cross-check |
| C6 | Torsion-spring sizing with margin | Design-point record and sensitivity sweep |
| C7 | Deployment reliability from Monte Carlo | Seeded simulation with an explicit run record |
| C8 | Composite layup stiffness and hinge-pin factor of safety | Classical laminate theory and a closed-form pin check |

## Current status of each claim

<!-- evidence:claims-table -->
**Record state:** 8 claims · 3 contradicted · 4 unresolved · 1 supported within stated limits · 0 accepted physical measurements · 17 open discrepancies of 24 · 5 of 5 predictions not measured.

| Claim | Subject | Status | Strongest accepted evidence | Failing or disputed requirements | Open discrepancies |
|---|---|---|---|---|---|
| [C1](claims/C1.md) | Folding-fin mechanism model | **CONTRADICTED** | MODEL ONLY | R-C1-CLOSURE NOT SATISFIED | D-002, D-004, D-005 |
| [C2](claims/C2.md) | Deployment timing | **UNRESOLVED** | IMPLEMENTATION ONLY | none failing | D-017, D-018, D-024 |
| [C3](claims/C3.md) | CAD generator software | **SUPPORTED WITHIN STATED LIMITS** | IMPLEMENTATION ONLY | none failing | none |
| [C4](claims/C4.md) | Material mass accounting | **UNRESOLVED** | MODEL ONLY | none failing | D-010, D-022 |
| [C5](claims/C5.md) | Static-stability model | **UNRESOLVED** | MODEL ONLY | R-C5-WINDOW MODELS DISAGREE | D-006, D-007, D-008, D-009, D-023 |
| [C6](claims/C6.md) | Spring margin consistency | **CONTRADICTED** | MODEL ONLY | R-C6-MARGIN NOT SATISFIED | D-009, D-010, D-011 |
| [C7](claims/C7.md) | Deployment reliability evidence | **UNRESOLVED** | MODEL ONLY | none failing | D-010, D-013 |
| [C8](claims/C8.md) | Structural claim boundaries | **CONTRADICTED** | MODEL ONLY | R-C8-MODULUS NOT SATISFIED | D-009, D-010, D-015 |
<!-- /evidence:claims-table -->

A paper statement becomes a requirement in `evidence/requirements.json`, evaluated from committed values and labeled with the evidence class of the value. Where the repository's own models contradict the paper (C1 closure, C6 margin, C8 modulus) or disagree with each other (C5), that is recorded, not rounded. Passports: [docs/claims](claims/README.md).

## Matching a target is not validation

`docs/EVIDENCE/CHANGELOG.md` records that model inputs for C5, C6, and C8 were revised until the results matched the paper's numbers, and marked those items "resolved". The pre-revision OpenRocket model is preserved in the failure archive. Changing inputs until a model agrees with a target is not independent validation; each revised input needs an independent source (drawing, datasheet, or measurement). This is discrepancy D-009.

Use the [Evidence Observatory](EVIDENCE_OBSERVATORY.md) to inspect the exact files, classes, requirements, and open questions together. A successful review build checks record consistency and file integrity; it is not a scientific acceptance test.
