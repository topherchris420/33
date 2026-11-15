# Warhead Loadout Claim Passports — MODELED

**Phase 2 · Date 2026-11-14 · Evidence class: MODELED.** No warhead has been
built, weighed, or detonated. Every figure below comes from
`Simulation/warheads.py` at the shared design point
(`design_point.json`), recorded in [`docs/EVIDENCE/WH_loadouts.json`](../EVIDENCE/WH_loadouts.json).
Live-fire validation is Phase 6.

## Bay design (common to all loadouts)

- **Location:** forward bay ahead of the CG — nose cone interior plus the
  first 60 mm of the forward body; canard servo ring sits aft of the bay.
- **Envelope:** 70 mm OD × 85 mm long, threaded 7075-T6 or heat-treated
  steel case.
- **Constant-mass rule:** every loadout totals **250 g** (case + liner + fill
  + structural ballast ring), so all loadouts share the Phase 1 mass
  properties. No re-trim of fins or ballast when changing loadout.
- **Static margin check (re-balance requirement):** SM = **1.66 cal at
  ignition → 1.76 cal at burnout for every loadout**, inside the required
  [1.5, 2.0] window. Same value for GP/HEAT/EFP by design.

## Loadout (a) — GP HE-Fragmentation, ~250 g

| Property | Value (MODELED) |
|---|---|
| Explosive | 110 g Composition A5 (~127 g TNT-eq) |
| Case | 115 g heat-treated fragmenting steel, ~0.2 g fragment class |
| Ballast | 25 g structural ring |
| Fragment launch velocity | 2,091 m/s (Gurney cylinder) |
| Effective fragments | ~287 |
| **Casualty radius** | **≈ 6.8 m** vs personnel (50% hit + 58 J criteria; the spatial-density limit, not fragment energy, governs) |
| Fuze | Contact PD, delay-selectable 0/5/10/20 ms |
| Confidence | MODERATE — closed-form estimates, no arena test |

## Loadout (b) — HEAT shaped charge, anti-armor

| Property | Value (MODELED) |
|---|---|
| Explosive | 120 g Composition B |
| Liner | 50 g OFHC copper, 60° cone, 58 mm CD |
| Case + wave shaper | 60 g |
| Ballast | 20 g |
| Jet penetration | **62–93 mm RHA** at normal incidence (hydrodynamic jet estimate, jet length 1.0–1.5 CD) |
| Optimal standoff | 116–174 mm (2–3 CD), provided by the standoff probe |
| Fuze | Contact PD through standoff probe (point-initiate at 2 CD) |
| Confidence | MODERATE — shaped-charge performance is highly design-sensitive |
| Defeats | APC/IFV side and roof armor (30–50 mm RHA class); **not** MBT frontal armor |

## Loadout (c) — EFP, ~150 g effective

| Property | Value (MODELED) |
|---|---|
| Explosive | 95 g Composition A5 |
| Liner | 40 g armco iron or OFHC copper dish, 55 mm CD |
| Case | 55 g |
| Ballast | 60 g |
| EFP velocity | ≈ 2,300 m/s |
| Penetration | **28–44 mm RHA** at 1–50 m standoff |
| Fuze | RF proximity (2–6 m gate) or contact PD |
| Confidence | LOW-TO-MODERATE — EFP performance scatters widely with liner fabrication |
| Defeats | Light-skinned vehicles, APC roofs at standoff, soft targets to 50 m |

## What would falsify these numbers

- Arena fragment test (Phase 6.4) against the casualty radius.
- Liner firing table (Phase 6.4) against the penetration bands.
- Bay mass weighing (constant-mass rule compliance).
