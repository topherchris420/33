"""Run with python -m evidence; every command operates on local files only.

No command opens a network connection, talks to hardware, or sends a command.
"""

import argparse
import csv
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import sys

from . import docs as D
from . import evaluate as E
from . import session as S
from . import vocabulary as V
from .bundle import build_audit, build_review, compare_reviews, drift, load_assessment, verify_bundle
from .common import EvidenceError, canonical_json, new_directory
from .workflow import reproduce, snapshot

ROOT = Path(__file__).resolve().parents[1]


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
               ("RAW", None, "LOG_START,3"), ("LOG", 0, "0"), ("LOG", 50, "0.2")]
    for index, (kind, time_ms, roll) in enumerate(samples):
        received = (start + timedelta(milliseconds=50 * index)).isoformat()
        if kind == "RAW":
            writer.writerow({"received_at_iso": received, "source": "synthetic-fixture", "message_type": "RAW",
                             "time_ms": "", "roll_deg": "", "rate_deg_s": "", "servo_output": "", "raw": roll})
            continue
        writer.writerow({"received_at_iso": received, "source": "synthetic-fixture", "message_type": kind,
                         "time_ms": time_ms, "roll_deg": roll, "rate_deg_s": "0", "servo_output": "0",
                         "raw": f"{kind},{time_ms},{roll},0,0"})
    with new_directory(output) as stage:
        fixture = stage / "synthetic-telemetry.csv"
        fixture.write_bytes(buffer.getvalue().encode())
        audit = build_audit(fixture, stage / "review", origin="synthetic")
        (stage / "README.txt").write_text(
            "SYNTHETIC SOFTWARE FIXTURE — NO HARDWARE DATA\n"
            "Open review/index.html. Expected: 1 duplicate, 1 invalid numeric sample, 1 device-time gap,\n"
            "1 clock regression, an interval unlike the 50 ms firmware period, and a log dump that\n"
            "announced 3 rows, delivered 2, and never terminated (a partial capture).\n"
            "The audit quality is intentionally 'error'. No commands are transmitted.\n", encoding="utf-8")
    return audit


