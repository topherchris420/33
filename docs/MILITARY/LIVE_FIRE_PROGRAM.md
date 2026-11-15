# Phased Live-Fire Test Program

**Phase 6 · Authority:** program sponsor's written order of 2026-11-14
(MIL-DEV-002 supersedes the repository's no-live-fire rule). Each phase has
pass/fail gates; **no phase begins until the previous phase's gates pass.**
Every result is logged in [LIVE_FIRE_LOG.md](LIVE_FIRE_LOG.md) and labeled
MEASURED or FIELDLED. Nothing below has run yet on hardware.

> **Software-in-the-loop pre-validation (2026-11-15):** the logic halves of
> items 1.1–1.4 are implemented and passing in `Firmware/sa_harness.py` /
> `Firmware/tests/test_sa_harness.py` (20 cases, fidelity-enforced against
> the firmware source); items 1.5–1.6 pass at the software level in
> `Firmware/crypto_harness.py` / `Firmware/tests/test_crypto_harness.py`
> (15 cases, including the cross-language AES-CCM round-trip). The bench
> pre-registrations P-006–P-011 are on record. **This is not the hardware
> gate:** every item below stays PENDING until it runs on physical hardware.

## Phase 6.1 — Fuze S&A chain, bench validation (inert)

| # | Test | Gate | Status |
|---|---|---|---|
| 1.1 | S&A no-fire checks: drop test (1.5 m, 6 faces), static 8 g for 5 s, thermal storage −40/+60 °C soak | Fuze does not arm or function; no initiator continuity change | PENDING (logic halves passing in SIL; P-006) |
| 1.2 | Arm-in-order check: launch accel alone, canard-deploy alone, time-gate alone | Each single event leaves fuze SAFE | PENDING (logic halves passing in SIL; P-007) |
| 1.3 | Arm-in-order check: all three events in sequence | Fuze arms; `FUZE,ARMED` telemetered | PENDING (logic halves passing in SIL; P-007) |
| 1.4 | Impact function: 8 g+ deceleration input with fuze armed | `FUZE,FUNCTION`; fire output after selected delay | PENDING (logic halves passing in SIL; P-008) |
| 1.5 | Command-link security: replayed AUTH packets, forged HMAC, single-key OVERRIDE | All rejected; two-key OVERRIDE accepted | PENDING (software level passing; P-009) |
| 1.6 | Telemetry crypto round-trip launcher→dashboard | ENC packets decrypt; crypto-failure falls back to plain | PENDING (software level passing; P-010) |

**Gate 6.1:** all six pass on hardware. Exit criteria include a documented key change
from bench defaults.

## Phase 6.2 — Captive carry / guidance-in-the-loop (inert)

| # | Test | Gate | Status |
|---|---|---|---|
| 2.1 | Rocket GPS fix quality on the move (vehicle, 5 Hz) | Position σ ≤ 5 m; velocity σ ≤ 0.5 m/s | PENDING |
| 2.2 | Attitude estimate vs. reference (rate table or swing) | Pitch/yaw error ≤ 3° over 30 s; roll ≤ 2° | PENDING |
| 2.3 | PN law hardware-in-loop: target point driven on a cart; canard commands recorded | Commands point toward target; no sign inversions; authority not saturated >80% | PENDING |
| 2.4 | MIL-33 static fire (instrumented, tethered) | Thrust within ±10% of the .eng curve; burn time ±10%; case intact | PENDING (P-011) |
| 2.5 | Deployment mechanism function on the militarized linkage (20 cycles) | Locks at 90° every cycle; no under-deployment below 89° | PENDING |

**Gate 6.2:** all five pass.

## Phase 6.3 — Inert-guided flight shots (G64W motor, no energetics in the bay)

| # | Test | Gate | Status |
|---|---|---|---|
| 3.1 | 3 unguided reference shots | Ballistic dispersion within 2× of the CEP model's ballistic arm | PENDING |
| 3.2 | 5 guided shots at 300 m point targets | **Measured CEP ≤ 2× the modeled 14 m** (i.e. ≤ 28 m) | PENDING |
| 3.3 | Telemetry link + post-strike ring-buffer dumps | Every shot recovers a complete NAV/LOG record | PENDING |
| 3.4 | Fuze S&A flight behavior | Arms after burn time; no premature function; `FUZE,ARMED` received | PENDING |

**Gate 6.3:** all four pass. Failures feed the model, not the narrative.

## Phase 6.4 — Full live warhead shots (MIL-33 motor, live bay)

| # | Test | Gate | Status |
|---|---|---|---|
| 4.1 | 2 GP HE-frag shots vs. personnel target boards at 1–3 km | Fragment spread and casualty radius within ±50% of the 6.8 m MODELED estimate | PENDING |
| 4.2 | 2 HEAT shots vs. RHA plates at 2 CD standoff | Penetration inside the 62–93 mm band | PENDING |
| 4.3 | 2 EFP shots vs. light-vehicle targets at 10–50 m standoff | Penetration inside the 28–44 mm band; functioning at standoff | PENDING |
| 4.4 | 2 two-key OVERRIDE live launches under supervision | Correct authorization chain observed; no unauthorized-path firings | PENDING |

**Gate 6.4 (program exit):** all four pass → the round is FIELDLED at the
tested envelope. Any failure returns the affected subsystem to its model with
a deviation-register entry.

## Standing rules for all live phases

- Two-person rule at the launcher; positive weapons control per the
  [operator card](OPERATOR_CARD.md) at all times.
- Live-fire shots are commanded MITL by default; AUTO requires the explicit
  pre-launch mode selection AND the two-key OVERRIDE.
- Every shot gets a session record (dashboard CSV, `session.json`) filed in
  [LIVE_FIRE_LOG.md](LIVE_FIRE_LOG.md) — MODELED numbers are updated to
  MEASURED/FIELDLED only through this log.
- Energetic material handling, storage, and transport per local law and
  range regulations; the bench-test rules in
  [docs/SAFETY.md](../SAFETY.md) still govern inert work.
