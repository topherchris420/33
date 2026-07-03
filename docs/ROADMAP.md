# Validation Roadmap

This roadmap keeps Project 33 focused on evidence quality rather than adding features without proof. Each stage should produce artifacts that a reviewer can inspect without needing access to the original bench setup.

## Stage 1: Repository Hardening

Status: mostly complete.

- Keep firmware builds and Python checks running in CI.
- Keep protocol constants generated from `protocol/project33_protocol.json`.
- Keep wiring docs synchronized with firmware constants.
- Keep dashboard launch disabled by default.
- Keep README, project page, safety docs, and status docs aligned.

Exit gate: CI is green and public docs clearly separate demonstrated behavior from planned validation.

## Stage 2: Inert Bench Evidence

Status: next priority.

- Capture servo-centering evidence with photos or video stills.
- Capture gyro calibration and drift behavior with dashboard screenshots.
- Capture launcher arming, READY, abort, LED/buzzer, and command-rejection behavior.
- Capture one PID tuning run with `telemetry.csv`, `graph.png`, `pid-comparison.md`, and `session-summary.md`.
- Capture one onboard log dump recovery run.

Exit gate: at least one complete bench package uses [BENCH_EVIDENCE_TEMPLATE.md](BENCH_EVIDENCE_TEMPLATE.md) and points to raw files.

## Stage 3: Mechanical Review Package

Status: planned.

- Export Fusion renders for folded, deployed, launcher, and nozzle views.
- Add annotated dimensions for fin chord/span, hinge geometry, servo placement, launcher controls, and nozzle section.
- Record prototype material and print settings.
- Note known differences between CAD and assembled hardware.

Exit gate: CAD documentation is sufficient for a reviewer to understand the assembly without opening Fusion 360.

## Stage 4: Control-System Refinement

Status: planned.

- Add drift characterization for the MPU6050 integration path.
- Compare PID windows across repeated inert bench runs.
- Decide whether a complementary filter or reference correction is required before any field testing.
- Document servo current draw and brownout margin.

Exit gate: control-loop limitations are quantified with repeatable bench data.

## Stage 5: Field-Test Readiness Review

Status: not started, not claimed.

This stage is intentionally separate from the repository's current bench-validation scope. Any live propulsion or flight activity requires qualified supervision, local rule compliance, range procedures, and a safety review outside this repo's current evidence claim.

Exit gate: only a separately approved field-test plan can move the project beyond inert validation.
