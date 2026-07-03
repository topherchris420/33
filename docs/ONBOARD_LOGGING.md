# Onboard Logging

The rocket firmware now keeps a RAM ring buffer of the most recent telemetry samples. This is not a replacement for the dashboard CSV log; it is a recovery tool if WiFi/RF telemetry becomes a blocker during bench or field testing.

## How It Works

- The rocket records each 50 ms telemetry sample into a 240-sample ring buffer.
- The launcher forwards dashboard `dumplog` commands to the rocket as `DUMPLOG`.
- The rocket responds with `LOG_START,<count>`, one `LOG,...` row per retained sample, then `LOG_END`.
- The launcher forwards those rows to the dashboard.
- The dashboard CSV logger stores `LOG` rows with the same roll/rate/output/PID columns as live telemetry.

At 20 Hz, the current buffer preserves about 12 seconds of recent samples.

## When to Use It

Use onboard log dump after:

- Dashboard disconnect/reconnect during a run
- Suspected UDP packet loss
- A test where the live graph looked incomplete
- A bench run where the rocket kept operating but dashboard telemetry stalled

## Limits

- The ring buffer is RAM-only and clears on reset or power loss.
- It does not solve UART wiring failures between rocket and launcher.
- It is intentionally small to avoid SD-card hardware and flash wear.
- Add SD-card or flash-backed logging only if RAM dumps do not answer the test question.
