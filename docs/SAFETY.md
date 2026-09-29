# Safety and Test Boundaries

Project 33 is intended for inert bench validation, simulation, and supervised educational testing. Treat any live propulsion or ignition work as a separate safety-reviewed activity under local law, launch-site rules, and qualified supervision. Nothing in this repository, including a passing CI run, a clean audit, or an evidence packet, authorizes live propulsion or flight activity.

## Current Safety Gates

<!-- evidence:safety-gates -->
| ID | Gate | Where | Behavior | Source checked by tests | Bench evidence |
|---|---|---|---|---|---|
| G-01 | Physical arming switch | Launcher | Leaving SAFE requires the switch; releasing it from any other state aborts to SAFE. | [Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp) | NOT MEASURED |
| G-02 | Rocket readiness handshake | Launcher + rocket | Launcher enters READY only after the rocket reports READY within 8 s; otherwise it aborts. | [Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp) | NOT MEASURED |
| G-03 | Heartbeat timeout | Launcher | READY aborts if rocket telemetry stops for 2 s. | [Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp) | NOT MEASURED |
| G-04 | Dashboard launch disabled by default | Launcher | UDP launch is rejected with CMD_REJECT:dashboard_launch_disabled unless firmware is rebuilt with the opt-in. | [Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp) | NOT MEASURED |
| G-05 | Dashboard launch requires READY | Launcher | Even with the opt-in, UDP launch is accepted only in READY. | [Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp) | NOT MEASURED |
| G-06 | Dashboard source check | Launcher | Commands are ignored unless they come from the address that sent the shared-token HELLO. | [Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp) | NOT MEASURED |
| G-07 | Physical launch hold | Launcher | The launch button must be held for 1 s with the switch still armed. | [Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp) | NOT MEASURED |
| G-08 | Rocket ARM requires IDLE and a healthy IMU | Rocket | ARM is refused (and now reported) otherwise. | [Firmware/Rocket/src/main.cpp](../Firmware/Rocket/src/main.cpp) | NOT MEASURED |
| G-09 | Rocket IGNITE requires ARMED and a healthy IMU | Rocket | IGNITE is refused (and now reported) otherwise. | [Firmware/Rocket/src/main.cpp](../Firmware/Rocket/src/main.cpp) | NOT MEASURED |
| G-10 | Rocket IGNITE requires the deploy flag | Rocket | IGNITE is refused unless the deploy timer has fired; see discrepancy D-017 for the ordering question. | [Firmware/Rocket/src/main.cpp](../Firmware/Rocket/src/main.cpp) | NOT MEASURED |
| G-11 | Deploy trigger requires a non-IDLE state | Rocket | Handling an unarmed rocket cannot fire the deploy output. | [Firmware/Rocket/src/main.cpp](../Firmware/Rocket/src/main.cpp) | NOT MEASURED |
| G-12 | Forced ignition is bench-build only | Rocket | IGNITE_FORCE exists only when BENCH_MODE is defined; the committed build does not define it. | [Firmware/Rocket/platformio.ini](../Firmware/Rocket/platformio.ini)<br>[Firmware/Rocket/src/main.cpp](../Firmware/Rocket/src/main.cpp) | NOT MEASURED |
| G-13 | Refusals and aborts are logged | Rocket + launcher + dashboard | Rocket refusals travel over UART as CMD_REJECT lines; the launcher forwards them and its own ABORT reasons to the dashboard CSV. | [Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp)<br>[Firmware/Rocket/src/main.cpp](../Firmware/Rocket/src/main.cpp) | NOT MEASURED |
| G-14 | Bounded controller gains | Launcher + rocket | PID values outside 0-10 or malformed are rejected on both boards. | [Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp)<br>[Firmware/Rocket/src/main.cpp](../Firmware/Rocket/src/main.cpp) | NOT MEASURED |

Generated from `evidence/safety_gates.json`. `tests/test_firmware_safety.py` fails if any gate's source text changes. Source inspection shows the gate is implemented; it does not show the hardware behaves that way.
<!-- /evidence:safety-gates -->

Deterministic interlocks live in firmware and stay there. The rocket's IGNITE path additionally requires the deploy flag, which is set only by a >15 g event while not IDLE; on the bench this acts as an extra interlock, and its intended ordering is an open design question (D-017). Do not remove or reorder any gate without a separate safety review.

## Automated tools and AI

- No AI feature, script, or CI job may send launch, ignition, or arming commands, change a gate, or enable `ENABLE_DASHBOARD_LAUNCH`.
- Automated tools may interpret the evidence record and draft inert-test proposals. A human decides whether a test is run, and only a named human accepts its evidence.
- Model confidence, test results, and clean telemetry never stand in for readiness.

## Bench-Test Rules

- Use inert loads for servo, control, and telemetry tests. No energetic material is present during any repository test.
- Keep the ignition servo mechanically disconnected when validating dashboard commands.
- Confirm the arming switch returns the launcher to `SAFE` before connecting any actuator.
- Power servos from a supply sized for stall current, not from a weak USB port.
- Label every connector before moving from breadboard wiring to enclosed wiring.
- Keep every dashboard session folder (CSV, `session.json`, `commands.csv`); declare it and build a passport before citing it.
- Stored-energy parts (torsion springs) are restrained during characterization; wear eye protection.

## Preflight Checklist for Inert Demonstrations

1. Verify wiring against [WIRING.md](WIRING.md).
2. Build both PlatformIO projects from a recorded commit.
3. Connect to the launcher access point.
4. Start the dashboard and confirm the session ID, "RAW SESSION", and the data-quality line appear.
5. Confirm GPS status, altitude (or "not reported"), and heartbeat telemetry update.
6. Flip the arming switch and verify the launcher reaches `READY`.
7. Confirm switch reset returns the system to `SAFE` and an `ABORT:` row is logged.
8. Run calibration with the rocket held still; the dashboard records that it was sent (the firmware does not acknowledge it).
9. Confirm digital launch is rejected by default and `CMD_REJECT:dashboard_launch_disabled` is logged; enable it only for a separately reviewed inert test.
10. Close the dashboard so `session.json` records a clean close, then run `python -m evidence session declare` and `session passport`.
