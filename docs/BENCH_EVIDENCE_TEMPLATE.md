# Bench Evidence Template

Use this template as the human review notes for a session passport (see [BENCH_SESSIONS.md](BENCH_SESSIONS.md)). Most fields are already captured by `session.json`, `declaration.json`, and the passport; this page records the reviewer's judgement.

Do not fabricate telemetry, photos, screenshots, or launch results. If a field is unknown, write `NOT RECORDED` or `NOT MEASURED` and say why. Unknown is not zero.

## Session metadata

- Session ID:
- Passport manifest digest (`manifest.sha256`):
- Pre-registration (ID and status):
- Operator:
- Test objective (one question):
- Inert hardware configuration:
- Hardware revision:
- Firmware commit (both boards):
- Dashboard commit and digest match (from passport):

## Safety setup

- Propulsion/ignition hardware state (no energetic material present?):
- Ignition servo mechanically disconnected?:
- Power supply and current limit:
- Arming switch behavior confirmed before test?:
- Emergency stop/reset method:

## Measurement equipment

- Instrument, model, sample rate or resolution:
- Calibration certificate or date:
- Stated measurement uncertainty:

## Required checks

| Check | Evidence (file, row, or frame) |
|-------|--------------------------------|
| Wiring matched `docs/WIRING.md` | |
| Rocket stayed inert | |
| Dashboard command rejection captured (`CMD_REJECT:...` row) | |
| Arming switch returned launcher to SAFE (`ABORT:` row) | |
| Onboard log dump complete per audit, or intentionally skipped | |
| Passport warnings reviewed and explained | |

## Results

- What happened:
- What did not happen:
- What this session cannot establish:
- Anomalies:
- Result against the pre-registered interpretation rule (or "no rule: descriptive only"):
- Reviewer decision (accept / reject with reason) and name:
