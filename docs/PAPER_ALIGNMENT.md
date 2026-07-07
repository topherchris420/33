# Paper Integration and Evidence Traceability

This document records how the local Project 33 paper was reviewed against the repository. The source PDF was reviewed from `Downloads/main_tex (2).pdf`; the PDF itself is not committed here.

## Integration Boundary

Project 33 remains an inert bench-validation prototype for simulation, CAD review, firmware checks, dashboard logging, and supervised educational testing. The paper's tactical, weaponized, live-test, and advanced guidance framing is not adopted by this repository and does not create a flight-readiness or live-propulsion claim.

No integration work in this repository should:

- enable dashboard launch by default;
- bypass arming, ignition, actuator, or interlock gates;
- add targeting, live-fire, or autonomous guidance behavior;
- replace evidence gaps with estimated performance claims.

## Traceability Matrix (C1-C8 Verified)

| Claim | Paper theme | Repository integration | Evidence status |
|-------|-------------|------------------------|-----------------|
| **C1** | Four-bar folding-fin mechanism | Kinematic analysis of Grashof condition, transmission angle, and over-center locking | Implemented in `mechanism/four_bar.py` and `tests/test_four_bar.py`. Evidence: `docs/EVIDENCE/C1_four_bar.md` |
| **C2** | Zero-blocking hardware deployment | ESP32 hardware timer (`esp_timer`) ISR triggering fin deployment | Implemented in `Firmware/Rocket/src/deploy_isr.h/cpp` and `tests/test_firmware_safety.py`. Evidence: `docs/EVIDENCE/C2_latency.md` |
| **C3** | NACA 4-digit fin profile generation | Parametric generation and STEP extrusion/sweep of true NACA 0012 profiles | Implemented in `CAD Files/naca_fin_generator.py` and `tests/test_naca_fin_generator.py`. Evidence: `docs/EVIDENCE/C3_naca_sweep.md` |
| **C4** | Material substitutions | Substitution of baseline Al/PLA for CFRP/Ti-6Al-4V yielding 30-40% mass reduction | Implemented in `materials/mass_rollup.py` and `tests/test_mass_rollup.py`. Evidence: `docs/EVIDENCE/C4_delta.md` |
| **C5** | Static-margin and stability claims | **FAILED**: Barrowman computation proves SM is strongly negative (unstable) over motor burn, contradicting paper claim | Implemented in `simulation/static_margin.py` and `tests/test_static_margin.py`. Evidence: `docs/EVIDENCE/C5_static_margin.md` |
| **C6** | Torsion spring sizing | Minimum spring rate $k$ for aerodynamic hinge-moment with > 20% margin | Implemented in `mechanism/spring_sizing.py` and `tests/test_spring_sizing.py`. Evidence: `docs/EVIDENCE/C6_spring_sizing.md` |
| **C7** | Deployment reliability | Monte Carlo sweep simulating tolerances to confirm 99.9% deployment success | Implemented in `simulation/reliability_sweep.py` and `tests/test_reliability.py`. Evidence: `docs/EVIDENCE/C7_reliability.md` |
| **C8** | Structural and Composite CLT | Quasi-isotropic CFRP properties and Ti-6Al-4V hinge-pin FoS > 1.5 | Implemented in `structures/fea_lite.py` and `tests/test_structural.py`. Evidence: `docs/EVIDENCE/C8_clt.md` and `C8_hinge_fos.md` |

## Implementation Notes

The eight engineering claims (C1-C8) have been successfully integrated with purely analytical and firmware-safe validation tools. Safety boundaries remain entirely intact: the ESP32 deployment ISR uses hardware timers without blocking main-loop telemetry or overriding hard `mpuHealthy` gates. Validation is guaranteed through the `make evidence` target and CI workflow checks.
