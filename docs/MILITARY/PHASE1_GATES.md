# Phase 1 Gate Report — Stabilize the Platform

**Date:** 2026-11-14 · **Authority:** program sponsor direction of 2026-11-14 ·
**Engineer:** chief weapons engineer · **Evidence class of everything below:
MODELED.** Nothing in this report is a physical measurement.

## Gate 1 — Linkage closes and locks over-center (D-002, D-004, D-005): PASS

| Item | Result |
|---|---|
| Redesigned linkage (design_point.json) | ground 25, crank 14, coupler 15.5, output 15 mm |
| Closure over the full deployment stroke | **CLOSES at every pose** (1,201 poses, every link length self-checked; the historical 25/60/15/15 linkage closed at none) |
| Fin stroke | folded flush → 90° hard stop, monotone, 103.7° crank sweep |
| Over-center lock | toggle at fin 91.55°, **1.55° beyond the stop** (8.8° of crank margin); Kennedy toggle condition verified where \|AC\| = b + c |
| Back-drive ratio at stop | **0.363** — fin hinge moments reach the crank attenuated; spring preload 5.76 N·m must be overcome to fold back |
| Transmission over power stroke (ψ 20°→90°) | **42.2°–75.3°**, inside the 40–140° window |
| Tolerance robustness | worst-case ±0.15 mm on all four links still assembles at the stop; radial closure margin at stop 17.4 mm |
| CAD | Fusion script + STEP regenerated at the verified deployed-stop pose |

## Gate 2 — Static-margin derivation resolved (D-006, D-007, D-008, D-009): PASS

- **Which model was wrong:** the reference `static_margin.py`. It put the root
  chord where the tip-leading-edge sweep belongs (fin CP term) and the sweep
  length where the mid-chord line length belongs (normal-force term). Both
  errors pushed the CP aft and inflated the margin. The textbook cross-check
  was right. Compounding: ogive coefficient on an ellipsoid nose, Estes C6-5
  instead of the G64W, nose mass omitted, canards ignored.
- **Truth at the old geometry: ≈0.70 cal — the rocket was under-stable.**
- **Fix:** fins resized to 160×220 mm rectangles, leading edge at 440 mm; nose
  carries a 250 g warhead simulator (Phase 2 loadout mass). Explicit component
  mass model replaces ambiguous tube overrides; G64W certified motor data
  (thrustcurve.org); fin stations now follow OpenRocket axial semantics
  (canards at 0.180 m, main fins at 0.440 m, both absolute).
- **Result (revision 3 model): SM = 1.66 cal at ignition → 1.76 cal at
  burnout — inside [1.5, 2.0] across the entire burn.**
- **Independent check:** spanwise strip integration + discrete nose sums agree
  with the closed form within 0.001 mm (CP) and 0.007% (CN).

## Gate 3 — Deployment reliability ≥ 99% (D-010, D-011, D-013): PASS

- Shared design point created (D-010 resolved): `design_point.json`, read by
  every model.
- Spring redesigned to drive the four-bar crank: k_min = 7.82 N·m/rad
  (lock-dominated), specified 11.0 N·m/rad → **40.7% margin** (≥ 20%
  requirement, D-011 resolved).
- Monte Carlo rebuilt (D-013 resolved) with reachable failure modes:
  **9,993 / 10,000 = 99.93%** (sponsor gate ≥ 99%: PASS; repository
  requirement ≥ 99.9%: PASS). All 7 failures are the stop-angle
  manufacturing-tolerance tail — the actionable engineering finding is that the
  fin stop should be toleranced to ±0.5° or better.

## Firmware changes this phase

- **MIL-DEV-010:** deploy trigger re-derived for rail launch — 2.0 g
  sustained 150 ms replaces the 15 g one-shot threshold the G64W could never
  reach on this mass. Safety gate G-11 updated accordingly.

## Test status

Full Python suite at the Phase 1 commit: see CI. The militarized analysis
is covered by new tests in `tests/test_four_bar.py`, `tests/test_static_margin.py`,
`tests/test_reliability.py`; the evidence record (requirements, discrepancies,
claim passports) was regenerated through `python -m evidence docs`.

## What is still NOT established

- No physical mechanism, spring, fin, or airframe has been built or measured.
- Static margin is a model; the physical CG is unmeasured (PRED-C5-DRY-CG).
- The ignition-vs-deployment ordering question (D-017) remains open for the
  Phase 6 live-fire program design.
- The ellipsoid-nose CP derivation and the strip-integration cross-check
  validate algebra, not physics.

**Phase 1 gates are met. Proceeding to Phase 2 — Make It a Munition.**
