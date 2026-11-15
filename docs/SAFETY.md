# Safety and Test Boundaries

Project 33 began as an inert bench-validation repository. Under the program
sponsor's direction of 2026-11-14 it is a guided-munition program: live
propulsion and live fire are planned as the separately gated
[live-fire program](MILITARY/LIVE_FIRE_PROGRAM.md) (militarization deviation
MIL-DEV-002), executed under the sponsor's written order, local law,
launch-site rules, and qualified supervision. All inert bench work remains
governed by this page: nothing here, including a passing CI run, a clean
audit, or an evidence packet, authorizes live propulsion or flight activity
outside that program.

## Current Safety Gates

<!-- evidence:safety-gates -->
| ID | Gate | Where | Behavior | Source checked by tests | Bench evidence |
|---|---|---|---|---|---|
| G-01 | Physical arming switch | Launcher | Leaving SAFE requires the switch; releasing it from any other state aborts to SAFE. | [Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp) | NOT MEASURED |
| G-02 | Rocket readiness handshake | Launcher + rocket | Launcher enters READY only after the rocket reports READY within 8 s; otherwise it aborts. | [Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp) | NOT MEASURED |
| G-03 | Heartbeat timeout | Launcher | READY aborts if rocket telemetry stops for 2 s. | [Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp) | NOT MEASURED |
| G-04 | Dashboard launch enabled as the wartime remote-fire path with authentication | Launcher | UDP launch is enabled (MIL-DEV-004) but must be authenticated (HMAC + sequence number, AUTH wrapper) or use the classic inert-bench path, and a plain unauthenticated remote fire without a recent physical hold or OVERRIDE is rejected. | [Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp) | NOT MEASURED |
| G-05 | Dashboard launch requires READY plus fire discipline | Launcher | UDP launch is accepted only in READY and only with a recent 1 s physical fire-button hold or a valid two-key OVERRIDE; otherwise rejected with launch_needs_fire_hold_or_override. | [Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp) | NOT MEASURED |
| G-06 | Dashboard source check | Launcher | Commands are ignored unless they come from the address that sent the shared-token HELLO. | [Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp) | NOT MEASURED |
| G-07 | Physical launch hold | Launcher | The launch button must be held for 1 s with the switch still armed. | [Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp) | NOT MEASURED |
| G-08 | Rocket ARM requires IDLE and a healthy IMU | Rocket | ARM is refused (and now reported) otherwise. | [Firmware/Rocket/src/main.cpp](../Firmware/Rocket/src/main.cpp) | NOT MEASURED |
| G-09 | Rocket IGNITE requires ARMED and a healthy IMU | Rocket | IGNITE is refused (and now reported) otherwise. | [Firmware/Rocket/src/main.cpp](../Firmware/Rocket/src/main.cpp) | NOT MEASURED |
| G-10 | Rocket IGNITE requires the deploy flag | Rocket | IGNITE is refused unless the deploy timer has fired; see discrepancy D-017 for the ordering question. | [Firmware/Rocket/src/main.cpp](../Firmware/Rocket/src/main.cpp) | NOT MEASURED |
| G-11 | Deploy trigger requires a non-IDLE state and sustained launch acceleration | Rocket | Handling an unarmed rocket cannot fire the deploy output, and a single bump cannot either: the deploy output fires only after the x-axis acceleration holds above the threshold continuously for the sustain time (MIL-DEV-010). | [Firmware/Rocket/src/main.cpp](../Firmware/Rocket/src/main.cpp) | NOT MEASURED |
| G-12 | Forced ignition is bench-build only | Rocket | IGNITE_FORCE exists only when BENCH_MODE is defined; the committed build does not define it. | [Firmware/Rocket/platformio.ini](../Firmware/Rocket/platformio.ini)<br>[Firmware/Rocket/src/main.cpp](../Firmware/Rocket/src/main.cpp) | NOT MEASURED |
| G-13 | Refusals and aborts are logged | Rocket + launcher + dashboard | Rocket refusals travel over UART as CMD_REJECT lines; the launcher forwards them and its own ABORT reasons to the dashboard CSV. | [Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp)<br>[Firmware/Rocket/src/main.cpp](../Firmware/Rocket/src/main.cpp) | NOT MEASURED |
| G-14 | Bounded controller gains | Launcher + rocket | PID values outside 0-10 or malformed are rejected on both boards. | [Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp)<br>[Firmware/Rocket/src/main.cpp](../Firmware/Rocket/src/main.cpp) | NOT MEASURED |
| G-15 | Weapons commands are HMAC-authenticated with replay protection | Launcher | AUTH-wrapped commands carry an HMAC-SHA256 over sequence number, operator, and payload; monotonic sequence numbers with a sliding replay window block captured-command replay (Phase 5). | [Firmware/Launcher/src/crypto.h](../Firmware/Launcher/src/crypto.h) | NOT MEASURED |
| G-16 | Wartime OVERRIDE requires two keys | Launcher | The OVERRIDE enabler must be signed by BOTH operator keys (two digital arms) and is valid for 60 s; a dashboard launch without a physical fire hold is rejected otherwise. | [Firmware/Launcher/src/crypto.h](../Firmware/Launcher/src/crypto.h)<br>[Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp) | NOT MEASURED |
| G-17 | Telemetry downlink is AES-128-CCM encrypted | Launcher | Downlink packets are authenticated-encrypted (AES-128-CCM, mbedtls); a crypto failure degrades to plain telemetry, never to silence (Phase 5). | [Firmware/Launcher/src/crypto.h](../Firmware/Launcher/src/crypto.h)<br>[Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp) | NOT MEASURED |
| G-18 | Fuze S&A requires all three arming events | Rocket | The fuze arms only on launch acceleration AND canard-deployment confirmation AND the flight-time gate; it functions only on a real impact deceleration (Phase 2). | [Firmware/Rocket/src/main.cpp](../Firmware/Rocket/src/main.cpp) | NOT MEASURED |
| G-19 | AUTONOMOUS engagement is an explicit pre-launch selection | Rocket | MODE,AUTO (fire-and-forget) is accepted only in IDLE/ARMED as an explicit operator action; MITL is the default (Phase 3). | [Firmware/Rocket/src/main.cpp](../Firmware/Rocket/src/main.cpp) | NOT MEASURED |
| G-20 | DISARM safes an armed rocket without a restart | Rocket + launcher + dashboard | DISARM returns an ARMED rocket to IDLE (launch detect cleared, ignition servo off, fins latch reset) and replies DISARMED; refused outside ARMED/IDLE and never in FLIGHT, so a burning round is not remotely safed (MIL-DEV-011, D-025). | [Firmware/Launcher/src/main.cpp](../Firmware/Launcher/src/main.cpp)<br>[Firmware/Rocket/src/main.cpp](../Firmware/Rocket/src/main.cpp) | NOT MEASURED |

