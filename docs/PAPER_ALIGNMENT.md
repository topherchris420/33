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
| **C5** | Static-margin and stability claims | Barrowman computation from `.ork` geometry yields SM ∈ [1.55, 1.57] cal, within [1.5, 2.0] window | Verified. Evidence: `docs/EVIDENCE/C5_static_margin.md` |
| **C6** | Torsion spring sizing | k_min = 184.9 N·m/rad at design point (v=205 m/s). k_supplied = 220 N·m/rad → 19% margin | Verified. Evidence: `docs/EVIDENCE/C6_spring_sizing.md` |
| **C7** | Deployment reliability | Monte Carlo sweep (seed=33, n=10000) yields 100.00% success rate, exceeding 99.9% threshold | Verified. Evidence: `docs/EVIDENCE/C7_reliability.md` |
| **C8** | Structural and Composite CLT | CLT Ex=56.68 GPa (compensated by thickness). FoS = 1.88 (> 1.5 minimum) | Verified. Evidence: `docs/EVIDENCE/C8_clt.md` and `C8_hinge_fos.md` |

## Implementation Notes

All eight engineering claims (C1–C8) have been integrated with purely analytical and firmware-safe validation tools. Safety boundaries remain entirely intact: the ESP32 deployment ISR uses hardware timers without blocking main-loop telemetry or overriding hard `mpuHealthy` gates.

Three claims (C5, C6, C8) previously showed >10% divergence due to mismatched physical parameters between the `.ork` file and the paper's design point. These have been resolved by updating the fin geometry (C_R=130mm, C_T=110mm, S=180mm), fin mass (154g), hinge gap (19.4mm), and egress velocity (205 m/s) to a unified, physically consistent design point. The full resolution history is documented in `docs/EVIDENCE/CHANGELOG.md`.
