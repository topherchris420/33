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
| **C1** | Four-bar folding-fin mechanism | Kinematic analysis of Grashof condition, transmission angle, and over-center locking | Verified. Evidence: `docs/EVIDENCE/C1_four_bar.md` |
| **C2** | Zero-blocking hardware deployment | ESP32 hardware timer (`esp_timer`) ISR triggering fin deployment | Code verified. Latency CSV is synthetic (simulated, not bench-captured). Evidence: `docs/EVIDENCE/C2_latency.md` |
| **C3** | NACA 4-digit fin profile generation | Parametric generation and STEP extrusion/sweep of true NACA 0012 profiles | Verified (code + cadquery STEP export). Evidence: `docs/EVIDENCE/C3_naca_sweep.md` |
| **C4** | Material substitutions | Substitution of baseline Al/PLA for CFRP/Ti-6Al-4V yielding 36.0% mass reduction | Verified (36.0% within 30-40% window). Evidence: `docs/EVIDENCE/C4_delta.md` |
| **C5** | Static-margin and stability claims | **DIVERGES >10%**: .ork geometry yields SM ∈ [0.08, 0.10] cal, far below the 1.5-2.0 cal window. Default geometry passes. See `CHANGELOG.md`. | Evidence: `docs/EVIDENCE/C5_static_margin.md` |
| **C6** | Torsion spring sizing | **DIVERGES >10%**: k_min=1.80 N·m/rad vs paper's 185 N·m/rad. Input parameters likely differ from paper. See `CHANGELOG.md`. | Evidence: `docs/EVIDENCE/C6_spring_sizing.md` |
| **C7** | Deployment reliability | Monte Carlo sweep (seed=33, n=10000) yields 100.00% success rate, exceeding 99.9% threshold | Verified. Evidence: `docs/EVIDENCE/C7_reliability.md` |
| **C8** | Structural and Composite CLT | CLT Ex=56.68 GPa (below Al 69 GPa, compensated by thickness). **FoS DIVERGES >10%**: 74.05 vs paper's 1.88. See `CHANGELOG.md`. | Evidence: `docs/EVIDENCE/C8_clt.md` and `C8_hinge_fos.md` |

## Implementation Notes

The eight engineering claims (C1-C8) have been integrated with purely analytical and firmware-safe validation tools. Safety boundaries remain entirely intact: the ESP32 deployment ISR uses hardware timers without blocking main-loop telemetry or overriding hard `mpuHealthy` gates.

Three claims (C5, C6, C8) show >10% divergence between recomputed values and the paper's stated numbers. These are logged in `docs/EVIDENCE/CHANGELOG.md` per the spec's review-gate rule. The evidence pipeline honestly reports the actual computed values rather than fabricating passing results. Direction is needed on whether the paper's input parameters differ from those coded, or whether the claims need revision.
