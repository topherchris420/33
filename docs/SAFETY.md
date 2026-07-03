# Safety and Test Boundaries

Project 33 is intended for inert bench validation, simulation, and supervised educational testing. Treat any live propulsion or ignition work as a separate safety-reviewed activity under local law, launch-site rules, and qualified supervision.

## Current Safety Gates

| Gate | Location | Behavior |
|------|----------|----------|
| Physical arming switch | Launcher firmware | Leaving `SAFE` requires the switch to be armed; switch reset aborts the sequence |
| Rocket readiness handshake | Launcher + rocket firmware | Launcher waits for `READY` before entering `READY` state |
| Heartbeat timeout | Launcher firmware | Launcher aborts if rocket telemetry stops in `READY` |
| Dashboard launch gate | Launcher firmware | UDP `launch` is rejected by default; if firmware opt-in is enabled for an inert test, launcher must still be `READY` |
| Rocket ignition gate | Rocket firmware | `IGNITE` is ignored unless rocket is already `ARMED` |
| Abort logging | Launcher + dashboard | Abort reasons are sent to dashboard and captured in CSV logs |

## Bench-Test Rules

- Use inert loads for servo, control, and telemetry tests.
- Keep the ignition servo mechanically disconnected when validating dashboard commands.
- Confirm the arming switch returns the launcher to `SAFE` before connecting any actuator.
- Power servos from a supply sized for stall current, not from a weak USB port.
- Label every connector before moving from breadboard wiring to enclosed wiring.
- Save dashboard CSV logs for every test run and attach representative graphs to the report.

## Preflight Checklist for Inert Demonstrations

1. Verify wiring against [WIRING.md](WIRING.md).
2. Build both PlatformIO projects.
3. Connect to `ROCKET_LAUNCHER`.
4. Start the dashboard and confirm a CSV log filename appears in the top bar.
5. Confirm GPS status, altitude, and heartbeat telemetry update.
6. Flip arming switch and verify launcher reaches `READY`.
7. Confirm switch reset returns the system to `SAFE`.
8. Run calibration with the rocket held still.
9. Confirm digital launch is rejected by default with inert hardware connected; enable it only for a separately reviewed inert test.
10. Save the graph and keep the CSV file with the test notes.
