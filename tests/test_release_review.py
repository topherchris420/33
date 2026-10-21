"""Release tooling must preserve missing evidence, identity and failed builds."""

import csv
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import finalize_release as release
import generate_release_fixture as fixture
from evidence.bundle import verify_bundle
from evidence.common import EvidenceError, canonical_json, digest
from evidence.telemetry import audit_bytes
from telemetry_log import FIELDNAMES, TelemetryCsvLogger


def registry_bytes():
    return {p.name: p.read_bytes() for p in (ROOT / "evidence").glob("*.json")}


def test_synthetic_fixture_is_compatible_but_never_a_measurement(tmp_path):
    before = registry_bytes()
    output = tmp_path / "fixture"
    document = fixture.generate(output)
    csv_path = output / "synthetic-dashboard/telemetry.csv"
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert set(FIELDNAMES).issubset(reader.fieldnames)
        rows = list(reader)
    assert len(rows) == 201
    assert rows[0]["time_ms"] == "0" and rows[-1]["time_ms"] == "10000"
    assert {r["origin"] for r in rows} == {"synthetic"}
    assert {r["source"] for r in rows} == {"synthetic-fixture"}
    # Each invented payload passes through the same parser used by the dashboard.
    logger = TelemetryCsvLogger(tmp_path / "reparsed.csv")
    try:
        for row in rows:
            logger.log_packet(row["raw"], source=row["source"])
    finally:
        logger.close()
    audit = audit_bytes(csv_path.read_bytes(), origin="synthetic")
    assert audit["quality"] == "clean"
    assert audit["origin"] == "synthetic"
    assert document["stage"] == "audited"
    assert document["origin_declared"] == "synthetic"
    assert verify_bundle(output / "passport")["bundle_integrity"] == "verified"
    assert registry_bytes() == before
    second = tmp_path / "fixture-2"
    fixture.generate(second)
    assert csv_path.read_bytes() == (second / "synthetic-dashboard/telemetry.csv").read_bytes()
    with pytest.raises(EvidenceError):
        fixture.generate(output)


def purchase_project(tmp_path):
    (tmp_path / "materials").mkdir()
    (tmp_path / "materials/bom.csv").write_text(
        "item,qty,unit_price_usd,price_basis,purchased_price_usd,source_date\n"
        "Fixture part,2,4,purchased,4,2000-01-01\n", encoding="utf-8")
    folder = tmp_path / "evidence/materials/receipts"
    folder.mkdir(parents=True)
    receipt = b"SYNTHETIC UNIT TEST DOCUMENT, NOT AN INVOICE\n"
    (folder / "fixture.txt").write_bytes(receipt)
    ledger = {"schema": "project33.procurement/1", "currency": "USD", "record_kind": "purchase_records",
              "invoices": [{"invoice_id": "UNIT-TEST-ONLY", "vendor": "Software test fixture",
                            "purchased_on": "2000-01-01", "transaction_status": "paid",
                            "document": {"path": "evidence/materials/receipts/fixture.txt", "sha256": digest(receipt)},
                            "lines": [{"item": "Fixture part", "quantity": "2", "line_total_usd": "8.00"}]}]}
    return ledger


def save_ledger(root, ledger):
    (root / "evidence/materials/invoices.json").write_bytes(canonical_json(ledger))


def test_purchase_reconciliation_checks_totals_and_receipt_bytes(tmp_path):
    ledger = purchase_project(tmp_path)
    save_ledger(tmp_path, ledger)
    assert release.procurement_status(tmp_path)["acquisition_cost_usd"] == "8.00"
    ledger["invoices"][0]["lines"][0]["quantity"] = "1"
    save_ledger(tmp_path, ledger)
    assert release.procurement_status(tmp_path)["acquisition_cost_usd"] is None
    (tmp_path / "evidence/materials/receipts/fixture.txt").write_bytes(b"tampered")
    with pytest.raises(EvidenceError, match="digest mismatch"):
        release.procurement_status(tmp_path)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "1.001", "not-money"])
def test_invalid_money_cannot_become_a_purchase(value):
    with pytest.raises(EvidenceError):
        release.money(value)


