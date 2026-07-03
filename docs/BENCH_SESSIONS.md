# Bench Session Evidence

Each dashboard run now owns a single session folder under `Firmware/TestSessions/`.

The folder is created automatically when `Firmware/dashboard.py` starts:

```text
Firmware/TestSessions/bench_YYYYMMDD_HHMMSS/
  telemetry.csv
  graph.png
  pid-comparison.md
  session-summary.md
```

These folders are ignored by git because they are raw lab output. For reports, copy the selected CSV, graph, and summary into a dated evidence folder or attach them directly to the project submission.

Use [BENCH_EVIDENCE_TEMPLATE.md](BENCH_EVIDENCE_TEMPLATE.md) when promoting a local bench run into shareable evidence. The template is deliberately explicit about inert hardware, command rejections, and raw-file provenance so the repo does not accidentally imply unverified flight or live-propulsion results.

## Session Workflow

1. Connect to the launcher WiFi AP.
2. Start the dashboard.
3. Confirm the top bar shows the active session ID.
4. Run one focused bench test.
5. Use **Save Graph** during the test if you want an immediate graph export.
6. Close the dashboard at the end of the run.
7. Keep the generated `telemetry.csv`, `graph.png`, `pid-comparison.md`, and `session-summary.md` together.

## What Gets Captured

| Artifact | Purpose |
|----------|---------|
| `telemetry.csv` | Raw dashboard packets normalized into CSV columns |
| `graph.png` | Roll, scaled roll-rate, and servo-output plot |
| `pid-comparison.md` | Grouped PID windows with mean/peak roll and servo-output metrics |
| `session-summary.md` | Lightweight index of captured files and packet count |

## Evidence Naming

Use one session per test question, for example:

- Servo centering at neutral positions
- Gyro calibration drift check
- PID comparison run
- Digital launch rejection check
- Onboard log dump recovery check

Short, focused sessions make the CSV and graph much easier to explain.
