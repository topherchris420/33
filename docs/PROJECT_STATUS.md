# Project Status and Readiness Matrix

Project 33 is a bench-validation prototype. Every status below names the class of evidence behind it. Where the answer is "not measured", that is the status, not a gap in this document.

## Claim status

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

Passports: [docs/claims](claims/README.md). Requirements and predictions: [Traceability](TRACEABILITY.md). Mismatches: [Discrepancies](DISCREPANCIES.md).

## Status snapshot

| Dimension | Current state | Evidence class |
|-----------|---------------|----------------|
| Lifecycle stage | Bench-validation prototype | Specification |
| Flight claim | No flight-test claim | — (outside the validation boundary; see [SAFETY.md](SAFETY.md)) |
| Simulation | OpenRocket model and reference static-margin script; an independent formulation disagrees (D-006) | Analytical |
| Mechanical design | Fusion 360 archives; C1 linkage dimensions cannot close (D-002) | Implementation / analytical |
| Rocket firmware | Compiles in CI; arming, deploy, and refusal logging checked in source | Implementation; not bench-verified |
| Launcher firmware | Compiles in CI; every gate in the safety registry checked in source | Implementation; not bench-verified |
| Dashboard | Writes raw sessions with metadata, command log, gain windows, and live quality counters | Implementation; exercised only with synthetic packets |
| Bench evidence | Session passport and human-acceptance workflow exist; no session is registered | None — NOT MEASURED |
| Evidence Observatory | Record validation, requirement evaluation, staleness, reproduction, portable packets | Software verified in CI |
| Safety posture | Inert bench validation only; dashboard launch rejected by default | Implementation |

## Readiness matrix

| Capability | Readiness | What would close the next gate |
|------------|-----------|--------------------------------|
| Repository reproducibility | Ready for review | CI green: protocol check, tests, model reproduction, record check, firmware builds |
| Model integrity | Not ready | Human review of D-002 (C1 topology), D-006 (C5 formulation), D-010 (shared design point) |
| Protocol and wiring traceability | Ready for review | Generated protocol and wiring tests stay synchronized |
| CAD package | Partial | Annotated Fusion exports; C1 CAD cannot be regenerated until D-002 is resolved |
| Rocket firmware bench behavior | NOT MEASURED | A human registers P-001; an inert session is captured, audited, and accepted |
| Launcher interlock behavior | NOT MEASURED | Inert session showing switch, READY, abort, and CMD_REJECT rows, accepted by a named reviewer |
| Dashboard evidence capture | Ready for review | One accepted inert session package |
| Flight readiness | Not claimed | A separate safety review, test-range process, and qualified supervision outside this repository |

## Evidence standard

If the repository says it happened, it points to an artifact, and the artifact's class says what it can show. Acceptable artifacts are source, generated records, CI run records, model outputs, bench CSVs, graphs, photos, and explicit **NOT MEASURED** entries.

Do not fabricate or imply flight, propulsion, or live-ignition results. If a test was not run, say so and list the next evidence needed. A passing test is not a qualification result; a clean dataset is not proof of a physical event.

## Current gaps

- No accepted physical measurement of any quantity.
- C1: the specified linkage cannot be assembled; over-center locking is not modeled.
- C5: reference and textbook fin-term formulations disagree; the script burns a different motor than the OpenRocket file.
- C6: calculated spring margin is 19.0%, below the stated 20%.
- C7: the reliability simulation cannot produce the failures it counts.
- C8: laminate modulus is below the aluminium comparison.
- No shared design point across C4, C6, C7, and C8.
- Live telemetry carries launcher relay time; no sequence number or boot identifier.

## Submission package checklist

- `python -m evidence check` passes: no stale review, prediction drift, or stale generated document.
- CI checks pass: protocol generation, tests, model reproduction, firmware builds.
- Any bench evidence goes through the session passport and is accepted by a named human before it is cited.
- Limitations sit next to the claim they qualify; unresolved claims stay visible.
- Safety gates are documented before any command path or actuator behavior is described.
