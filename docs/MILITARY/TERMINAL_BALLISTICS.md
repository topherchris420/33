# Terminal Ballistics Estimates — MODELED

**Phase 2 · Evidence class: MODELED.** Closed-form engineering estimates at
the shared design point; no arena or firing-range test has been performed.
Generator: `Simulation/warheads.py`; record:
[`docs/EVIDENCE/WH_loadouts.json`](../EVIDENCE/WH_loadouts.json).
Live-fire validation is a Phase 6.4 gate.

## Summary table

| Loadout | Effect | Estimate (MODELED) | Confidence |
|---|---|---|---|
| GP HE-Frag | Casualty radius vs personnel | **≈ 6.8 m** (50% hit + 58 J) | MODERATE |
| GP HE-Frag | Fragment velocity | 2,091 m/s (Gurney) | MODERATE |
| HEAT | RHA penetration | **62–93 mm**, normal incidence, 2 CD standoff | MODERATE |
| HEAT | Optimal standoff | 116–174 mm | MODERATE |
| EFP | RHA penetration | **28–44 mm** at 1–50 m standoff | LOW-TO-MODERATE |
| EFP | EFP velocity | ≈ 2,300 m/s | LOW-TO-MODERATE |

## Method and stated assumptions

- **Fragments:** Gurney cylinder relation (Comp A5, sqrt(2E) = 2,600 m/s),
  spherical drag (Cd 0.47, sea level), ~0.2 g natural-fragment class with
  half the case mass fragmenting usefully (~287 effective fragments). The
  casualty radius is governed by the SPATIAL-DENSITY limit (hemispherical
  spread onto a 0.5 m² presented human, 50% hit probability), not by
  fragment energy: the energy-limited radius (67 m at 58 J) is far larger
  than the spread-limited 6.8 m.
- **HEAT:** hydrodynamic jet estimate P ≈ L_jet·sqrt(ρ_jet/ρ_target) with
  jet length 1.0–1.5 liner CD for a well-designed 60° copper cone —
  consistent with the P/CD ≈ 1–2 band typical of charges this size.
- **EFP:** Gurney plate relation for velocity and the 0.5–0.8 CD
  penetration band from small-EFP literature; EFP performance is the most
  fabrication-sensitive number in this table.

## Engineering reading

- GP: defeat personnel in the open or behind light cover within ~7 m of
  burst; delay option lets it penetrate light structures first.
- HEAT: defeats APC/IFV-class side and roof armor; it does NOT defeat MBT
  frontal armor. Optimal standoff requires the probe + PD point-initiate.
- EFP: vehicle kill at standoff where the airframe cannot or should not
  close; lowest confidence, widest scatter.

## What would falsify these numbers

Phase 6.4 gates: arena fragment spread/velocity; liner penetration firing
table; EFP target board at 10/25/50 m.
