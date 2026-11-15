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
| `CMD_REJECT_DISARM_NOT_ARMED` | `CMD_REJECT:disarm_not_armed` |
| `CMD_DISARM` | `DISARM` |
| `DISARMED` | `DISARMED` |
| `DASHBOARD_DISARM` | `disarm` |
| `FUZE_PREFIX` | `FUZE,` |
| `FUZE_STATE_SAFE` | `SAFE` |
| `FUZE_STATE_ARMED` | `ARMED` |
| `FUZE_STATE_FUNCTION` | `FUNCTION` |
| `CMD_FUZE_DELAY` | `FUZEDELAY` |

## Messages

| Direction | Format | Purpose |
|-----------|--------|---------|
| Rocket -> Launcher | `READY` | Rocket idle heartbeat |
| Rocket -> Launcher | `IGNITED` | Rocket-side ignition acknowledgement |
| Rocket -> Launcher | `DATA,<ax>,<ay>,<az>,<roll>,<rate>,<output>,<state>,<Kp>,<Kd>,<skew>` | Live rocket telemetry packet |
| Rocket -> Launcher | `LOG,<ms>,<roll>,<rate>,<output>,<state>,<Kp>,<Kd>,<skew>` | Onboard ring-buffer log dump sample |
| Rocket -> Launcher | `FUZE,<state>` | Warhead fuze state (SAFE / ARMED / FUNCTION); dual-event S&A arming chain telemetry |
| Rocket -> Launcher | `NAV,<e_m>,<n_m>,<u_m>,<ve>,<vn>,<vu>,<yaw>,<pitch>,<roll>,<gps_fix>,<mode>,<target_valid>` | Phase 3 navigation and guidance state (ENU from launch point, GPS-aided IMU) |
| Launcher -> Rocket | `FUZEDELAY,<ms>` | Set point-detonating fuze delay (0, 5, 10, or 20 ms); zero accepted in IDLE or ARMED |
| Launcher -> Rocket | `TARGET,<lat>,<lon>,<alt_m>` | Phase 3 target designation by grid coordinates; accepted before flight only |
| Launcher -> Rocket | `MODE,MITL | MODE,AUTO` | Engagement-mode selection: man-in-the-loop (default) or autonomous fire-and-forget on the locked target point; explicit pre-launch operator action |
| Dashboard -> Launcher | `AUTH,<seq>,<operator>,<payload>,<hmac_hex>` | Phase 5 authenticated command wrapper: HMAC-SHA256 over seq,operator,payload with replay-window sequence numbers |
| Dashboard -> Launcher | `OVERRIDE,enabler,<nonce_hex>,<hmacA_hex>,<hmacB_hex>` | Phase 5 wartime two-key OVERRIDE authorization (both operator keys must sign; valid 60 s) |
| Launcher -> Dashboard | `ENC,<iv_hex>,<ct_hex>` | Phase 5 AES-128-CCM authenticated-encrypted telemetry downlink |
| Dashboard -> Launcher -> Rocket | `BIT` | Phase 6 built-in test: rocket replies BIT,<mpu>,<gps>,<fuze>,<fins>,<mode>,<target>,<state> so the pre-fire checklist is machine-checkable |
| Dashboard -> Launcher | `MARK` | Phase 6 MARK-point designation: store the launcher's own surveyed GPS position as the target; echoed to the dashboard as MARK,<lat>,<lon>,<alt> |
| Dashboard -> Launcher -> Rocket | `DISARM` | MIL-DEV-011: safe an ARMED rocket after an abort without a restart; the rocket replies DISARMED, refuses outside ARMED/IDLE, and never disarms a round in FLIGHT |
| Rocket -> Launcher | `DISARMED` | Rocket acknowledgement that it returned to IDLE and is safe |
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
