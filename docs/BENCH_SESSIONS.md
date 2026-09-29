# Bench Session Evidence

Each dashboard run owns one session folder under `Firmware/TestSessions/` (git-ignored). A session folder is a **RAW SESSION**: raw capture plus what the dashboard itself knows. It becomes evidence only after it is audited, declared by the operator, and accepted by a named human.

```text
Firmware/TestSessions/bench_YYYYMMDD_HHMMSS/
  telemetry.csv        every received packet, normalized; raw text kept in the raw column
  session.json         capture start/end (UTC), clean close, dashboard and protocol digests, what is NOT RECORDED
  commands.csv         every command the dashboard sent, with UTC time and send outcome
  graph.png            units, clock domain, gaps shaded, state changes, gains; display scaling labeled
  pid-comparison.md    gain windows (T and LOG separate, invalid samples excluded)
  session-summary.md   counts, data-quality summary, next steps
  declaration.json     written later by the operator; never edits the raw files
```

## What the dashboard shows while running

- **Session identity:** session ID, "RAW SESSION (not evidence)", origin undeclared.
- **Data quality:** packets, live T samples, recovered LOG samples, invalid samples, gaps over 500 ms, clock regressions, rejections, and seconds since the last packet (STALE after 2 s).
- **Active configuration:** gains observed in STATUS packets versus gains last commanded (unconfirmed until STATUS matches), and whether calibration was sent (the firmware does not acknowledge it).
- **Unknown values stay unknown:** "—" or "not received" before data arrives, "no fix" instead of 0.000000 coordinates, "not reported" when the launcher has no barometer.

## Session workflow

1. Write or pick a pre-registration for the question (see `evidence/preregistrations.json`). A human registers it before testing.
2. Connect to the launcher access point and start the dashboard. Confirm the session ID and data-quality line.
3. Run one focused inert test. One question per session.
4. Close the dashboard normally so `session.json` records a clean close.
5. Declare what the session was, without editing any raw file:

   ```bash
   python -m evidence session declare Firmware/TestSessions/bench_EXAMPLE \
     --operator "Your Name" --origin bench --purpose "Stationary roll drift, 600 s" \
     --tests gyro_drift --firmware-commit $(git rev-parse HEAD) --hardware-revision "proto-1" \
     --inert-configuration "No energetic material; ignition servo horn removed" \
     --ignition-servo-disconnected true --calibration "CALIBRATE sent at start, rocket on level fixture" \
     --measurement-equipment "none (telemetry only)" --preregistration P-003
   ```

6. Build a verifiable passport and read it:

   ```bash
   python -m evidence session passport Firmware/TestSessions/bench_EXAMPLE --output build/bench_EXAMPLE-passport
   python -m evidence verify build/bench_EXAMPLE-passport
   ```

   The passport reports what was tested, versions, configuration, capture times, raw-file digests, the audit, warnings (missing declaration, unclean close, revision mismatch, calibration not recorded, audit errors), which claims it might inform, and what it cannot establish. It reaches **REVIEW CANDIDATE** only with a bench declaration, operator, purpose, inert configuration, and no audit errors.

7. A named human reviews the passport. If it should enter the record:

   ```bash
   python -m evidence session register build/bench_EXAMPLE-passport       # copies raw bytes into evidence/sessions/
   python -m evidence session accept bench_EXAMPLE --reviewer "Reviewer Name"   # human only
   ```

   Or reject it with `--reject "reason"`; rejected sessions stay in the registry with the reason.

8. Only an accepted session can back a measurement in `evidence/measurements.json`, and only that measurement can move a claim past a physical gate.

## Rules

- Never edit `telemetry.csv`, `session.json`, or `commands.csv`. Corrections go in the declaration's `anomalies` field or a new session.
- A declared `bench` origin is a statement, not proof that hardware was present.
- Clean data quality is necessary, never sufficient.
- Automated tools, including AI assistants, never run `session accept`.

## Audit a capture on its own

```bash
python -m evidence audit Firmware/TestSessions/bench_EXAMPLE/telemetry.csv --origin bench --output build/bench-review
```

Exit code 1 means the audit found data-quality errors; the report is still written so problem captures stay inspectable. See [Evidence Observatory](EVIDENCE_OBSERVATORY.md) for every check.
