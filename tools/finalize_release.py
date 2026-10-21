"""Build a review distribution; report release blockers without granting approval.

Never writes the evidence registries, invents a measurement or purchase, names a
human reviewer, signs on their behalf, or sends a command to connected hardware.
Exit 1 means a complete review package was produced with unresolved blockers;
exit 2 means packaging failed. Exit 0 would still require a human release decision.
"""

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evidence.bundle import build_review, provenance, verify_bundle
from evidence.bench import build_readiness
from evidence.common import EvidenceError, canonical_json, digest, new_directory, read_bytes, safe_path

REQUIRED_CHECKS = (
    "record-check", "protocol-check", "link-check", "figure-check", "openrocket-cache",
    "tests", "reproduction", "firmware-rocket", "firmware-launcher",
)
BUILD_FILENAMES = ("firmware.bin", "firmware.elf", "bootloader.bin", "partitions.bin")


def money(value):
    try:
        result = Decimal(str(value))
        valid = result.is_finite() and result >= 0 and result == result.quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise EvidenceError("Invalid monetary value") from exc
    if not valid:
        raise EvidenceError("Money must be finite, nonnegative, and precise to cents")
    return result


def procurement_status(root):
    """Receipt hashes establish integrity only; authenticity needs human review."""
    with (root / "materials/bom.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ledger_path = root / "evidence/materials/invoices.json"
    result = {"bom_lines": len(rows), "finalized_lines": 0, "recorded_paid_subtotal_usd": "0.00",
              "acquisition_cost_usd": None, "findings": [],
              "meaning": "Document integrity and reconciliation only; not proof of purchase authenticity."}
    if not rows or len({r["item"] for r in rows}) != len(rows):
        raise EvidenceError("BOM must have unique, nonempty items")
    estimate = sum((money(r["unit_price_usd"]) * money(r["qty"]) for r in rows), Decimal(0))
    result["planning_subtotal_usd"] = f"{estimate:.2f}"
    result["estimated_lines"] = sum(r["price_basis"] == "estimate" for r in rows)
    if not ledger_path.exists():
        result["findings"].append("Purchase ledger is missing")
        return result
    ledger = json.loads(read_bytes(ledger_path))
    if (ledger.get("schema") != "project33.procurement/1" or ledger.get("currency") != "USD"
            or ledger.get("record_kind") != "purchase_records" or not isinstance(ledger.get("invoices"), list)):
        raise EvidenceError("Expected a USD purchase-record ledger, not a mock ledger")
    paid = {}
    invoice_ids = set()
    for invoice in ledger["invoices"]:
        if (not invoice.get("invoice_id") or invoice["invoice_id"] in invoice_ids
                or not invoice.get("vendor") or invoice.get("transaction_status") != "paid"):
            raise EvidenceError("Invoices need unique IDs, a vendor, and paid status")
        invoice_ids.add(invoice["invoice_id"])
        try:
            datetime.strptime(invoice["purchased_on"], "%Y-%m-%d")
        except (KeyError, TypeError, ValueError) as exc:
            raise EvidenceError("Invoice needs a purchase date YYYY-MM-DD") from exc
        document = invoice.get("document", {})
        receipt = safe_path(root, document.get("path", ""))
        if not document.get("path", "").startswith("evidence/materials/receipts/"):
            raise EvidenceError("Receipt must be under evidence/materials/receipts/")
        if digest(read_bytes(receipt)) != document.get("sha256"):
            raise EvidenceError("Invoice receipt digest mismatch")
        if not isinstance(invoice.get("lines"), list) or not invoice["lines"]:
            raise EvidenceError("Invoice needs line items")
        for line in invoice["lines"]:
            if line.get("item") not in {r["item"] for r in rows}:
                raise EvidenceError("Invoice item does not match a BOM item")
            qty, total = money(line["quantity"]), money(line["line_total_usd"])
            if qty <= 0:
                raise EvidenceError("Invoice quantity must be positive")
            previous_qty, previous_total = paid.get(line["item"], (Decimal(0), Decimal(0)))
            paid[line["item"]] = (previous_qty + qty, previous_total + total)
    result["recorded_paid_subtotal_usd"] = f"{sum((v[1] for v in paid.values()), Decimal(0)):.2f}"
    for row in rows:
        qty = money(row["qty"])
        if qty <= 0:
            raise EvidenceError("BOM quantities must be positive")
        if row["price_basis"] != "purchased" or not row["purchased_price_usd"] or not row["source_date"]:
            result["findings"].append(f"{row['item']}: final purchase fields or price basis missing")
        elif paid.get(row["item"]) != (qty, money(row["purchased_price_usd"]) * qty):
            result["findings"].append(f"{row['item']}: paid quantity/total does not reconcile with BOM")
        else:
            result["finalized_lines"] += 1
    if result["finalized_lines"] == len(rows):
        result["acquisition_cost_usd"] = result["recorded_paid_subtotal_usd"]
    return result


def source_inventory(root):
    """Git-selected source, including new files, excluding ignored/private builds."""
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root, check=True,
                             capture_output=True, text=True, timeout=30).stdout.strip()
        if Path(top).resolve() != root.resolve():
            raise ValueError("Portable source directory is not the parent Git checkout")
        run = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                             cwd=root, check=True, capture_output=True, timeout=30)
        names = run.stdout.decode("utf-8").strip("\0").split("\0")
    except (OSError, ValueError, subprocess.SubprocessError):
        # The portable source snapshot deliberately contains no .git directory.
        excluded = {".git", ".venv", "venv", "env", "node_modules", "build", "dist", ".pio",
                    ".pytest_cache", "__pycache__", "TestSessions", "TelemetryLogs"}
        names = []
        for directory, subdirs, files in os.walk(root):
            subdirs[:] = [name for name in subdirs if name not in excluded and not name.startswith(".evidence-")]
            for name in files:
                path = Path(directory) / name
                if name != "wifi_config.h" and path.suffix not in (".pyc", ".log"):
                    names.append(path.relative_to(root).as_posix())
    result = []
    for name in sorted(set(names)):
        if (not name or name == "Firmware/Launcher/src/wifi_config.h"
                or any(p.startswith(".evidence-") for p in Path(name).parts)):
            continue
        path = safe_path(root, name)
        raw = read_bytes(path)
        result.append({"path": name, "bytes": len(raw), "sha256": digest(raw)})
    return result


