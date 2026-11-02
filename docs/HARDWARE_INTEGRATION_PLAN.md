# Hardware and firmware integration plan

Companion to the [technology map](TECHNOLOGY_INTEGRATION.md) and
[bench configuration workflow](BENCH_CONFIGURATION.md).

## Baseline and current delivery

The repository specifies two ESP32 roles, an MPU6050 on the rocket, and GPS,
compass and barometer on the launcher. Their authoritative assignments remain in
[Wiring](WIRING.md) and [Architecture](ARCHITECTURE.md). Actual installed hardware,
binary identities and calibration records have not been supplied in this task.
No board has been connected, flashed or tested by this work.

The laboratory implements synthetic display validity and alert handling, existing
dependency/fault exhibits, the utility reference, and local comparison of bench
plan identities. These software demonstrations do not implement aircraft flight
management, automatic recovery, propulsion or environmental-control equipment.

## Integration work packages

| Package | Existing hardware/software interface | Proposed integration | Verification required before a hardware claim |
|---|---|---|---|
| Source validity | Existing telemetry channels and capture timestamps | Reuse ground-status age and missing-channel semantics; compare recorded behavior with synthetic exercises | Time-stamped inert captures with known interruptions and independent timing reference |
| Display reversion | Dashboard/status board, source-pinned dependency model | Present remaining information with explicit lost/unknown status; separate independent channels | Review dependency assumptions, then document inert fault observations under a registered procedure |
| Configuration identity | Bench plans, source snapshots, installed binary digest fields | Compare planned and captured identities with the existing offline tools and new browser comparison | Record actual flashed binary digests and specimen ID; matching source alone is insufficient |
| Alerts and event history | Existing status-board advisories and raw capture | Preserve warning reasons and ages; demonstrate recovery on synthetic and recorded input | Check alert ordering and replay determinism, then obtain human-reviewed inert observations |
| Sensor provenance | MPU6050, barometer, compass and GPS records | Bind each reported quantity to units, source kind, calibration record and known limits | Independent instrument provenance; quantity-specific uncertainty and acceptance criteria |
| Built-in-test reporting | Existing boot health flags and software tests | Specify an observational health report independently from control states | New protocol design and compatibility review before firmware implementation; existing boot flags do not detect every later failure |
| Firmware identity reporting | Current capture leaves device firmware revision unreported | Design a versioned, read-only identification record for future firmware work | Review bandwidth/parser compatibility, boot timing and installed-binary identification; no implementation is claimed here |
| Power and environmental monitoring | No accepted voltage/current/temperature instrumentation record | Identify actual supply and sensor requirements from the bench specimen | Component specifications, electrical review and measured supply behavior; aircraft ECS/APU designs are not substitutes |

## Firmware boundary

The repository documents separate review requirements for its command gates,
heartbeat and rocket disarm behavior. This plan does not change those mechanisms.
In particular, a health message must not silently become a readiness signal or
alter heartbeat acceptance. The existing [Ground Status](GROUND_STATUS.md)
discussion identifies the related unresolved changes.

New identification or health messages need a concrete schema, producer timing,
parser behavior, compatibility policy and regression tests before implementation.
Those requirements cannot be recovered from the historical supplement or inferred
from an apparently healthy display.

## Required inputs for physical integration

1. Actual board revisions, wiring revision and installed component identifiers.
2. Installed binary digests for both processors and the corresponding source commit.
3. The intended stationary, inert observation and named responsible operator.
4. Available independent instruments, calibration records and power configuration.
5. A human-registered pre-registration and the corresponding frozen bench plan.

Use `python -m evidence bench init --output build/bench-plan` to generate the
existing configuration template in a fresh directory. Leave unavailable values
unknown. This generates a proposal; it neither operates hardware nor accepts
evidence. The browser identity comparison compares supplied declarations only.

## Aircraft-only technology

Autopilot/autothrottle, flight-management modes, recovery systems, aircraft engine
and fuel equipment, environmental control, mission equipment and operating limits
are not specified for this bench specimen. They remain reference topics in the
technology map, not promised firmware features. The provided supplement refers
to a base manual and omits engineering implementation details, so it cannot serve
as a complete hardware design specification.
