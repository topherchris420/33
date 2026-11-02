# Technology integration map

This inventory distinguishes existing laboratory functionality from candidate
additions. It is not a claim that the aircraft's equipment has been implemented.
The historical source is a supplement and defers some systems to a separate base
manual. The study limitations are in [Utility Bench Manual](UTILITY_BENCH_MANUAL.md).

| Technology family | Existing Project 33 counterpart | Integration status and gap |
|---|---|---|
| Multipurpose displays | [Instrumentation laboratory](../lab/instruments.html), generic cockpit and selectable display explanations | Existing conceptual exhibit; not an aircraft display implementation |
| Head-up information and decluttering | Generic canvas preview and cockpit displays | Existing synthetic display and declutter controls |
| Attitude awareness | Ground-status roll/rate display and generic synthetic attitude exhibit | Existing; project telemetry does not supply pitch/yaw as operational channels |
| Air-data interpretation | Generic source validity pipeline; launcher barometric altitude | Existing educational examples; no project air-data computer or measured airspeed implementation |
| Inertial reference | IMU-origin telemetry, validity and roll-reference interpretation | Existing limited project implementation; not a navigation-grade inertial system |
| Map and navigation presentation | Generic navigation display in the cockpit exhibit | Conceptual only; no route-management or navigation solution is established |
| Data entry and command confirmation | Active/preselect/sent/confirmed gain states in the status board | Existing interpretation; no browser command path |
| Configuration and stored-data identity | Bench plan, installed binary digests, source manifests | Existing offline configuration identity workflow |
| Built-in test and equipment status | Source-pinned dependency model, preflight audit, and dedicated USB monitor firmware | Sensor/register checks and raw diagnostic reporting implemented; physical qualification remains unmeasured |
| Failure isolation and redundancy | Generic power/processor graph and project degraded-mode matrix | Existing interactive dependency analysis; several failures remain observationally ambiguous |
| Alerts and priority | Ground-status warnings/cautions/advisories | Existing project-specific advisories, not aircraft fault messages |
| Automatic flight/speed modes | No corresponding laboratory implementation | Aircraft behavior cannot be inferred from labels; no compatible bench specification supplied |
| Automatic recovery | [Model-rocket pressure and recovery review](MODEL_ROCKET_REVIEW.md) | Offline rise/peak/descent estimation and simulated release markers implemented; physical recovery actuation and performance remain unimplemented |
| Environmental control and auxiliary power | No corresponding rocket subsystem | Aircraft-specific hardware; possible educational explanation, not a compatible component specification |
| Fire, engine and fuel systems | No corresponding validated bench-laboratory subsystem | Aircraft procedures cannot serve as Project 33 procedures |
| Sensor updates and calibration | Calibration interpretation and independent-instrument provenance | Existing project workflow; a sent request is not a completed calibration |
| Operating envelopes and performance | Claim requirements, unresolved model results and release blockers | Aircraft limits are not project limits; no aircraft performance transfer |
| Mission and stores equipment | No counterpart in the bench laboratory | No implementation proposed in this research reference |

## Selected integration scope

The selected scope is interactive laboratory simulation plus a separate
[hardware and firmware integration plan](HARDWARE_INTEGRATION_PLAN.md). Simulation
features consume synthetic data; physical integration requires the actual
specimen and its specifications. Existing laboratory functions remain read-only
and separate from physical evidence.

## Functional additions in this change

The [standalone USB instrumentation](USB_BENCH_MONITOR.md) adds actual firmware
and sensor-driver integration. Separate observer images report the existing
MPU6050, BMP180, compass and GPS sources over USB, with boot/reset/memory and ELF
identity records. The capture/replay tool validates frames and the laboratory
loads its diagnostic reports. This implementation is distinct from the generic
synthetic display exercises below.

The [model-rocket addition](MODEL_ROCKET_REVIEW.md) supplies a separate ESP32/BMP180
pressure-logger image, validated capture import, local relative-height/rate
estimation and a scrubbable recovery-review timeline. It distinguishes ground
sensors from declared rocket sources and breaks model history across invalid
samples or capture gaps. Release markers are simulated report events, not
actuator outputs or demonstrations of physical recovery.

- The instrumentation preview, 3D cockpit and flat fallback consume the same
  timestamped synthetic observations. A missing source expires into stale data;
  stale readings hold the last valid value while other sources continue updating.
- Invalid samples, elapsed times, source names and declutter inputs are rejected.
  Returned snapshots cannot mutate the simulation's stored values.
- Alerts retain their raised time while active, clear on recovery, sort by
  severity and recency, and count both declutter and capacity overflow.
- The configuration panel compares two local `project33.bench_plan/1` declarations.
  It distinguishes changed, added, missing, matched and unknown identities.
  A missing installed binary digest remains unknown even when source files match.

These are original educational software features. The validity windows belong
to the existing generic exhibit and are not Project 33 hardware acceptance limits.
Disagreement is an injected scenario, not a newly implemented navigation estimator.

The implemented manual adaptation already supplies system descriptions, review
checklists, source-linked troubleshooting and revision control. The table above
does not relabel those reference features as implementations of aircraft systems.
