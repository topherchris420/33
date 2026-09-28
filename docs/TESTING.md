# Testing and Evidence Plan

Project 33 is judged on evidence: what builds, what reproduces, what was measured, and what is honestly marked as not measured. Every check below names its scope. "Build passed" is not "design works".

## What CI can and cannot establish

| CI establishes | CI cannot establish |
|---|---|
| Firmware compiles for both boards | That any firmware behavior happens on hardware |
| Python tests pass (a JUnit record is attached to the CI review packet) | That a mechanism deploys or locks |
| Every committed model output regenerates from source and matches by value | That a model's formulation or inputs are valid |
| Requirements are evaluated from committed values, labeled with their evidence class | That a requirement is met physically |
| Records are internally consistent; generated docs and figures are current | Timing, stiffness, servo authority, drift, current draw |
| Interlocks are present in source, pinned by tests | That interlocks behave correctly on hardware, or operational safety |

## Automated checks

Run from the repository root:

```bash
python tools/generate_protocol.py --check      # protocol JSON, firmware header, and PROTOCOL.md agree
python tools/check_markdown_links.py           # local Markdown targets exist
python tools/review_figures.py --check         # review figures match the tested geometry code
python -m evidence check                        # record consistency, review freshness, stale generated docs
python -m pytest tests Firmware/tests -q        # regression and adversarial tests
python -m evidence reproduce                    # regenerate model outputs and compare values (needs requirements-evidence.txt)
```

What the tests cover:

- **Evidence record:** schema validation, forbidden classes, promotion refusal (status, gate, support), synthetic-data relabeling, physical evidence without an accepted session, duplicate measurements counted as repeats, pre-registrations edited after a result, prediction drift, missing values, incomplete denominators, stale reviews (source, statement, assumption, discrepancy changes), stale generated passports, packet tampering, source replaced after a packet, hash-seed independence, archive immutability, execution records (skipped is not passed), reproduction records going stale (`tests/test_evidence_adversarial.py`, `tests/test_evidence_review.py`).
- **Telemetry and sessions:** non-finite and malformed samples, duplicates and conflicts, clock regressions and rollover, missing timezones, stream separation and clock domains, partial log dumps, gain windows, command responses, session passports for missing metadata, unclean close, version mismatch, synthetic declarations, and human-only acceptance.
- **Models:** C1 geometry and null handling (unassemblable poses report no value), margin arithmetic, run-record denominators, laminate isotropy, and regression against committed outputs. No CI test asserts that a design meets its requirement; requirement outcomes are evaluated by the record.
- **Firmware source:** wiring docs match constants, gates match the safety registry, refusal logging comes after the gates it reports, missing altitude is `nan`, and no rocket-side text can trigger the launcher's `READY`/`IGNITED` substring matches.
- **Dashboard modules:** PID windows follow gain changes, T and LOG stay separate, invalid samples are excluded, live quality counters, session metadata, command log, and gap-breaking plots.

The documentation checker uses only the Python standard library and runs offline.
It supports inline links/images and single-line reference definitions, relative
paths, root paths (including the site's `/33/` prefix), URL-encoded filenames,
angle-bracket paths with spaces, optional quoted titles, and one level of nested
parentheses in destinations. Code fences, inline code, indented code, and generated
directories (`.git`, `.venv`, `venv`, `node_modules`, `TestSessions`, `__pycache__`,
`.pio`, and `build`) are skipped. It checks target existence, not heading anchors, external
URLs, HTML links, Liquid templates, or unresolved reference labels. A missing
target prints `file:line: missing local target: path` and exits with status 1.
Use `--root PATH` to check a different documentation tree.

## Firmware builds

```bash
pio run -d Firmware/Rocket
pio run -d Firmware/Launcher
```

GitHub Actions runs these on every push and pull request. A successful build is compile-level evidence only.

## Bench evidence to capture

Every capture goes through the session workflow in [BENCH_SESSIONS.md](BENCH_SESSIONS.md): declare, passport, human acceptance, then citation. Until then it is a raw session, not evidence.

| Test | Evidence to save | Related record |
|------|------------------|----------------|
| Deploy-output timing | External logic-analyzer capture of GPIO 33 against a trigger reference | P-001, R-C2-JITTER |
| Gyro drift, stationary | Session with periodic `dumplog`, rocket-clock LOG rows | P-003 |
| Torsion spring rate | Torque-angle table with instrument and calibration | P-002, R-C6-SPRING-RATE |
| Servo centering | Photo/video plus center angles used | — |
| PID comparison | Session CSV, `pid-comparison.md`, `graph.png`, identical fixture motion across runs | — |
| Launcher arming and aborts | Session showing READY, `ABORT:` rows, LED/buzzer video | Safety gates G-01 to G-03 |
| Command rejection | `CMD_REJECT:dashboard_launch_disabled`, `CMD_REJECT:ignite_not_armed` rows | G-04, G-09, G-13 |
| Onboard log dump | `LOG_START`, `LOG,...`, `LOG_END` rows; audit reports the dump complete | — |
| Dry CG | Balance-point measurement of the inert airframe | PRED-C5-DRY-CG |
| CAD assembly renders | Exports listed in [CAD_ASSEMBLIES.md](CAD_ASSEMBLIES.md) | D-005 |

## Known validation gaps

- No accepted physical measurement of any quantity.
- Live telemetry has launcher relay timestamps and no sequence number or boot identifier.
- Stabilization is roll-axis only; gyro integration drift is uncharacterized.
- UDP does not guarantee delivery; the dashboard records "sent", not "received".
- Servo authority under aerodynamic load is unmeasured and outside inert bench scope.