Generated from `evidence/safety_gates.json`. `tests/test_firmware_safety.py` fails if any gate's source text changes. Source inspection shows the gate is implemented; it does not show the hardware behaves that way.
<!-- /evidence:safety-gates -->

Deterministic interlocks live in firmware and stay there. The rocket's IGNITE path additionally requires the deploy flag, which is set only by a sustained above-2 g launch-acceleration event (150 ms qualification plus a 50 ms hardware delay; see G-11 and militarization deviation MIL-DEV-010) while not IDLE; on the bench this acts as an extra interlock, and its intended ordering is an open design question (D-017). Do not remove or reorder any gate without a separate safety review.

## Automated tools and AI

- No AI feature, script, or CI job may send launch, ignition, or arming commands, change a gate, or enable `ENABLE_DASHBOARD_LAUNCH`.
- The wartime autonomous engagement mode (`MODE,AUTO`) is a firmware mode selected by an operator behind an explicit arm toggle (MIL-DEV-003); it is not an automated tool.
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

> **WARNING:** Step 6 arms the rocket. Step 7 returns only the launcher to `SAFE`: the rocket stays `ARMED` with its deploy trigger live until it is **DISARMed** (dashboard DISARM button; the rocket replies `DISARMED` and returns to `IDLE` — MIL-DEV-011, D-025) or restarted. Treat it as armed through the remaining steps, and confirm `IDLE` on the dashboard before arming again.

1. Verify wiring against [WIRING.md](WIRING.md).
2. Build both PlatformIO projects from a recorded commit.
3. Connect to the launcher access point.
4. Start the dashboard and confirm the session ID, "RAW SESSION", and the data-quality line appear.
5. Confirm GPS status, altitude (or "not reported"), and heartbeat telemetry update.
6. Flip the arming switch and verify the launcher reaches `READY`.
7. Confirm switch reset returns the launcher to `SAFE` and an `ABORT:` row is logged.
8. Run calibration with the rocket held still; the dashboard records that it was sent (the firmware does not acknowledge it).
9. Confirm digital launch is rejected by default and `CMD_REJECT:dashboard_launch_disabled` is logged; enable it only for a separately reviewed inert test.
10. Close the dashboard so `session.json` records a clean close, then run `python -m evidence session declare` and `session passport`.

Afterwards, `python Firmware/preflight_audit.py SESSION_FOLDER` compares the recording with these steps. See [Bench Sessions](BENCH_SESSIONS.md#compare-a-session-with-the-preflight-checklist).
