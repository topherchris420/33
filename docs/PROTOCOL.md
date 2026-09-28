# Project 33 Protocol Reference

Generated from `protocol/project33_protocol.json`.

## Firmware Constants

| Name | Value |
|------|-------|
| `READY` | `READY` |
| `IGNITED` | `IGNITED` |
| `CMD_ARM` | `ARM` |
| `CMD_IGNITE` | `IGNITE` |
| `CMD_CALIBRATE` | `CALIBRATE` |
| `CMD_DUMPLOG` | `DUMPLOG` |
| `DASHBOARD_LAUNCH` | `launch` |
| `DASHBOARD_CALIBRATE` | `calibrate` |
| `DASHBOARD_DUMPLOG` | `dumplog` |
| `DATA_PREFIX` | `DATA,` |
| `STATUS_PREFIX` | `STATUS:` |
| `ENV_PREFIX` | `ENV,` |
| `LOG_PREFIX` | `LOG` |
| `LOG_START` | `LOG_START` |
| `LOG_END` | `LOG_END` |
| `CMD_ACK_LAUNCH_READY` | `CMD_ACK:launch_ready` |
| `CMD_REJECT_LAUNCH_NOT_READY` | `CMD_REJECT:launch_not_ready` |
| `CMD_REJECT_DASHBOARD_LAUNCH_DISABLED` | `CMD_REJECT:dashboard_launch_disabled` |
| `CMD_REJECT_PID_INVALID` | `CMD_REJECT:pid_invalid` |
| `CMD_REJECT_UNKNOWN_COMMAND` | `CMD_REJECT:unknown_command` |
| `ABORT_PREFIX` | `ABORT:` |
| `CMD_REJECT_ARM_NOT_IDLE` | `CMD_REJECT:arm_not_idle` |
| `CMD_REJECT_IGNITE_NOT_ARMED` | `CMD_REJECT:ignite_not_armed` |
| `CMD_REJECT_IGNITE_FINS_NOT_DEPLOYED` | `CMD_REJECT:ignite_fins_not_deployed` |
| `CMD_REJECT_SENSOR_UNAVAILABLE` | `CMD_REJECT:sensor_unavailable` |

## Messages

| Direction | Format | Purpose |
|-----------|--------|---------|
| Rocket -> Launcher | `READY` | Rocket idle heartbeat |
| Rocket -> Launcher | `IGNITED` | Rocket-side ignition acknowledgement |
| Rocket -> Launcher | `DATA,<ax>,<ay>,<az>,<roll>,<rate>,<output>,<state>,<Kp>,<Kd>,<skew>` | Live rocket telemetry packet |
| Rocket -> Launcher | `LOG,<ms>,<roll>,<rate>,<output>,<state>,<Kp>,<Kd>,<skew>` | Onboard ring-buffer log dump sample |
| Launcher -> Rocket | `ARM` | Arm rocket flight computer |
| Launcher -> Rocket | `IGNITE` | Start rocket ignition state |
| Launcher -> Rocket | `DUMPLOG` | Request rocket onboard ring-buffer dump |
| Dashboard -> Launcher | `dumplog` | Ask launcher to request rocket onboard log dump |
| Launcher -> Dashboard | `CMD_REJECT:launch_not_ready` | Dashboard launch command rejected outside READY |
| Launcher -> Dashboard | `CMD_REJECT:dashboard_launch_disabled` | Dashboard launch command rejected because remote launch is disabled in firmware |
| Launcher -> Dashboard | `CMD_REJECT:pid_invalid` | Dashboard PID command rejected because values were malformed or outside the allowed range |
| Launcher -> Dashboard | `CMD_REJECT:unknown_command` | Dashboard command was not recognized by the launcher |
| Launcher -> Rocket | `CALIBRATE` | Re-zero the gyro offset; the rocket sends no acknowledgement |
| Launcher -> Rocket | `PID,<Kp>,<Kd>` | Set controller gains (each 0-10); invalid values return CMD_REJECT:pid_invalid |
| Rocket -> Launcher | `LOG_START,<count> ... LOG_END` | Bracket an onboard log dump so a partial dump is detectable |
| Rocket -> Launcher -> Dashboard | `CMD_REJECT:arm_not_idle` | ARM refused because the rocket is not IDLE |
| Rocket -> Launcher -> Dashboard | `CMD_REJECT:ignite_not_armed` | IGNITE refused because the rocket is not ARMED |
| Rocket -> Launcher -> Dashboard | `CMD_REJECT:ignite_fins_not_deployed` | IGNITE refused because the deploy flag is not set (see discrepancy D-017) |
| Rocket -> Launcher -> Dashboard | `CMD_REJECT:sensor_unavailable` | ARM or IGNITE refused because the MPU6050 is unavailable |
| Launcher -> Dashboard | `T,<launcher_ms>,<roll>,<rate>,<output>` | Live sample relayed from a DATA line; the time is the launcher's millis() at relay, not the rocket's sample time |
| Launcher -> Dashboard | `STATUS:<state>,<Kp>,<Kd>,<skew>` | Rocket state and active gains, sent after each T packet |
| Launcher -> Dashboard | `ENV,<lat>,<lon>,<alt>,<gps_state>` | Launcher environment; lat/lon are 0.0 placeholders unless gps_state is 2; alt is nan when the barometer is unavailable |
| Launcher -> Dashboard | `ABORT:<reason>` | Launcher abort reason (switch reset, rocket timeout, heartbeat loss, missing IGNITED ack) |
