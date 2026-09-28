# Validation Roadmap

Project 33 moves forward by producing evidence a reviewer can inspect without the original bench, not by adding features. Claims move only through explicit gates:

**ANALYTICAL MODEL → SOFTWARE REPRODUCTION → SYNTHETIC TEST → INERT BENCH SETUP → INERT PHYSICAL MEASUREMENT → REPEATED MEASUREMENT → INDEPENDENT REVIEW**

The evidence record enforces the gates: INERT BENCH SETUP needs a pre-registration registered by a named human, and the physical gates need measurements from sessions a named human has accepted. No AI model, CI run, or repository setting can move a claim across them. Any field activity is a separate, safety-reviewed process outside this repository.

## Stage 1: Repository Hardening and Evidence Discipline

Status: mostly complete.

- CI builds both firmware projects, runs the tests, reproduces every model output, and checks record consistency.
- Protocol constants are generated from `protocol/project33_protocol.json`; wiring docs and the safety-gate registry are tested against firmware source.
- Dashboard launch stays disabled by default; rocket refusals are logged over UART.
- Claims, requirements, predictions, discrepancies, pre-registrations, sessions, reviews, and the failure archive are machine-checked records with generated passports.

Exit gate: CI green, `python -m evidence check` clean, and public docs generated from the record rather than restating it.

## Stage 2: Inert Bench Evidence

Status: next priority. Nothing below has been measured.

- A human reviews and registers P-001 (deploy-output timing with an external instrument) before any timing capture.
- A human reviews P-003 (stationary roll drift, exploratory) and captures it with periodic `dumplog` so rocket-clock LOG rows exist.
- Capture launcher arming, READY, abort, LED/buzzer, and the CMD_REJECT rows (dashboard launch disabled, ignite not armed, ignite fins not deployed).
- Capture one onboard log-dump recovery and confirm the audit reports the dump complete.
- For each session: `session declare`, `session passport`, human review, `session register`, `session accept --reviewer NAME`. Only then cite it.

Exit gate: at least one human-accepted inert session registered in `evidence/sessions.json`, with its passport and raw bytes, cited by a claim.

## Stage 3: Model Integrity Review

Status: open; runs in parallel with Stage 2. These are review decisions, not measurements.

- C1: confirm the intended linkage topology and dimensions (D-002); model the locking moment or declare it a physical question (D-004).
- C5: adjudicate the fin-term formulation (D-006), the motor (D-007), and the omitted inputs (D-008).
- C4/C6/C7/C8: define one shared, reviewed design point read by every model (D-010); rebuild the reliability simulation so its failure modes can occur (D-013).
- C6 and C8: a human decides whether to change the design, the requirement, or the claim (D-011, D-015), and records why.
- Each revised model registers new predictions and supersedes the old ones; prior outputs go to the failure archive.

Exit gate: every open discrepancy marked `contradicts_claim` has a recorded human decision.

## Stage 4: Mechanical Review Package

Status: planned.

- Export Fusion renders for folded, deployed, launcher, and nozzle views with key dimensions and material notes.
- Regenerate the four-bar CAD only after Stage 3 resolves D-002; keep D-005 open until then.
- Record as-built part masses (P-002-style protocol) and CAD-versus-as-built differences.

Exit gate: a reviewer can understand the assembly without opening Fusion 360, and every CAD-versus-model mismatch is in the discrepancy register.

## Stage 5: Control-System Refinement

Status: planned.

- Characterize MPU6050 drift (P-003) and compare PID windows across repeated inert runs with identical fixture motion.
- Propose a protocol revision adding rocket sample time, a sequence number, and a boot identifier to live telemetry (D-018), bench-verified before adoption.
- Document servo current draw and brownout margin with a measured supply.

Exit gate: control-loop limitations quantified by repeated, accepted bench sessions.

## Stage 6: Field-Test Readiness Review

Status: not started, not claimed.

Outside this repository's validation boundary. Any live propulsion or flight activity requires qualified supervision, local rule compliance, range procedures, and a separate safety review. Only a separately approved field-test plan can move the project beyond inert validation.