def run_step(root, stage, name, args, *, timeout=900):
    """Keep actual output even on a failed build. Never reuse previous binaries."""
    log = stage / "logs" / f"{name}.txt"
    log.parent.mkdir(exist_ok=True)
    print(f"Running {name}...", flush=True)
    try:
        with log.open("wb") as handle:
            run = subprocess.run([sys.executable, *args], cwd=root, stdout=handle,
                                 stderr=subprocess.STDOUT, timeout=timeout)
        code = run.returncode
    except (OSError, subprocess.TimeoutExpired) as exc:
        with log.open("ab") as handle:
            handle.write(f"\n{type(exc).__name__}: {exc}\n".encode("utf-8"))
        code = 2
    return {"name": name, "command": ["python", *args], "exit_code": code,
            "result": "passed" if code == 0 else "failed", "log": log.relative_to(stage).as_posix()}


def release_blockers(assessment, procurement, checks):
    blockers = []
    for item in assessment["discrepancies"]:
        if item["status"] == "open":
            blockers.append({"code": "open_discrepancy", "id": item["id"], "detail": item["title"]})
    for req in assessment["requirements"]:
        if req["result"] != "satisfied":
            blockers.append({"code": "requirement_incomplete", "id": req["id"], "detail": req["label"]})
    for claim in assessment["claims"]:
        if claim["status"] != "supported_within_limits":
            blockers.append({"code": "claim_incomplete", "id": claim["id"], "detail": claim["status_label"]})
    for finding in assessment["violations"]:
        blockers.append({"code": "record_consistency", "detail": finding["message"]})
    check_counts = Counter(check["name"] for check in checks)
    for name in REQUIRED_CHECKS:
        if check_counts[name] != 1:
            blockers.append({"code": "software_check_inventory", "id": name,
                             "detail": "Exactly one result is required for this check"})
    for check in checks:
        if check["result"] != "passed" or check.get("exit_code") != 0:
            blockers.append({"code": "software_check_incomplete", "id": check["name"], "detail": check["result"]})
    execution = assessment.get("execution_record") or {}
    if not execution.get("tests"):
        blockers.append({"code": "execution_record_missing", "detail": "A nonempty software test run record is required"})
    if execution.get("failed", 0):
        blockers.append({"code": "tests_failed", "detail": "The software run record contains failed tests"})
    if execution.get("skipped", 0):
        blockers.append({"code": "tests_skipped", "detail": "Skipped software tests are not verified"})
    # Partial reproduction is useful for investigation, but a full distribution
    # must account for every declared recipe output exactly once.
    expected = {(recipe["id"], artifact) for recipe in assessment["recipes"]
                for artifact in recipe["outputs"]}
    reproduced = (assessment.get("reproduction_record") or {}).get("results", [])
    actual = Counter((row["recipe"], row["artifact"]) for row in reproduced)
    if not expected or set(actual) != expected or any(count != 1 for count in actual.values()):
        blockers.append({"code": "reproduction_coverage", "detail": "Every declared model output needs exactly one reproduction result"})
    current = {artifact["id"]: artifact["sha256"] for artifact in assessment["artifacts"]}
    for row in reproduced:
        if row["result"] != "reproduced" or current.get(row["artifact"]) != row["committed_sha256"]:
            blockers.append({"code": "reproduction_unverified", "id": row["artifact"],
                             "detail": "Model result failed or refers to different committed bytes"})
    if procurement["acquisition_cost_usd"] is None:
        blockers.append({"code": "procurement_incomplete", "detail": "Paid acquisition cost is not established"})
    return blockers


