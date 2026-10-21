"""Release tooling must preserve missing evidence, identity and failed builds."""

import csv
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


def test_failed_builds_cannot_package_stale_binaries_or_sign_reviews(tmp_path, monkeypatch):
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
    result = release.finalize(ROOT, output)
    assert result["decision"] == "HOLD"
    assert result["release_authorized"] is False
    assert result["human_signoff"] is None
    assert not (output / "firmware").exists()
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
