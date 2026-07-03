import csv
from dataclasses import dataclass
from pathlib import Path
import statistics


@dataclass
class PidSummary:
    kp: str
    kd: str
    samples: int
    mean_abs_roll: float
    peak_abs_roll: float
    mean_abs_rate: float
    peak_abs_servo_output: float


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def summarize_pid_csv(path):
    groups = []
    active = None

    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            message_type = row.get("message_type")
            if message_type == "STATUS":
                active = {"kp": row.get("kp", ""), "kd": row.get("kd", ""), "samples": []}
                groups.append(active)
            elif message_type in {"T", "LOG"} and active is not None:
                active["samples"].append(
                    {
                        "roll": _safe_float(row.get("roll_deg")),
                        "rate": _safe_float(row.get("rate_deg_s")),
                        "servo": _safe_float(row.get("servo_output")),
                    }
                )

    summaries = []
    for group in groups:
        samples = group["samples"]
        if not samples:
            continue
        abs_roll = [abs(sample["roll"]) for sample in samples]
        abs_rate = [abs(sample["rate"]) for sample in samples]
        abs_servo = [abs(sample["servo"]) for sample in samples]
        summaries.append(
            PidSummary(
                kp=group["kp"],
                kd=group["kd"],
                samples=len(samples),
                mean_abs_roll=round(statistics.fmean(abs_roll), 3),
                peak_abs_roll=round(max(abs_roll), 3),
                mean_abs_rate=round(statistics.fmean(abs_rate), 3),
                peak_abs_servo_output=round(max(abs_servo), 3),
            )
        )
    return summaries


def render_pid_markdown(summaries):
    lines = [
        "# PID Comparison",
        "",
        "| Kp | Kd | Samples | Mean Abs Roll | Peak Abs Roll | Mean Abs Rate | Peak Servo Output |",
        "|----|----|---------|---------------|---------------|---------------|-------------------|",
    ]
    if not summaries:
        lines.append("| No PID windows captured | | | | | | |")
    for summary in summaries:
        lines.append(
            "| {kp} | {kd} | {samples} | {mean_abs_roll:.3f} | {peak_abs_roll:.3f} | "
            "{mean_abs_rate:.3f} | {peak_abs_servo_output:.3f} |".format(**summary.__dict__)
        )
    return "\n".join(lines) + "\n"


def write_pid_report(csv_path, output_path):
    summaries = summarize_pid_csv(csv_path)
    output = Path(output_path)
    output.write_text(render_pid_markdown(summaries), encoding="utf-8")
    return output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Summarize Project 33 PID telemetry windows.")
    parser.add_argument("csv_path", help="Dashboard telemetry CSV")
    parser.add_argument("-o", "--output", default="pid-comparison.md", help="Markdown output path")
    args = parser.parse_args()
    write_pid_report(args.csv_path, args.output)
