# Testing and Evidence Plan

The project should be graded on evidence: buildability, simulation, bench telemetry, and clear documentation of limitations.

## Automated Checks

Run from the repository root:

```bash
python -m pytest tests Firmware/tests -q
```

What this covers:

- `docs/WIRING.md` stays synchronized with important firmware constants.
- Firmware command-gate expectations stay visible in review.
- The telemetry CSV logger preserves dashboard packets in a machine-readable format.

## Firmware Builds

Run with PlatformIO:

```bash
pio run -d Firmware/Rocket
pio run -d Firmware/Launcher
```

The GitHub Actions workflow runs both builds on every push and pull request.

## Simulation Evidence Already in Repo

| Artifact | Purpose |
|----------|---------|
| `Simulation/Folding Stabilized Rocket.ork` | OpenRocket model |
| `Simulation/OpenRocket_3D_View.png` | Visual configuration reference |
| `Simulation/Side View.png` | Geometry overview |
| `Simulation/Stability Graph.png` | Stability trend evidence |

## Bench Evidence to Capture

| Test | Evidence to save |
|------|------------------|
| Servo centering | Photo/video plus center angles used |
| Gyro calibration | Dashboard screenshot before/after calibration |
| PID tuning | CSV log plus saved graph showing roll/rate/output |
| Launcher arming | Video showing switch, LED/buzzer, `READY`, and abort behavior |
| Dashboard command rejection | CSV row or screenshot showing `CMD_REJECT:launch_not_ready` |
| GPS/barometer status | CSV row showing `ENV` messages and GPS state |

## Dashboard Logs

`Firmware/dashboard.py` automatically creates CSV logs in `Firmware/TelemetryLogs/` when the dashboard starts. The CSV includes packet time, message type, roll, rate, output, PID values, skew, GPS, altitude, and raw messages. The folder is ignored by git so test runs do not pollute commits.

## Known Validation Gaps

- No flight-test data is committed yet.
- Stability control is roll-axis focused.
- Gyro integration can drift over time.
- UDP is convenient for the bench but does not provide delivery guarantees.
- Servo authority under real aerodynamic load still needs measurement.
