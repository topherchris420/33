# Onboard Logging

The rocket firmware now keeps a RAM ring buffer of the most recent telemetry samples. This is not a replacement for the dashboard CSV log; it is a recovery tool if WiFi/RF telemetry becomes a blocker during bench or field testing.

## How It Works

- The rocket records each 50 ms telemetry sample into a 240-sample ring buffer.
- The launcher forwards dashboard `dumplog` commands to the rocket as `DUMPLOG`.
- The rocket responds with `LOG_START,<count>`, one `LOG,...` row per retained sample, then `LOG_END`.
- The launcher forwards those rows to the dashboard.
- The dashboard CSV logger stores `LOG` rows with the same roll/rate/output/PID columns as live telemetry, and keeps `LOG_START`/`LOG_END` as raw rows.
- `python -m evidence audit` compares the announced count with the rows received and reports a dump that is incomplete, overfull, or never terminated. A partial dump is reported, never assumed complete.
- `LOG` rows carry the rocket's own clock and gains, so they are the only rocket-time record; live `T` rows carry launcher relay time.

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
- Recovered rows describe the same period as live rows; they never add live coverage and are summarized separately.
- Add SD-card or flash-backed logging only if RAM dumps do not answer the test question.