def copy_build_outputs(source, destination):
    """Publish only a complete, nonempty set from a successful build.

    Read all inputs before creating the output directory. Missing, empty or
    unreadable inputs must not leave an apparently usable partial artifact set.
    The caller remains responsible for checking the actual build exit code.
    """
    contents = {}
    for filename in BUILD_FILENAMES:
        raw = read_bytes(source / filename)
        if not raw:
            raise EvidenceError(f"Empty build output: {filename}")
        contents[filename] = raw
    with new_directory(destination) as stage:
        for filename, raw in contents.items():
            (stage / filename).write_bytes(raw)
    return list(contents)


def finalize(root, output, *, skip_firmware=False, bench_plan=None, bench_observations=None):
    if bench_observations is not None and bench_plan is None:
        raise EvidenceError("Bench observations require their configuration plan")
    root = Path(root).resolve()
    before = source_inventory(root)
    with new_directory(output) as stage:
        checks = []
        for name, args in [
            ("record-check", ["-m", "evidence", "check"]),
            ("protocol-check", ["tools/generate_protocol.py", "--check"]),
            ("link-check", ["tools/check_markdown_links.py"]),
            ("figure-check", ["tools/review_figures.py", "--check"]),
            ("openrocket-cache", ["Simulation/openrocket_reference.py", "--ork", "Simulation/Folding Stabilized Rocket.ork",
                                 "--emit", str(stage / "openrocket-cache.json")]),
            ("tests", ["-m", "pytest", "tests", "Firmware/tests", "-q", f"--junitxml={stage / 'tests.xml'}"]),
            ("reproduction", ["-m", "evidence", "reproduce", "--record", str(stage / "reproduction.json")]),
        ]:
            checks.append(run_step(root, stage, name, args))
        firmware = []
        for project, env in (("Rocket", "rocket"), ("Launcher", "launcher")):
            name = f"firmware-{env}"
            if skip_firmware:
                checks.append({"name": name, "result": "not_run", "exit_code": None})
                continue
            check = run_step(root, stage, name, ["-m", "platformio", "run", "-d", f"Firmware/{project}"], timeout=1800)
            checks.append(check)
            if check["result"] != "passed":
                continue
            artifacts = []
            try:
                filenames = copy_build_outputs(root / "Firmware" / project / ".pio/build" / env,
                                               stage / "firmware" / env)
                artifacts = [f"firmware/{env}/{filename}" for filename in filenames]
            except (OSError, EvidenceError) as exc:
                check.update(result="failed", detail=f"Build outputs unavailable: {exc}")
            firmware.append({"project": project, "environment": env, "artifacts": artifacts,
                             "build": check, "hardware_validation": "NOT ESTABLISHED"})
        assessment = build_review(root, stage / "review",
                                  execution_record=stage / "tests.xml" if (stage / "tests.xml").exists() else None,
                                  reproduction_record=stage / "reproduction.json" if (stage / "reproduction.json").exists() else None)
        verify_bundle(stage / "review")
        procurement = procurement_status(root)
        # record-check validates committed docs against the record alone.
        # Attached execution records intentionally enrich the portable review;
        # comparing that view with committed docs creates false stale warnings.
        blockers = release_blockers(assessment, procurement, checks)
        bench = None
        if bench_plan is None:
            blockers.append({"code": "bench_configuration_missing", "detail": "No configuration-bound bench observation packet was supplied"})
        else:
            bench = build_readiness(root, bench_plan, stage / "bench", bench_observations)
            verify_bundle(stage / "bench")
            if bench["stage"] != "observation_review_candidate":
                blockers.append({"code": "bench_observations_incomplete", "detail": "Bench configuration or observation metadata is incomplete; see bench/readiness.json"})
        wifi = root / "Firmware/Launcher/src/wifi_config.h"
        example = root / "Firmware/Launcher/src/wifi_config.h.example"
        wifi_hash = digest(read_bytes(wifi)) if wifi.exists() else None
        if wifi_hash is not None and example.exists() and wifi_hash == digest(read_bytes(example)):
            blockers.append({"code": "example_wifi_configuration", "detail": "Launcher uses public example bench credentials"})
        if before != source_inventory(root):
            blockers.append({"code": "source_changed_during_build", "detail": "Repeat the build from stable source"})
        cached_path = stage / "openrocket-cache.json"
        cached = json.loads(read_bytes(cached_path)) if cached_path.exists() else None
        report = {"schema": "project33.release_review/1", "created_utc": datetime.now(timezone.utc).isoformat(),
                  "decision": "HOLD" if blockers else "HUMAN_REVIEW_REQUIRED", "release_authorized": False,
                  "human_signoff": None, "scope": "Inert bench review distribution; no flight or field authorization",
                  "launcher_local_configuration_sha256": wifi_hash,
                  "openrocket_cache": None if cached is None else {
                      "artifact": "openrocket-cache.json", "evidence_class": "simulated",
                      "source_sha256": cached["source_sha256"], "creator_as_saved": cached["creator_as_saved"],
                      "generating_geometry_sha256": None},
                  "provenance": provenance(root), "counts": assessment["counts"], "checks": checks,
                  "bench_readiness": None if bench is None else {"artifact": "bench/readiness.json", "stage": bench["stage"],
                                                                "measurement_acceptance": "NOT PERFORMED"},
                  "procurement": procurement, "firmware": firmware, "blockers": blockers,
                  "meaning": "SHA-256 hashes identify files; they are not signatures, measurements, or human approval."}
        (stage / "release-review.json").write_bytes(canonical_json(report))
        (stage / "source-manifest.json").write_bytes(canonical_json({"files": before}))
        for item in before:
            target = stage / "source" / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / item["path"], target)
            if digest(read_bytes(target)) != item["sha256"]:
                raise EvidenceError("Source changed while copying the distribution")
        shutil.copyfile(root / "LICENSE", stage / "LICENSE")
        (stage / "README.txt").write_text(
            f"PROJECT 33: {report['decision']}\n\n"
            "Open review/index.html and release-review.json. Read source/docs/USER_GUIDE.md.\n"
            "This is a review distribution. Hardware performance and flight readiness are not established.\n"
            "Firmware was compiled only; no device was flashed and no hardware commands were sent.\n"
            "Hashes establish file identity, not authenticity or approval. No human signature was created.\n"
            "Use a trusted checkout to verify the review packet: python -m evidence verify PATH/review\n"
            "Package files are listed in SHA256SUMS (the file excludes itself).\n", encoding="utf-8")
        lines = [f"{digest(read_bytes(p))}  {p.relative_to(stage).as_posix()}"
                 for p in sorted(stage.rglob("*")) if p.is_file()]
        (stage / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist", help="New directory; never overwritten")
    parser.add_argument("--skip-firmware", action="store_true", help="Offline review only; records firmware as NOT RUN")
    parser.add_argument("--bench-plan", type=Path, help="Frozen configuration and measurement plan")
    parser.add_argument("--bench-observations", type=Path, help="Actual observation metadata and relative raw-file references")
    args = parser.parse_args(argv)
    try:
        report = finalize(ROOT, args.output, skip_firmware=args.skip_firmware,
                          bench_plan=args.bench_plan, bench_observations=args.bench_observations)
        print(json.dumps({"output": str(args.output), "decision": report["decision"],
                          "blockers": len(report["blockers"]), "release_authorized": False}, indent=2))
        return 1 if report["blockers"] else 0
    except (EvidenceError, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f"finalize_release: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
