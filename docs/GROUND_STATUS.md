# Ground Status

The status board answers the questions an operator has during an inert bench session: what is actually reporting, what could be wrong, what can I still do, and is what I commanded what the rocket is using?

It reads packets and draws conclusions. It **cannot send anything**, has no command path, and is **not evidence**. Its model is pinned to firmware source and exercised against synthetic packets; no fault has been injected on hardware, so its behavior on real faults is **NOT MEASURED**.

## Use it

```bash
python Firmware/status_panel.py --demo             # invented packets, no hardware
python Firmware/dashboard.py                       # then press STATUS BOARD
python Firmware/ground_status.py SESSION_FOLDER    # replay a recorded session as text
python Firmware/preflight_audit.py SESSION_FOLDER  # compare a recorded session with the preflight checklist
python tools/generate_degraded_modes.py --check    # is the failure analysis current?
```

Replay needs only the standard library and never changes the session folder. It refuses `--output` paths inside that folder, because the passport hashes every file there.

**Reset Data** on the dashboard clears the plot, not the board. An abort warning must not disappear because a plot was cleared.

## What it shows

| Area | What it does | Why it is built this way |
|---|---|---|
| Rocket state | Shows the last state with its age, and marks it `STALE` after 2 s. | A stale `ARMED` that looks current is the worst thing this screen could show. |
| Launcher state | Says `NOT REPORTED`, with an inference labeled as one. | The protocol has no launcher state message. |
| Attitude | Roll, rate, and servo output. It cannot be hidden, and goes invalid after 0.5 s instead of holding the last value. | Pitch and yaw are not in the protocol, and gyro drift is not measured. The panel says both. |
| Roll reference | `GEOMETRY OK`, `WEAK GEOMETRY`, `GYRO ONLY`, or `NOT OBSERVED`, read from the `[FUSION]` pitch. | Firmware corrects roll from two accelerometer axes, and near vertical little gravity falls on them (D-026). This describes pose geometry and is not a health check. |
| Calibration | `NOT SENT`, `SENT`, `CHANGE SEEN`, `NO CHANGE SEEN`, or `UNCONFIRMED`, with the current skew. | Firmware sends no reply, and skew changes only when it calibrates, so a change is the only sign available. No change proves nothing: skew is reported to 0.01 deg. |
| Units | `SEEN`, `SUSPECT`, or `NOT SEEN`. | `SEEN` means packets needing that unit are arriving. It is deliberately not "healthy". |
| Isolation | The failures consistent with what is missing, and the next test that would narrow them. | Model-based diagnosis: it reports every minimal explanation rather than guessing one. |
| Capabilities | `SUPPORTED`, `AT RISK`, `LOST`, or `NOT OBSERVED`. | Separates what still works from what merely cannot be seen. |
| Gains | `ACTIVE`, `PRESELECT`, `SENT`, `CONFIRMED`, `REJECTED`, `NO MATCH`, or `UNCONFIRMED`. | Firmware acknowledges nothing, so only a later `STATUS` can confirm a change. No telemetry is `UNCONFIRMED`, not `NO MATCH`. |
| Advisories | `WARNING`, `CAUTION`, `ADVISORY`, most severe first, each with its reason. | The full list is in [Degraded Modes](DEGRADED_MODES.md). |

## Isolating a fault

Each packet stream depends on a set of units. A stream that is arriving clears those units; a stream that is missing means at least one of its remaining units failed.

The useful case is the launcher reporting while rocket telemetry has stopped. That leaves the UART, the rocket, or an IMU that failed at boot. Those look identical from packets alone, because the rocket's failed-IMU branch returns before it sends anything. But it handles commands first, so **DUMP LOG** separates them:

- A reply clears the UART and rocket, leaving the IMU.
- Silence leaves the UART or the rocket, and no dashboard test separates those.

The board suggests this. The operator presses the existing button; the board never sends it. `dumplog` reads the onboard ring buffer and moves no actuator.

## Detecting a restart

A rocket restart returns gains to their defaults, zeroes roll, and loses the onboard log, so it matters even when nothing else looks wrong. The board raises `C-ROCKET-RESTART` on any of three signs:

- **State moved backwards.** Firmware has no such transition.
- **Skew changed while `IDLE` with no calibration to explain it.** Firmware sets skew only while calibrating: at boot, on `ARM`, and on `CALIBRATE`. This is what catches a restart in `IDLE`, the usual bench state. It misses a restart whose new skew rounds to the old value.
- **The rocket clock fell behind ground time between two complete log dumps.** `LOG` rows carry the rocket clock, which starts over at a restart. The shortfall equals how long the rocket had been up when it restarted, so pressing **DUMP LOG** at the start and end of a session checks everything between them, unless the rocket restarted within 5 s of booting. Partial dumps are ignored because lost rows would look like a late clock.

## Limits

- **Interpretation only.** A clean board does not show hardware works, and an advisory does not show it failed. Only an accepted inert session can establish behavior.
- **Steady state.** A fault takes up to the channel timeout to appear, and brief gaps can raise short advisories while the launcher is in a blocking wait.
- **Sensors after boot.** `mpuHealthy` and `bmpHealthy` are set once in `setup()`. A sensor failing later keeps reporting whatever the driver returns. `A-IMU-FROZEN` is a heuristic for the IMU, and its threshold is not based on measured noise. Nothing covers the barometer.
- **The rest** of what is not modeled is listed in [Degraded Modes](DEGRADED_MODES.md#not-modeled).

## What this does not do

The board does not touch flight behavior. It adds no steering, guidance, navigation, or targeting; the rocket's only control loop remains roll stabilization. It changes no firmware, protocol message, or safety gate, and nothing here moves a claim across a validation gate. The same holds for the preflight audit. See [Safety](SAFETY.md).

## Proposed firmware changes, not implemented

The model exposes three gaps. Each changes command or heartbeat behavior, so each needs a human decision and a separate safety review:

1. **A disarm path (D-025).** A launcher abort leaves an armed rocket armed with its deploy trigger live, and the launcher then cannot re-arm it. Only a restart returns the rocket to `IDLE`.
2. **A heartbeat that does not depend on the IMU.** The launcher already accepts `ALIVE`, and the rocket never sends it. Sending it would separate an IMU fault from a UART or rocket fault passively, but it would also change what counts as a heartbeat for gate G-03.
3. **A launcher state message.** This would replace the board's inference with a report, and let the preflight check for `READY` be recorded rather than read off an LED.

## Findings recorded, not fixed

Building the roll reference exposed two limits in the roll estimator. Both come from reading the source and from a software port of its equations with invented noise; neither has been seen on hardware, and no firmware changed:

- **D-026.** Nothing stops the correction from using near-zero axes when the rocket is near vertical. In the port the effect was small until within a few degrees of vertical.
- **D-027.** While stationary, the correction holds roll near its reference, so roll cannot show gyro drift. The P-003 proposal now also integrates `rate_deg_s`, which reads the gyro directly.

## Keeping it honest

`tests/test_ground_status_model.py` pins every dependency in `protocol/ground_status_model.json` to exact firmware text, in the same way `evidence/safety_gates.json` pins the gates. If firmware changes, the test fails and the model has to be re-read. The same test fails if the status modules gain network access or the panel gains a control, and if a disarm path appears without the board and D-025 being updated.

`Firmware/tests/test_ground_status.py` runs all 256 combinations of failed units through the real packet path, with and without the probe, and checks that a failed unit is never marked `SEEN` and that the true failure always contains one of the reported explanations. This tests the software against its own model. It is not a fault-injection result.
