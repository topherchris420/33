# Terminal Guidance Design — MODELED / IMPLEMENTATION

**Phase 3 · Firmware: IMPLEMENTATION (compile-verified, not flown).
Performance: MODELED.** Nothing in this document has flown.

## Architecture

```
Operator target designation (grid coords) ──► Launcher ──UART──► Rocket
                                                          │
Rocket GPS (UART1, 5 Hz) ─┐                               ▼
MPU6050 gyro/accel ───────┼──► GPS-aided IMU ──► PN law ──► canard mixer
                          │    (ENU state)     (N = 3)      (4 servos ±12°)
```

- **Guidance law:** proportional navigation, N = 3, `a = N·(ω × V)`, command
  limited to the canard authority (9.6 m/s² ≈ 1 g derived at 200 m/s, with
  margin for servo lag and hysteresis), plus a 75% gravity bias on the
  vertical channel and a 2 mrad/s LOS-rate deadband so the loop does not
  chase sensor noise.
- **Roll channel:** the Phase 1 roll damper is retained; the guidance law
  rides a roll-stabilized airframe. The mixer rotates the ENU command into
  the rolled body frame and splits it into the pitch pair (up/down canards)
  and yaw pair (left/right).
- **Navigation:** rocket-side GPS (UART1, receive-only, GPIO 13) is the ENU
  origin at launch and the position/ground-velocity source; the MPU6050
  provides attitude (gyro-integrated pitch/yaw/roll with a gravity-reference
  correction while on the rail). This is a GPS-aided IMU, not an INS: the
  CEP model treats GPS latency and gyro drift as budgeted error terms.
- **Target designation:** `TARGET,<lat>,<lon>,<alt_m>` uploaded pre-launch from
  the launcher (relayed verbatim; the launcher does not interpret
  coordinates). The target ENU is locked against the first post-launch GPS
  fix. A laser/radio beacon receiver is an option the bus allows; the
  baseline is grid coordinates.

## Engagement modes

| Mode | Behavior | Selection |
|---|---|---|
| **MITL** (default) | Operator designates the target pre-launch, verifies, and commands the launch. Guidance steers to the designated point. | Default; no action needed |
| **AUTO** | Fire-and-forget on the locked target point. | `MODE,AUTO` — accepted **only before flight** (IDLE/ARMED), an explicit operator arm-mode toggle (MIL-DEV-003) |

Both modes fly the same in-flight law; the mode governs the pre-launch
procedure and positive control, not the guidance.

## CEP estimates (MODELED, `Simulation/cep_model.py`)

Monte Carlo (400 trials/point) including GPS error and latency, gyro drift,
attitude bias, wind (0–8 m/s), servo lag, motor thrust scatter (±4%),
launcher aim error (σ 0.3°), and 10 m target-designation CEP. The launcher
flies a per-range fire-control (range-card) elevation:

| Motor | Range | Guided CEP | Ballistic CEP | Improvement |
|---|---|---|---|---|
| G64W (inert test) | 300 m | **14 m** | 13 m | 0.95× (at the motor's max range, little to correct) |
| Phase 4 preliminary (800 Ns) | 1 km | **50 m** | 57 m | 1.14× |
| Phase 4 preliminary (800 Ns) | 2 km | **19 m** | 54 m | 2.8× |
| Phase 4 preliminary (800 Ns) | 3 km | **81 m** | 650 m | 8.0× (3 km is at the ballistic edge; guidance stretches the envelope) |

**Key caveat:** the Phase 4 motor is a preliminary assumption in this model
(800 Ns, 2.0 s, 0.75 kg wet). The 3 km point sits at the edge of its ballistic
reach (aim-solution error 647 m) — the Phase 4 motor sizing must add impulse
to put 3 km comfortably inside the envelope. The G64W numbers describe the
Phase 6.3 inert-guidance flight tests.

## What the model caught

The Python CEP re-implementation of the PN law caught a sign error in the
firmware's first cut (`V × ω` instead of `ω × V` — the rocket would have
steered *away* from the target). Both implementations now read `a = N·(ω × V)`
and the cross-check is why that is not a flight-test discovery.

## Not yet established

- Captive-carry / guidance-in-the-loop bench test (Phase 6.2 gate).
- Canard authority (CANARD_ACCEL_PER_DEG = 0.8) is derived, not measured.
- Servo polarity per axis must be bench-verified before any flight (WIRING.md).