def status_text(assessment):
    lines = ["Project 33 evidence status", "", D.counts_sentence(assessment).replace("**", ""), ""]
    for c in assessment["claims"]:
        lines.append(f"{c['id']}  {c['status_label']:<31} {c['support_label']:<22} review: {c['freshness_label']}")
        lines.append(f"    {c['title']}")
        for r in c["requirement_results"]:
            cls = f" ({V.EVIDENCE_CLASSES[r['evidence_class']]['label'].lower()})" if r["evidence_class"] else ""
            lines.append(f"    - {r['id']:<26} {r['label']}{cls}")
    lines += ["", "Scopes:"] + [f"  - {s['text']}" for s in assessment["scopes"]]
    if assessment["violations"]:
        lines += ["", "Record consistency findings:"] + [f"  - [{v['code']}] {v['message']}" for v in assessment["violations"]]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Project 33 offline evidence observatory")
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root (default: this checkout)")
    parser.add_argument("--catalog", default="evidence/catalog.json")
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="Snapshot the record into a portable review packet")
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--execution-record", type=Path, help="pytest JUnit XML to attach as a run record")
    build.add_argument("--reproduction-record", type=Path, help="JSON from 'reproduce --record' to attach")
    verify = commands.add_parser("verify", help="Check bundle integrity against its manifest")
    verify.add_argument("directory", type=Path)
    verify.add_argument("--expected-sha256", help="Digest from an independently trusted channel")
    compare = commands.add_parser("compare", help="What changed between two review packets, and which claims it affects")
    compare.add_argument("before", type=Path)
    compare.add_argument("after", type=Path)
    drift_cmd = commands.add_parser("drift", help="Which files changed since a review packet was built")
    drift_cmd.add_argument("bundle", type=Path)
    commands.add_parser("check", help="Strict record check: drift, stale reviews, consistency, stale generated docs")
    commands.add_parser("status", help="Print claim status, requirement results, and scopes")
    impact = commands.add_parser("impact", help="Which claims, requirements, and checks depend on these paths")
    impact.add_argument("paths", nargs="+")
    query = commands.add_parser("query", help="Answer a grounded evidence question from the record")
    query.add_argument("question", nargs="?", help="Question ID; omit to list them")
    snap = commands.add_parser("snapshot", help="Record the current state of claims as their last review")
    snap.add_argument("--claims", nargs="+", required=True)
    snap.add_argument("--note", required=True)
    snap.add_argument("--reviewer", help="Your name. Only a human records a human review; tooling must omit this.")
    snap.add_argument("--independent", action="store_true", help="Reviewer is independent of the work (human only)")
    repro = commands.add_parser("reproduce", help="Re-run model recipes in a temporary directory and compare values")
    repro.add_argument("--only", nargs="+", help="Recipe IDs")
    repro.add_argument("--record", type=Path, help="Write the reproduction record here (new file)")
    docs_cmd = commands.add_parser("docs", help="Regenerate passports, traceability, and document fragments")
    docs_cmd.add_argument("--check", action="store_true", help="Fail if any generated document is stale")
    audit = commands.add_parser("audit", help="Audit a recorded CSV without connecting to hardware")
    audit.add_argument("csv", type=Path)
    audit.add_argument("--origin", choices=("unknown", "synthetic", "bench"), default="unknown")
    audit.add_argument("--gap-ms", type=float, default=500)
    audit.add_argument("--output", type=Path, required=True)
    sample = commands.add_parser("demo", help="Create an explicitly synthetic fault-injection example")
    sample.add_argument("--output", type=Path, required=True)
    session = commands.add_parser("session", help="Bench-session declaration, passport, and ingestion")
    steps = session.add_subparsers(dest="step", required=True)
    declare = steps.add_parser("declare", help="Write the operator's declaration beside a raw session")
    declare.add_argument("directory", type=Path)
    for key, meaning in S.DECLARATION_FIELDS.items():
        declare.add_argument("--" + key.replace("_", "-"), dest=key, help=meaning,
                             nargs="+" if key in ("tests", "measurement_equipment") else None)
    passport = steps.add_parser("passport", help="Build a verifiable session passport packet")
    passport.add_argument("directory", type=Path)
    passport.add_argument("--output", type=Path, required=True)
    passport.add_argument("--gap-ms", type=float, default=500)
    register = steps.add_parser("register", help="Copy a passport's raw files into the record as a review candidate")
    register.add_argument("bundle", type=Path)
    accept = steps.add_parser("accept", help="HUMAN ONLY: accept or reject a registered review candidate")
    accept.add_argument("session_id")
    accept.add_argument("--reviewer", required=True, help="Your name")
    accept.add_argument("--reject", metavar="REASON", help="Reject instead of accept, with the reason")

    args = parser.parse_args(argv)
    try:
        code = 0
        if args.command == "build":
            review = build_review(args.root, args.output, args.catalog, execution_record=args.execution_record,
                                  reproduction_record=args.reproduction_record)
            result = {"output": str(args.output), **review["counts"],
                      "scopes": {s["id"]: s["state"] for s in review["scopes"]},
                      "record_consistency_findings": len(review["violations"])}
        elif args.command == "verify":
            result = verify_bundle(args.directory, args.expected_sha256)
        elif args.command == "compare":
            result = compare_reviews(args.before, args.after)
        elif args.command == "drift":
            result = drift(args.bundle, args.root, args.catalog)
            code = 1 if result["changed_since_bundle"] or result["missing_now"] else 0
        elif args.command in ("check", "status"):
            _, _, assessment, _ = load_assessment(args.root, args.catalog)
            if args.command == "status":
                sys.stdout.write(status_text(assessment))
                return 0
            stale = D.check(args.root, assessment)
            result = {"record_consistency": "failed" if assessment["violations"] else "passed",
                      "violations": assessment["violations"], "stale_generated_docs": stale,
                      "counts": assessment["counts"],
                      "meaning": "Checks that the record is internally consistent and current. It does not "
                                 "validate engineering, run models, or establish physical performance."}
            code = 1 if assessment["violations"] or stale else 0
        elif args.command == "impact":
            records, _, _, _ = load_assessment(args.root, args.catalog)
            result = {"impact": E.impact(records, args.paths)}
        elif args.command == "query":
            _, _, assessment, _ = load_assessment(args.root, args.catalog)
            available = {q["id"]: q for q in assessment["questions"]}
            if not args.question:
                result = {key: q["question"] for key, q in available.items()}
            elif args.question not in available:
                raise EvidenceError(f"Unknown question; choose from {sorted(available)}")
            else:
                result = {**available[args.question], "source": "computed from the evidence record; not generated prose"}
        elif args.command == "snapshot":
            result = snapshot(args.root, args.claims, args.note, catalog_path=args.catalog,
                              reviewer=args.reviewer, independent=args.independent)
        elif args.command == "reproduce":
            result = reproduce(args.root, catalog_path=args.catalog, only=args.only)
            if args.record:
                if args.record.exists():
                    raise EvidenceError(f"{args.record} exists; records are not overwritten")
                args.record.parent.mkdir(parents=True, exist_ok=True)
                args.record.write_bytes(canonical_json(result))
            code = 0 if all(row["result"] == "reproduced" for row in result["results"]) else 1
        elif args.command == "docs":
            _, _, assessment, _ = load_assessment(args.root, args.catalog)
            if args.check:
                stale = D.check(args.root, assessment)
                result = {"stale_generated_docs": stale}
                code = 1 if stale else 0
            else:
                result = {"written": D.write(args.root, assessment)}
        elif args.command == "session":
            if args.step == "declare":
                fields = {key: getattr(args, key) for key in S.DECLARATION_FIELDS if getattr(args, key) is not None}
                if "ignition_servo_disconnected" in fields:
                    text = fields["ignition_servo_disconnected"].lower()
                    if text not in ("true", "false"):
                        raise EvidenceError("--ignition-servo-disconnected is true or false")
                    fields["ignition_servo_disconnected"] = text == "true"
                result = S.declare(args.directory, fields)
            elif args.step == "passport":
                document = S.build_passport(args.directory, args.output, root=args.root, gap_ms=args.gap_ms)
                result = {"output": str(args.output), "stage": document["stage"],
                          "warnings": [w["code"] for w in document["warnings"]]}
            elif args.step == "register":
                result = S.register(args.bundle, args.root, catalog_path=args.catalog)
            else:
                result = S.accept(args.root, args.session_id, args.reviewer, catalog_path=args.catalog,
                                  reject_reason=args.reject)
        else:
            result = demo(args.output) if args.command == "demo" else build_audit(
                args.csv, args.output, origin=args.origin, gap_ms=args.gap_ms)
            # A useful report is still written when audit data fails its quality checks.
            if args.command == "audit" and result["quality"] == "error":
                code = 1
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
        return code
    except (EvidenceError, OSError, UnicodeError) as exc:
        print(f"evidence: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
