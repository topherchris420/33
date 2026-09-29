"""Summarize telemetry by controller-gain window.

Rules this report follows:
- A window changes only when the gains change, not at every STATUS packet.
- Live T packets and recovered LOG rows are summarized separately; LOG rows
  carry their own recorded gains and are never merged with live samples.
- A malformed or non-finite value is counted and excluded, never read as 0.
- Samples seen before any gains are known are reported as unattributed.
"""

import csv
from dataclasses import dataclass
import math
from pathlib import Path
import statistics


@dataclass
class PidSummary:
    stream: str
    kp: str
    kd: str
    samples: int
    invalid_samples: int
    mean_abs_roll: float
    peak_abs_roll: float
    mean_abs_rate: float
    peak_abs_servo_output: float


def _finite(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _sample(row):
    values = [_finite(row.get(key)) for key in ("roll_deg", "rate_deg_s", "servo_output")]
    return None if any(value is None for value in values) else values


def summarize_pid_csv(path):
    """Return (summaries, unattributed_sample_count)."""
    windows = []
    current = {"T": None, "LOG": None}
    live_gains = None
    unattributed = 0

    def window_for(stream, gains):
        active = current[stream]
        if active is None or (active["kp"], active["kd"]) != gains:
            active = {"stream": stream, "kp": gains[0], "kd": gains[1], "samples": [], "invalid": 0}
            windows.append(active)
            current[stream] = active
        return active

    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            message_type = row.get("message_type")
            if message_type == "STATUS":
                kp, kd = row.get("kp") or "", row.get("kd") or ""
                if kp and kd:
                    live_gains = (kp, kd)
                continue
            if message_type == "T":
                if live_gains is None:
                    unattributed += 1
                    continue
                window = window_for("T", live_gains)
            elif message_type == "LOG":
                kp, kd = row.get("kp") or "", row.get("kd") or ""
                if not (kp and kd):
                    unattributed += 1
                    continue
                window = window_for("LOG", (kp, kd))
            else:
                continue
            sample = _sample(row)
            if sample is None:
                window["invalid"] += 1
            else:
                window["samples"].append(sample)

    summaries = []
    for window in windows:
        samples = window["samples"]
        if not samples:
            summaries.append(PidSummary(window["stream"], window["kp"], window["kd"], 0, window["invalid"],
                                        math.nan, math.nan, math.nan, math.nan))
            continue
        summaries.append(PidSummary(
            stream=window["stream"], kp=window["kp"], kd=window["kd"], samples=len(samples),
            invalid_samples=window["invalid"],
            mean_abs_roll=round(statistics.fmean(abs(s[0]) for s in samples), 3),
            peak_abs_roll=round(max(abs(s[0]) for s in samples), 3),
            mean_abs_rate=round(statistics.fmean(abs(s[1]) for s in samples), 3),
            peak_abs_servo_output=round(max(abs(s[2]) for s in samples), 3),
        ))
    return summaries, unattributed


def _cell(value):
    return "not measured" if isinstance(value, float) and math.isnan(value) else f"{value:.3f}"


def render_pid_markdown(summaries, unattributed=0):
    lines = [
        "# PID Comparison",
        "",
        "Windows change only when gains change. Live (T) and recovered (LOG) samples are separate streams;",
        "invalid samples are counted and excluded, never treated as zero. These are bench statistics for one",
        "session, not a tuning qualification.",
        "",
        "| Stream | Kp | Kd | Samples | Invalid (excluded) | Mean Abs Roll (deg) | Peak Abs Roll (deg) "
        "| Mean Abs Rate (deg/s) | Peak Servo Output (deg) |",
        "|--------|----|----|---------|--------------------|---------------------|---------------------"
        "|-----------------------|-------------------------|",
    ]
    if not summaries:
        lines.append("| No gain windows captured | | | | | | | | |")
    for s in summaries:
        lines.append(f"| {s.stream} | {s.kp} | {s.kd} | {s.samples} | {s.invalid_samples} | {_cell(s.mean_abs_roll)} | "
                     f"{_cell(s.peak_abs_roll)} | {_cell(s.mean_abs_rate)} | {_cell(s.peak_abs_servo_output)} |")
    lines += ["", f"Samples received before any gains were known (unattributed, excluded): {unattributed}"]
    return "\n".join(lines) + "\n"


def write_pid_report(csv_path, output_path):
    summaries, unattributed = summarize_pid_csv(csv_path)
    output = Path(output_path)
    output.write_text(render_pid_markdown(summaries, unattributed), encoding="utf-8")
    return output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Summarize Project 33 PID telemetry windows.")
    parser.add_argument("csv_path", help="Dashboard telemetry CSV")
    parser.add_argument("-o", "--output", default="pid-comparison.md", help="Markdown output path")
    args = parser.parse_args()
    write_pid_report(args.csv_path, args.output)