def test_mock_ledger_is_rejected_and_missing_real_prices_stay_unknown(tmp_path):
    ledger = purchase_project(tmp_path)
    ledger["invoices"] = []
    save_ledger(tmp_path, ledger)
    current = release.procurement_status(tmp_path)
    assert current["finalized_lines"] == 0
    assert current["acquisition_cost_usd"] is None
    ledger["record_kind"] = "synthetic_example"
    save_ledger(tmp_path, ledger)
    with pytest.raises(EvidenceError, match="not a mock ledger"):
        release.procurement_status(tmp_path)


def test_failed_command_keeps_diagnostics(tmp_path):
    check = release.run_step(ROOT, tmp_path, "expected-failure", ["-c", "print('test diagnostic'); raise SystemExit(7)"])
    assert check["result"] == "failed" and check["exit_code"] == 7
    assert "test diagnostic" in (tmp_path / check["log"]).read_text()


@pytest.mark.parametrize("include_bench", [False, True])
def test_failed_builds_cannot_package_stale_binaries_or_sign_reviews(tmp_path, monkeypatch, include_bench):
    before = registry_bytes()

    def failed_step(root, stage, name, args, **kwargs):
        if name == "tests":
            # Attach a synthetic software run record in this temporary unit
            # fixture. Its enriched C3 view must not stale committed docs.
            suite = ET.Element("testsuite")
            requirements = json.loads((ROOT / "evidence/requirements.json").read_bytes())["requirements"]
            for req in requirements:
                for test in req.get("tests_required", []):
                    module, function = test.split("::")
                    ET.SubElement(suite, "testcase", classname=f"tests.{module}", name=function)
            (stage / "tests.xml").write_bytes(ET.tostring(suite))
        return {"name": name, "result": "failed", "exit_code": 7}

    monkeypatch.setattr(release, "run_step", failed_step)
    output = tmp_path / "review-dist"
    kwargs = {}
    if include_bench:
        from evidence.bench import create_plan, create_observation_template
        create_plan(ROOT, tmp_path / "bench-plan")
        create_observation_template(tmp_path / "bench-plan/plan.json", tmp_path / "bench-capture")
        kwargs = {"bench_plan": tmp_path / "bench-plan/plan.json",
                  "bench_observations": tmp_path / "bench-capture/observations.json"}
    result = release.finalize(ROOT, output, **kwargs)
    assert result["decision"] == "HOLD"
    assert result["release_authorized"] is False
    assert result["human_signoff"] is None
    assert not (output / "firmware").exists()
    if include_bench:
        assert result["bench_readiness"]["stage"] == "blocked"
        assert any(b["code"] == "bench_observations_incomplete" for b in result["blockers"])
        assert verify_bundle(output / "bench")["kind"] == "bench_readiness"
    else:
        assert result["bench_readiness"] is None
        assert any(b["code"] == "bench_configuration_missing" for b in result["blockers"])
    assert any(b.get("id") == "D-021" for b in result["blockers"])
    assert any(b["code"] == "procurement_incomplete" for b in result["blockers"])
    assert any(b.get("id") == "firmware-rocket" for b in result["blockers"])
    assert not any(b["code"] == "stale_generated_doc" for b in result["blockers"])
    assert verify_bundle(output / "review")["bundle_integrity"] == "verified"
    assert not (output / "source/Firmware/Launcher/src/wifi_config.h").exists()
    assert (output / "source/docs/USER_GUIDE.md").exists()
    assert registry_bytes() == before


def test_portable_source_inside_an_ignored_parent_checkout_is_still_inventoried(tmp_path):
    parent = tmp_path / "parent"
    parent.mkdir()
    subprocess.run(["git", "init", str(parent)], check=True, capture_output=True)
    (parent / ".gitignore").write_text("dist/\n", encoding="utf-8")
    portable = parent / "dist/source"
    portable.mkdir(parents=True)
    (portable / "main.py").write_text("# synthetic source fixture\n", encoding="utf-8")
    (portable / ".venv").mkdir()
    (portable / ".venv/cache.py").write_text("# excluded cache\n", encoding="utf-8")
    (portable / "wifi_config.h").write_text("// excluded private configuration\n", encoding="utf-8")
    assert [p["path"] for p in release.source_inventory(portable)] == ["main.py"]


