---
title: Project 33
---

# Project 33

**Vers3Dynamics | Applied Aerospace Research**

## 1. What Project 33 is

A low-cost folding-fin/canard rocket testbed, built as an engineering system in which models, software, hardware behavior, measurements, assumptions, failures, and open questions stay connected through inspectable evidence. The rocket is the specimen; the evidence record is the product.

## 2. Current validation stage

**Bench-validation prototype.** Models, CAD, firmware, a telemetry dashboard, and automated checks exist. No physical measurement has been accepted into the evidence record. It is not a flight-tested system and makes no live-propulsion claim.

<!-- evidence:counts -->
**Record state:** 8 claims · 3 contradicted · 4 unresolved · 1 supported within stated limits · 0 accepted physical measurements · 17 open discrepancies of 24 · 5 of 5 predictions not measured.
<!-- /evidence:counts -->

## 3. Evidence Observatory

The [Evidence Observatory](docs/EVIDENCE_OBSERVATORY.md) answers, for each claim: what is claimed, which exact files support it, what class of evidence they are (analytical, simulated, synthetic, software-verified, bench-observed, bench-measured), which requirements it meets or misses, what contradicts it, which reviews a change has made insufficient, and which measurements are still missing. Support is derived from evidence classes and cannot be authored; a model never becomes a measurement.

Its portable review packets run offline on Python's standard library, carry every cited file with its SHA-256 digest, and state separately what was checked: bundle integrity, record consistency, software tests, model reproduction, firmware build. Physical performance is reported as not established; flight readiness as not assessed.

## 4. The engineering system

Question → model → registered prediction → implementation → pre-registered inert test → captured session → audit and passport → **named human acceptance** → comparison → claim review.

The dashboard talks to the launcher over UDP; the launcher owns the WiFi access point, physical arming controls, and the UART bridge to the rocket; the rocket owns IMU roll sensing, canard servos, and its own arming state. See [Architecture](docs/ARCHITECTURE.md), [Protocol](docs/PROTOCOL.md), and [Wiring](docs/WIRING.md).

## 5. C1–C8 claim status

<!-- evidence:claims-table -->
**Record state:** 8 claims · 3 contradicted · 4 unresolved · 1 supported within stated limits · 0 accepted physical measurements · 17 open discrepancies of 24 · 5 of 5 predictions not measured.

| Claim | Subject | Status | Strongest accepted evidence | Failing or disputed requirements | Open discrepancies |
|---|---|---|---|---|---|
| [C1](docs/claims/C1.md) | Folding-fin mechanism model | **CONTRADICTED** | MODEL ONLY | R-C1-CLOSURE NOT SATISFIED | D-002, D-004, D-005 |
| [C2](docs/claims/C2.md) | Deployment timing | **UNRESOLVED** | IMPLEMENTATION ONLY | none failing | D-017, D-018, D-024 |
| [C3](docs/claims/C3.md) | CAD generator software | **SUPPORTED WITHIN STATED LIMITS** | IMPLEMENTATION ONLY | none failing | none |
| [C4](docs/claims/C4.md) | Material mass accounting | **UNRESOLVED** | MODEL ONLY | none failing | D-010, D-022 |
| [C5](docs/claims/C5.md) | Static-stability model | **UNRESOLVED** | MODEL ONLY | R-C5-WINDOW MODELS DISAGREE | D-006, D-007, D-008, D-009, D-023 |
| [C6](docs/claims/C6.md) | Spring margin consistency | **CONTRADICTED** | MODEL ONLY | R-C6-MARGIN NOT SATISFIED | D-009, D-010, D-011 |
| [C7](docs/claims/C7.md) | Deployment reliability evidence | **UNRESOLVED** | MODEL ONLY | none failing | D-010, D-013 |
| [C8](docs/claims/C8.md) | Structural claim boundaries | **CONTRADICTED** | MODEL ONLY | R-C8-MODULUS NOT SATISFIED | D-009, D-010, D-015 |
<!-- /evidence:claims-table -->

## 6. Current evidence

![C1 loop-closure check: the output circle never meets the coupler circles](/33/docs/assets/review/c1_loop_closure.svg)

*C1: the specified four-bar cannot close at any drive angle. Rendered from the tested model; geometry only.*

![C3: NACA 0012 fin profile, 60 mm chord](/33/docs/assets/review/c3_naca0012_profile.svg)

*C3: generated fin profile with chord and maximum thickness. Geometry says nothing about aerodynamic performance.*

The complete requirement matrix and prediction ledger are in [Traceability](docs/TRACEABILITY.md); every recorded mismatch is in the [Discrepancy register](docs/DISCREPANCIES.md).

## 7. Known gaps

- No accepted inert bench measurement of anything: timing, spring rate, masses, CG, servo authority, gyro drift, interlocks.
- The C1 linkage dimensions cannot form a closed loop; the intended topology needs human review.
- Two static-margin formulations disagree about the C5 window; the script's motor differs from the OpenRocket model.
- The mass, spring, reliability, and structural models do not share a design point.
- Live telemetry timestamps are launcher relay times; the protocol has no sequence number or boot identifier.

## 8. Validation roadmap

Analytical model → software reproduction → synthetic test → inert bench setup → inert physical measurement → repeated measurement → independent review. Gates from inert bench setup onward require a human-registered pre-registration or a human-accepted measurement. See the [Roadmap](docs/ROADMAP.md) and [Project Status](docs/PROJECT_STATUS.md).

## 9. Safety boundary

Inert bench validation, simulation, and engineering review only. Dashboard launch is rejected by default in firmware; the physical arming switch, readiness handshake, heartbeat timeout, and rocket-side arming state remain in force, and refusals are logged. No AI feature or automated tool has authority over any gate. Field testing is a separate, safety-reviewed process outside this repository. See [Safety](docs/SAFETY.md).

## 10. Reproduce the review

```bash
python -m evidence status
python -m evidence check
python -m evidence build --output build/review
python -m evidence verify build/review
```

Open `build/review/index.html`. No network, account, or hardware is needed. CI retains review packets with the test and model-reproduction run records attached.

## Project documents

- [Project status and readiness matrix](docs/PROJECT_STATUS.md)
- [Evidence Observatory and offline review workflow](docs/EVIDENCE_OBSERVATORY.md)
- [Claim passports](docs/claims/README.md)
- [Paper integration and evidence traceability](docs/PAPER_ALIGNMENT.md)
- [Validation roadmap](docs/ROADMAP.md)
- [Bench session evidence](docs/BENCH_SESSIONS.md)
- [CAD assemblies and materials](docs/CAD_ASSEMBLIES.md)
- [Testing and evidence plan](docs/TESTING.md)
- [Safety and test boundaries](docs/SAFETY.md)
- [Bill of materials](docs/BOM.md)

![OpenRocket 3D model](/33/Simulation/OpenRocket_3D_View.png)

*OpenRocket export; the model revision that produced it is not recorded (D-023).*
