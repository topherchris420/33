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

| Paper theme | Repository integration | Evidence status |
|-------------|------------------------|-----------------|
| NACA 4-digit fin profile generation | The Fusion helper exposes a testable NACA coordinate generator with chord-scaled millimeter output. | Implemented in `CAD Files/naca_fin_generator.py` and covered by `tests/test_naca_fin_generator.py`. |
| Control-loop latency and blocking behavior | Existing firmware safety gates remain authoritative. Timing work is limited to future bench-safe refactors that preserve command rejection and interlocks. | Not adopted as a deployment or launch capability. |
| Four-bar folding-fin mechanism | Treated as a future CAD-only review item unless supported by inert render exports, dimensions, and bench evidence. | Not implemented. |
| Material substitutions | The repository continues to describe the current inert prototype material plan. Aerospace material claims require vendor specs, drawings, and physical evidence before adoption. | Not evidenced. |
| Static-margin and stability claims | Existing OpenRocket files and images remain the current evidence. New numeric claims require committed simulation exports and assumptions. | Not adopted beyond existing simulation artifacts. |

## Implementation Notes

The safe code-level integration is the NACA profile generator because it supports non-actuating CAD review and does not alter launch, ignition, guidance, or safety behavior. The generator now separates pure coordinate calculation from the Fusion 360 API wrapper so CI can test the math without requiring Fusion.

Future paper-to-repo updates should add evidence first, then claims. If a claim cannot point to source, generated artifacts, bench logs, photos, or simulation exports, it should stay in this document as planned work rather than move into the README.
