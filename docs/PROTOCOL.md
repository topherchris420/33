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
| `ABORT_PREFIX` | `ABORT:` |

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
