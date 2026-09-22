# Paper Integration and Evidence Traceability

This document records how the local Project 33 paper was reviewed against the repository. The source PDF was reviewed from `Downloads/main_tex (2).pdf`; the PDF itself is not committed here.

## Integration Boundary

Project 33 remains an inert bench-validation prototype for simulation, CAD review, firmware checks, dashboard logging, and supervised educational testing. The paper's tactical, weaponized, live-test, and advanced guidance framing is not adopted by this repository and does not create a flight-readiness or live-propulsion claim.

No integration work in this repository should:

- enable dashboard launch by default;
- bypass arming, ignition, actuator, or interlock gates;
- add targeting, live-fire, or autonomous guidance behavior;
- replace evidence gaps with estimated performance claims.

## Traceability Matrix

| Claim | Paper theme | Repository integration | Evidence status |
|-------|-------------|------------------------|-----------------| 
| **C1** | Four-bar folding-fin mechanism | Existing kinematic model and parameter sweep | Analytical only; no assembled-mechanism measurement. `docs/EVIDENCE/C1_four_bar.md` |
| **C2** | Zero-blocking hardware deployment | Timer implementation plus a 21-row synthetic timing fixture | Unresolved: synthetic rows do not establish hardware timing. `docs/EVIDENCE/C2_latency.md` |
| **C3** | NACA 4-digit fin profile generation | Parametric generator and STEP-export regression source | Software evidence; generated geometry does not establish physical performance. `docs/EVIDENCE/C3_naca_sweep.md` |
| **C4** | Material substitutions | Baseline and candidate mass calculations | Analytical only; no as-built weigh-in. `docs/EVIDENCE/C4_delta.md` |
| **C5** | Static-margin and stability claims | Existing model input and calculated static margin | Analytical only; applicability and uncertainty require review. `docs/EVIDENCE/C5_static_margin.md` |
| **C6** | Torsion spring sizing | Reported 19% margin against a stated requirement of at least 20% | Unresolved: the stated percentage is not met and the legacy test does not enforce that bound. `docs/EVIDENCE/C6_spring_sizing.md` |
| **C7** | Deployment reliability | Seeded simulation source and a failure-only CSV | Unresolved: a header-only CSV cannot establish the trial denominator; simulation does not measure physical reliability. `docs/EVIDENCE/C7_reliability.md` |
| **C8** | Structural and Composite CLT | Simplified material and hinge calculations | Unresolved: material modulus and component stiffness are different quantities; no physical qualification. `docs/EVIDENCE/C8_clt.md` and `C8_hinge_fos.md` |

Use the [Evidence Observatory](EVIDENCE_OBSERVATORY.md) to inspect the exact source
files, classifications, assumptions, and open questions together. The executable
catalog in `evidence/catalog.json` replaces the former blanket "Verified" labels
with explicit limits. A successful review build checks artifact availability and
integrity; it is not a scientific acceptance test.

## Implementation Notes

All eight claim themes (C1–C8) have corresponding code or authored evidence notes.
That traceability does not establish that the claims are physically true. The
offline review workflow does not exercise or modify actuation or command paths.

Historical parameter changes intended to align C5, C6, and C8 with paper targets
are recorded in `docs/EVIDENCE/CHANGELOG.md`. Matching a target by revising model
inputs is not independent validation. Input provenance, cross-model consistency,
and physical applicability remain review questions.
