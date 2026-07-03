# PID Tuning Data

The dashboard records active `Kp` and `Kd` values from `STATUS` packets and groups subsequent telemetry samples into PID windows. When the dashboard closes, it writes `pid-comparison.md` inside the active bench session folder.

## Metrics

| Metric | Meaning |
|--------|---------|
| Samples | Number of `T` or onboard `LOG` packets captured after a `STATUS` PID update |
| Mean Abs Roll | Average absolute roll angle during that PID window |
| Peak Abs Roll | Largest absolute roll angle during that PID window |
| Mean Abs Rate | Average absolute roll rate during that PID window |
| Peak Servo Output | Largest absolute servo correction magnitude |

Lower roll error is better only if the servo output remains realistic. A high-output setting that saturates servos is not a better tune just because it briefly lowers roll error.

## Generate a Report Manually

```bash
python Firmware/analyze_pid.py Firmware/TestSessions/<session>/telemetry.csv -o Firmware/TestSessions/<session>/pid-comparison.md
```

## Recommended Test Matrix

| Run | Kp | Kd | Goal |
|-----|----|----|------|
| Baseline | 0.50 | 0.20 | Current firmware default |
| Higher damping | 0.50 | 0.30 | Check whether roll rate settles faster |
| More proportional authority | 0.80 | 0.20 | Check whether roll angle corrects faster |
| Conservative | 0.35 | 0.15 | Check for smoother servo behavior |

Use the same bench motion for each run. Different hand motion or fixture motion will make the comparison noisy.
