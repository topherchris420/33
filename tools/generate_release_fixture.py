"""Create a ten-second synthetic dashboard-parser fixture, without hardware I/O.

Invented timestamps and values exercise software only. No deployment timing,
spring rate, long-duration drift, or laser-tracking measurement is represented.
"""

import argparse
import csv
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "Firmware"))

from evidence.common import canonical_json, new_directory
from evidence.session import build_passport, declare
from session_artifacts import TestSessionArtifacts
from telemetry_log import FIELDNAMES


def generate(output):
    start = datetime(2000, 1, 1, tzinfo=timezone.utc)  # Invented fixture time.
    with new_directory(output) as stage:
        session = TestSessionArtifacts(root=stage, session_id="synthetic-dashboard", now=start.isoformat())
        session.metadata.update(evidence_stage="SYNTHETIC SOFTWARE FIXTURE - NO HARDWARE",
                                origin="synthetic", generator="tools/generate_release_fixture.py")
        session.metadata["dashboard"]["capture_executed"] = False
        with session.telemetry_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=[*FIELDNAMES, "origin"], lineterminator="\n")
            writer.writeheader()
            for time_ms in range(0, 10001, 50):
                seconds = time_ms / 1000
                roll = 0.2 * math.sin(seconds)
                rate = 0.2 * math.cos(seconds)
                writer.writerow({"received_at_iso": (start + timedelta(milliseconds=time_ms)).isoformat(),
                                 "source": "synthetic-fixture", "origin": "synthetic", "message_type": "T",
                                 "time_ms": time_ms, "roll_deg": f"{roll:.6f}", "rate_deg_s": f"{rate:.6f}",
                                 "servo_output": 0, "raw": f"T,{time_ms},{roll:.6f},{rate:.6f},0"})
        session.close(201, now=(start + timedelta(seconds=10)).isoformat())
        declare(session.session_dir, {"operator": "software fixture generator (not a human operator)",
                                     "origin": "synthetic", "purpose": "Dashboard CSV/parser compatibility only",
                                     "inert_configuration": "No hardware or actuator connected; invented data",
                                     "tests": ["synthetic-parser-fixture"]})
        document = build_passport(session.session_dir, stage / "passport", root=ROOT)
        (stage / "fixture.json").write_bytes(canonical_json({
            "origin": "synthetic", "hardware_capture": False, "human_signoff": None,
            "duration_s": 10, "samples": 201, "stage": document["stage"],
            "does_not_validate": ["P-001: instrument timing, not available in T packets",
                                  "P-002: torque-angle characterization, not available in T packets",
                                  "P-003: 600 s stationary gyro experiment, not this invented 10 s trace",
                                  "P-006: no registered experiment or laser-tracking protocol exists"],
        }))
        with (ROOT / "materials/bom.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        (stage / "procurement-example.json").write_bytes(canonical_json({
            "schema": "project33.procurement/1", "currency": "USD", "record_kind": "synthetic_example",
            "origin": "synthetic", "mock_planning_total_usd": "81.00", "actual_acquisition_cost_usd": None,
            "note": "Software example only. No purchase, payment, vendor invoice, or receipt exists.",
            "lines": [{"item": row["item"], "quantity": row["qty"],
                       "estimated_unit_price_usd": row["unit_price_usd"], "origin": "synthetic"} for row in rows],
        }))
        (stage / "README.txt").write_text(
            "SYNTHETIC SOFTWARE FIXTURE - NO HARDWARE DATA OR PURCHASES\n"
            "201 invented T samples at 50 ms spacing over 10 s. Times are invented.\n"
            "Open passport/index.html. A clean audit establishes parser/data quality only.\n"
            "The example procurement file preserves the $81 estimate; it is not a transaction ledger.\n"
            "No session was registered, no measurements were added, and no review was signed.\n",
            encoding="utf-8")
    return document


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    document = generate(args.output)
    print(json.dumps({"output": str(args.output), "origin": "synthetic", "stage": document["stage"]}))


if __name__ == "__main__":
    main()