def complete_software_review():
    """Small synthetic record for testing the software audit, not a real review."""
    assessment = {
        "discrepancies": [], "requirements": [], "claims": [], "violations": [],
        "execution_record": {"tests": 1, "passed": 1, "failed": 0, "skipped": 0},
        "recipes": [{"id": "fixture", "outputs": {"a": "a.json", "b": "b.json"}}],
        "artifacts": [{"id": name, "sha256": "a" * 64} for name in ("a", "b")],
        "reproduction_record": {"results": [
            {"artifact": name, "recipe": "fixture", "committed_sha256": "a" * 64,
             "result": "reproduced"} for name in ("a", "b")]},
    }
    checks = [{"name": name, "result": "passed", "exit_code": 0} for name in release.REQUIRED_CHECKS]
    return assessment, {"acquisition_cost_usd": "8.00"}, checks


@pytest.mark.parametrize("change", ["missing", "duplicate", "nonzero_exit", "no_exit_code"])
def test_software_check_inventory_cannot_silently_drop_checks(change):
    assessment, procurement, checks = complete_software_review()
    if change == "missing":
        checks.pop()
    elif change == "duplicate":
        checks.append(deepcopy(checks[-1]))
    elif change == "nonzero_exit":
        checks[-1]["exit_code"] = 7
    else:
        checks[-1].pop("exit_code")
    blockers = release.release_blockers(assessment, procurement, checks)
    assert any(b["code"] in ("software_check_inventory", "software_check_incomplete") for b in blockers)


@pytest.mark.parametrize("record,code", [
    (None, "execution_record_missing"),
    ({"tests": 0}, "execution_record_missing"),
    ({"tests": 1, "failed": 1}, "tests_failed"),
    ({"tests": 1, "skipped": 1}, "tests_skipped"),
])
def test_successful_command_cannot_substitute_for_test_evidence(record, code):
    assessment, procurement, checks = complete_software_review()
    assessment["execution_record"] = record
    assert code in {b["code"] for b in release.release_blockers(assessment, procurement, checks)}


@pytest.mark.parametrize("change", ["missing", "empty", "partial", "duplicate", "wrong_recipe", "stale", "failed"])
def test_complete_current_reproduction_evidence_is_required(change):
    assessment, procurement, checks = complete_software_review()
    rows = assessment["reproduction_record"]["results"]
    if change == "missing":
        assessment["reproduction_record"] = None
    elif change == "empty":
        rows.clear()
    elif change == "partial":
        rows.pop()
    elif change == "duplicate":
        rows.append(deepcopy(rows[0]))
    elif change == "wrong_recipe":
        rows[0]["recipe"] = "unrelated"
    elif change == "stale":
        rows[0]["committed_sha256"] = "b" * 64
    else:
        rows[0]["result"] = "differs"
    assert any(b["code"].startswith("reproduction_")
               for b in release.release_blockers(assessment, procurement, checks))


def test_complete_software_evidence_does_not_create_false_blockers():
    assert release.release_blockers(*complete_software_review()) == []


@pytest.mark.parametrize("fault", ["missing", "empty"])
def test_partial_build_cannot_publish_any_binary(tmp_path, fault):
    source = tmp_path / "build"
    source.mkdir()
    for name in release.BUILD_FILENAMES[:-1]:
        (source / name).write_bytes(b"SYNTHETIC SOFTWARE TEST, NOT FIRMWARE")
    if fault == "empty":
        (source / release.BUILD_FILENAMES[-1]).touch()
    destination = tmp_path / "package"
    with pytest.raises((OSError, EvidenceError)):
        release.copy_build_outputs(source, destination)
    assert not destination.exists()


def test_complete_build_artifacts_preserve_exact_bytes_and_refuse_overwrite(tmp_path):
    source = tmp_path / "build"
    source.mkdir()
    for name in release.BUILD_FILENAMES:
        (source / name).write_bytes(f"SYNTHETIC TEST {name}, NOT FIRMWARE".encode())
    destination = tmp_path / "package/board"
    release.copy_build_outputs(source, destination)
    assert {p.name: p.read_bytes() for p in destination.iterdir()} == {
        p.name: p.read_bytes() for p in source.iterdir()}
    with pytest.raises(EvidenceError):
        release.copy_build_outputs(source, destination)


def test_distribution_refuses_observations_without_their_plan(tmp_path):
    with pytest.raises(EvidenceError, match="require their configuration plan"):
        release.finalize(ROOT, tmp_path / "dist", bench_observations=tmp_path / "unbound.json")
    assert not (tmp_path / "dist").exists()
