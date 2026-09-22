"""Run with python -m evidence; all commands operate on local files only."""

import argparse
import csv
from datetime import datetime, timedelta, timezone
import io
from pathlib import Path
import sys

from .bundle import build_audit, build_review, compare_reviews, verify_bundle
from .common import EvidenceError, canonical_json, new_directory


def demo(output):
    """An intentionally flawed fixture, never a substitute for bench data."""
    buffer = io.StringIO(newline="")
    fields = ["received_at_iso", "source", "message_type", "time_ms",
              "roll_deg", "rate_deg_s", "servo_output", "raw"]
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    samples = [("T", 0, "0"), ("T", 50, "0.2"), ("T", 50, "0.2"),
               ("T", 100, "NaN"), ("T", 900, "0.4"), ("T", 10, "0.1"),
               ("LOG", 0, "0"), ("LOG", 50, "0.2")]
    for index, (kind, time_ms, roll) in enumerate(samples):
        writer.writerow({"received_at_iso": (start + timedelta(milliseconds=50 * index)).isoformat(),
                         "source": "synthetic-fixture", "message_type": kind, "time_ms": time_ms,
                         "roll_deg": roll, "rate_deg_s": "0", "servo_output": "0",
                         "raw": f"{kind},{time_ms},{roll},0,0"})
    with new_directory(output) as stage:
        fixture = stage / "synthetic-telemetry.csv"
        fixture.write_bytes(buffer.getvalue().encode())
        audit = build_audit(fixture, stage / "review", origin="synthetic")
        (stage / "README.txt").write_text(
            "SYNTHETIC SOFTWARE FIXTURE — NO HARDWARE DATA\n"
            "Open review/index.html. Expected: 1 duplicate, 1 invalid numeric sample,\n"
            "1 device-time gap, 1 clock regression, and separate T/LOG streams.\n"
            "The audit quality is intentionally 'error'. No commands are transmitted.\n", encoding="utf-8")
    return audit


def main(argv=None):
    parser = argparse.ArgumentParser(description="Project 33 offline evidence observatory")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="Snapshot the claim catalog into a portable review")
    build.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    build.add_argument("--catalog", default="evidence/catalog.json")
    build.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify", help="Check bundle integrity against its manifest")
    verify.add_argument("directory", type=Path)
    verify.add_argument("--expected-sha256", help="Digest from an independently trusted channel")
    audit = commands.add_parser("audit", help="Audit a recorded CSV without connecting to hardware")
    audit.add_argument("csv", type=Path)
    audit.add_argument("--origin", choices=("unknown", "synthetic", "bench"), default="unknown")
    audit.add_argument("--gap-ms", type=float, default=500)
    audit.add_argument("--output", type=Path, required=True)
    sample = commands.add_parser("demo", help="Create an explicitly synthetic fault-injection example")
    sample.add_argument("--output", type=Path, required=True)
    compare = commands.add_parser("compare", help="Find which claims need review after an evidence change")
    compare.add_argument("before", type=Path)
    compare.add_argument("after", type=Path)
    args = parser.parse_args(argv)
    try:
        code = 0
        if args.command == "build":
            review = build_review(args.root, args.output, args.catalog)
            result = {"output": str(args.output), "claims": len(review["claims"]),
                      "artifacts": len(review["artifacts"]), "physical_artifacts": review["physical_evidence_count"],
                      "unresolved_claims": review["unresolved_claim_count"]}
        elif args.command == "verify":
            result = verify_bundle(args.directory, args.expected_sha256)
        elif args.command == "compare":
            result = compare_reviews(args.before, args.after)
        else:
            result = demo(args.output) if args.command == "demo" else build_audit(
                args.csv, args.output, origin=args.origin, gap_ms=args.gap_ms)
            # A useful report is still written when audit data fails its quality checks.
            if args.command == "audit" and result["quality"] == "error":
                code = 1
        sys.stdout.write(canonical_json(result).decode())
        return code
    except (EvidenceError, OSError, UnicodeError) as exc:
        print(f"evidence: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
