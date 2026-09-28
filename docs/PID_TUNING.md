# PID Tuning Data

When the dashboard closes, it writes `pid-comparison.md` in the session folder. The report groups samples into **gain windows** and states its own limits.

## How windows are formed

- A window changes only when the gains change. (The launcher sends a STATUS packet after every telemetry packet; an earlier version of this report started a new window at each one, producing one-sample windows — D-020.)
- Live `T` samples take the gains from the most recent STATUS packet. The launcher sends each packet's STATUS just after its T, so the first sample after a gain change is attributed to the previous gains: a one-packet lag at each transition.
- Recovered `LOG` rows carry their own recorded gains and are summarized as a separate stream. They are never merged with live samples, which would double-count the same period.
- Samples with malformed or non-finite values are counted in **Invalid (excluded)** and left out. They are never read as zero.
- Samples received before any gains are known are reported as unattributed.

## Metrics

| Metric | Meaning |
|--------|---------|
| Stream | `T` (live, launcher relay clock) or `LOG` (recovered, rocket clock) |
| Samples | Valid samples in the window |
| Invalid (excluded) | Samples dropped because a value was malformed or non-finite |
| Mean / Peak Abs Roll (deg) | Absolute roll angle during the window |
| Mean Abs Rate (deg/s) | Absolute roll rate during the window |
| Peak Servo Output (deg) | Largest absolute servo offset command |

A window with no valid samples reports its metrics as `not measured`. Lower roll error is better only if the servo output stays realistic; a saturating setting is not a better tune because it briefly lowers roll error. These are one session's bench statistics, not a tuning qualification.

## Generate a report manually

```bash
python Firmware/analyze_pid.py Firmware/TestSessions/<session>/telemetry.csv -o Firmware/TestSessions/<session>/pid-comparison.md
```

## Recommended test matrix

| Run | Kp | Kd | Goal |
|-----|----|----|------|
| Baseline | 0.50 | 0.20 | Current firmware default |
| Higher damping | 0.50 | 0.30 | Check whether roll rate settles faster |
| More proportional authority | 0.80 | 0.20 | Check whether roll angle corrects faster |
| Conservative | 0.35 | 0.15 | Check for smoother servo behavior |

Use the same fixture motion for each run and one session per setting; write the comparison rule in a pre-registration before the runs. Different hand motion makes the comparison noise.
