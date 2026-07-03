# Bench Evidence Template

Use this template when turning a local `Firmware/TestSessions/bench_*` run into project evidence.

Do not fabricate telemetry, photos, screenshots, or launch results. If a field is unknown, write `not measured` and explain why.

## Session Metadata

- Session ID:
- Date/time:
- Operator:
- Test objective:
- Inert hardware configuration:
- Firmware commit:
- Dashboard command source:

## Safety Setup

- Propulsion/ignition hardware state:
- Ignition servo mechanically disconnected?:
- Power supply and current limit:
- Arming switch behavior confirmed before test?:
- Emergency stop/reset method:

## Evidence Files

- Raw telemetry CSV:
- Saved graph:
- PID comparison:
- Session summary:
- Photos/video stills:

## Required Checks

| Check | Evidence |
|-------|----------|
| Wiring matched `docs/WIRING.md` | |
| Rocket stayed inert | |
| Dashboard command rejection captured | |
| Arming switch returned launcher to SAFE | |
| Onboard log dump captured or intentionally skipped | |

## Results

- What happened:
- What did not happen:
- Anomalies:
- Follow-up actions:
