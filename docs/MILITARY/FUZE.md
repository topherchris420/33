# Fuze and S&A Design — MODELED

**Phase 2 · Evidence class: MODELED (design) / IMPLEMENTATION (firmware).**
No fuze hardware has been built; no initiation chain has been bench-validated
(Phase 6.1 does that).

## Baseline: contact / point-detonating (all loadouts)

- Nose crush switch (piezo or collapsible-structure contact) as the primary
  target sensor; the crush crown is part of the nose cone.
- All-way accelerometer impact backup: deceleration event >8 g sustained with
  the |velocity| change signature of impact, so soft or glancing hits still
  initiate.
- **Delay-selectable:** 0 ms (GP frag, air-target), 5/10 ms (penetrating GP
  against cover), 20 ms max. Delay selected by loadout pin or launcher
  upload; default 0.

## Standoff option: RF proximity

- 5.8 GHz CW Doppler module, 0.5–2 mW radiated, gated **2–6 m**; designed for
  the HEAT loadout's 2–3 CD optimal standoff and for EFP employment.
- Simple, single-chip RF head + range-gate comparator; no target
  classification. Designed against clutter by velocity gating.
- Acoustic backup (simple threshold) was considered and deferred: low
  confidence in battlefield acoustic SNR.
- Proximity is an OPTION pod in the bay's aft ring; PD remains the backup
  initiation in all configurations (dual-path fire set).

## Dual-event S&A (arming logic)

The fire set is safe until ALL THREE conditions hold — no single event,
failure, or stray signal can arm it:

1. **Launch confirmation:** sustained ≥2 g axial acceleration for 150 ms
   (the same launch-detect event that gates fin deployment, MIL-DEV-010).
2. **Canard-deployment confirmation:** the flight computer's
   fins-deployed latch (is_fins_deployed()) must be set — proof of a real
   launch trajectory, not a drop or bench bump.
3. **Flight-time gate:** motor burn time (2.1 s) plus 0.5 s — the round
   is armed only after it has actually flown.

Implementation: firmware state machine (below) drives an electronic S&A
(energetic interrupt rotor in series with the initiator enable chain). The
safe-separation logic satisfies the classic dual-environment S&A intent:
launch acceleration + flight event, both required.

## Firmware (IMPLEMENTATION, compile-verified)

- Rocket `main.cpp` gains a fuze state machine: `FUZE_SAFE` → `FUZE_ARMED`
  on launch-detect ∧ fins-deployed ∧ flight-time gate; `FUZE_FUNCTION` on
  impact detection (deceleration >8 g in FLIGHT) or proximity command.
- Fuze state is telemetered (`FUZE,<state>`) so the launcher and dashboard
  log the arming chain; a fuze that never arms is visible on the ground
  station, not discovered at the target.
- Ignition path (electric initiator, Phase 4) is a SEPARATE circuit from the
  fuze fire set; the ignition servo remains the backup motor path (MIL-DEV-006).

## Not yet established

- S&A chain bench validation (Phase 6.1 gate): drop test, static
  acceleration test, no-fire checks.
- Proximity detection range and clutter rejection (Phase 6.1 gate).
- PD delay verification on representative targets.
