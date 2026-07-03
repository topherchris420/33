# Project Status and Readiness Matrix

Project 33 is a bench-validation prototype. The repository is organized to make each claim reviewable through source files, generated references, CI output, simulation assets, CAD archives, and bench evidence.

## Status Snapshot

| Dimension | Current state | Evidence |
|-----------|---------------|----------|
| Lifecycle stage | Bench-validation prototype | README, this status file |
| Flight claim | No flight-test claim | [SAFETY.md](SAFETY.md), README limitations |
| Simulation | OpenRocket model and visual exports are committed | `Simulation/` |
| Mechanical design | Fusion 360 archives are committed; annotated render exports are pending | `CAD Files/`, [CAD_ASSEMBLIES.md](CAD_ASSEMBLIES.md) |
| Rocket firmware | PlatformIO project with arming, stabilization, telemetry, and onboard log dump support | `Firmware/Rocket/`, CI |
| Launcher firmware | PlatformIO project with AP, UART bridge, physical arming, sensor telemetry, and launch gates | `Firmware/Launcher/`, CI |
| Dashboard | Tkinter telemetry console with CSV logging, graph export, PID comparison, and log dump request | `Firmware/dashboard.py`, `Firmware/tests/` |
| Bench evidence | Capture workflow exists; representative physical bench package is not yet committed | [BENCH_SESSIONS.md](BENCH_SESSIONS.md), [BENCH_EVIDENCE_TEMPLATE.md](BENCH_EVIDENCE_TEMPLATE.md) |
| Safety posture | Inert bench validation only; dashboard launch rejected by default | [SAFETY.md](SAFETY.md), `Firmware/Launcher/src/main.cpp` |

## Readiness Matrix

| Capability | Readiness | What would close the next gate |
|------------|-----------|--------------------------------|
| Repository reproducibility | Ready for review | CI badge green, protocol check clean, tests passing |
| Protocol and wiring traceability | Ready for review | Generated protocol artifacts and wiring tests remain synchronized |
| Simulation package | Ready for review | Add notes tying stability graph assumptions to test conditions |
| CAD package | Partially ready | Add exported Fusion renders with dimensions and material notes |
| Rocket firmware bench behavior | Needs physical evidence | Commit or attach inert bench CSV, graph, and operator notes |
| Launcher interlock behavior | Needs physical evidence | Capture switch, LED/buzzer, READY, abort, and command-rejection run |
| Dashboard evidence capture | Ready for review | Include one example sanitized bench session package |
| Flight readiness | Not claimed | Requires a separate safety review, test range process, and qualified supervision |

## Evidence Standard

Use this rule for every public claim: if the repository says it happened, it should point to an artifact. Acceptable artifacts include source code, generated docs, CI logs, OpenRocket exports, Fusion renders, bench CSV logs, graph exports, photos, videos, or explicit `not measured` entries in the evidence template.

Do not fabricate or imply flight, propulsion, or live-ignition results. If a test was not run, state that plainly and list the next evidence needed.

## Current Gaps

- No committed physical bench-session package yet.
- No flight-test data, and no flight-readiness claim.
- CAD archives need annotated render exports for easier review.
- Servo authority under aerodynamic load is not measured.
- Gyro drift and UDP delivery limits remain known technical risks.

## Submission Package Checklist

- README and project page link to the same status, safety, and evidence docs.
- CI checks pass for protocol generation, Python tests, and firmware builds.
- Bench evidence package uses [BENCH_EVIDENCE_TEMPLATE.md](BENCH_EVIDENCE_TEMPLATE.md).
- Representative screenshots or photos are named, dated, and tied to a commit.
- Limitations are listed next to the claim they qualify.
- Safety gates are documented before any command path or actuator behavior is described.
