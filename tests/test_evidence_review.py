"""Evidence integrity is separate from the scientific validity of a claim."""

import copy
import csv
import io
from pathlib import Path
import subprocess
import sys

import pytest

from evidence.__main__ import demo, main
from evidence.bundle import build_audit, build_review, compare_reviews, validate_catalog, verify_bundle
from evidence.common import EvidenceError, canonical_json, digest, load_json, safe_path
from evidence.telemetry import audit_bytes


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "sample.csv").write_text("time_ms,value\n0,1\n50,2\n", encoding="utf-8")
    catalog = {
        "schema_version": 1, "project": "Review fixture", "scope": "Synthetic software test only.",
        "artifacts": [{"id": "fixture", "path": "sample.csv", "kind": "synthetic", "format": "csv",
                       "columns": ["time_ms", "value"], "min_rows": 1, "description": "Synthetic"}],
        "claims": [{"id": "C1", "title": "Fixture", "statement": "A fixture is present.",
                    "basis": "synthetic", "evidence": ["fixture"], "assumptions": ["Synthetic values."],
                    "limitations": ["No measurement."], "next_evidence": ["Physical data."], "concerns": []}],
    }
    (root / "catalog.json").write_bytes(canonical_json(catalog))
    return root, catalog


def build(project, destination):
    root, catalog = project
    (root / "catalog.json").write_bytes(canonical_json(catalog))
    return build_review(root, destination, "catalog.json")


def telemetry(samples):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=["received_at_iso", "source", "message_type", "time_ms",
                                              "roll_deg", "rate_deg_s", "servo_output"])
    writer.writeheader()
    for sample in samples:
        row = {"received_at_iso": "2026-01-01T00:00:00+00:00", "source": "fixture", "message_type": "T",
               "time_ms": "0", "roll_deg": "0", "rate_deg_s": "0", "servo_output": "0"}
        row.update(sample)
        writer.writerow(row)
    return buffer.getvalue().encode()


def codes(audit):
    return {item["code"]: item["count"] for item in audit["findings"]}


def test_project_catalog_exposes_limits_and_header_only_failure_log(tmp_path):
    review = build_review(ROOT, tmp_path / "review")
    assert len(review["claims"]) == 8
    assert review["physical_evidence_count"] == 0
    assert review["unresolved_claim_count"] == 4
    artifacts = {a["id"]: a for a in review["artifacts"]}
    assert artifacts["reliability_failures"]["row_count"] == 0
    assert artifacts["timing_fixture"]["row_count"] == 21
    assert artifacts["timing_fixture"]["kind"] == "synthetic"
    assert verify_bundle(tmp_path / "review")["integrity"] == "ok"


def test_bundle_is_byte_reproducible_and_portable(project, tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    build(project, first)
    build(project, second)
    for path in first.rglob("*"):
        if path.is_file():
            assert path.read_bytes() == (second / path.relative_to(first)).read_bytes()
    relocated = tmp_path / "moved"
    first.rename(relocated)
    expected = (relocated / "manifest.sha256").read_text().strip()
    assert verify_bundle(relocated, expected)["trusted_digest_checked"]
    # Verifier also works without the original repository or any third-party packages.
    result = subprocess.run([sys.executable, "-B", "-m", "evidence", "verify", ".."],
                            cwd=relocated / "reviewer", capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("change", ["modify", "delete", "extra", "symlink", "manifest", "trusted"])
def test_verifier_rejects_tampering(project, tmp_path, change):
    output = tmp_path / "review"
    build(project, output)
    target = output / "artifacts/sample.csv"
    kwargs = {}
    if change == "modify":
        target.write_text("altered\n")
    elif change == "delete":
        target.unlink()
    elif change == "extra":
        (output / "unlisted.txt").write_text("not in manifest")
    elif change == "symlink":
        target.unlink()
        target.symlink_to(project[0] / "sample.csv")
    elif change == "manifest":
        (output / "manifest.json").write_text("{}")
    else:
        kwargs["expected_sha256"] = "0" * 64
    with pytest.raises((EvidenceError, OSError)):
        verify_bundle(output, **kwargs)


def test_no_partial_output_or_overwriting(project, tmp_path):
    output = tmp_path / "review"
    build(project, output)
    original = (output / "manifest.json").read_bytes()
    with pytest.raises(EvidenceError, match="already exists"):
        build(project, output)
    assert (output / "manifest.json").read_bytes() == original
    (project[0] / "sample.csv").unlink()
    missing = tmp_path / "missing"
    with pytest.raises(EvidenceError):
        build(project, missing)
    assert not missing.exists()


@pytest.mark.parametrize("name", ["../secret", "/etc/passwd", "a/../b", "a//b", "./a", "C:/a", "a\\b", ".", "a\x00b"])
def test_paths_cannot_escape_or_alias(tmp_path, name):
    with pytest.raises(EvidenceError):
        safe_path(tmp_path, name)


def test_source_symlink_is_rejected(project, tmp_path):
    root, _ = project
    (root / "sample.csv").unlink()
    external = tmp_path / "outside.csv"
    external.write_text("time_ms,value\n0,1\n")
    (root / "sample.csv").symlink_to(external)
    with pytest.raises(EvidenceError, match="Symlinks"):
        build(project, tmp_path / "review")


@pytest.mark.parametrize("change", ["duplicate_id", "unknown_ref", "physical_promotion", "unknown_key", "bool_rows", "empty_limits"])
def test_invalid_catalog_never_produces_a_report(project, tmp_path, change):
    _, catalog = project
    if change == "duplicate_id":
        catalog["claims"].append(copy.deepcopy(catalog["claims"][0]))
    elif change == "unknown_ref":
        catalog["claims"][0]["evidence"] = ["missing"]
    elif change == "physical_promotion":
        catalog["claims"][0]["basis"] = "physical"
    elif change == "unknown_key":
        catalog["claims"][0]["verified"] = True
    elif change == "bool_rows":
        catalog["artifacts"][0]["min_rows"] = True
    else:
        catalog["claims"][0]["limitations"] = []
    with pytest.raises(EvidenceError):
        build(project, tmp_path / "review")
    assert not (tmp_path / "review").exists()


@pytest.mark.parametrize("text", ['{"a":1,"a":2}', '{"n":NaN}', '{"n":Infinity}', '{"n":1e999}'])
def test_ambiguous_or_nonfinite_json_is_rejected(text):
    with pytest.raises(EvidenceError):
        load_json(text)


def test_html_escapes_content_and_links(project, tmp_path):
    _, catalog = project
    attack = '<script>alert("unsafe")</script>'
    catalog["claims"][0]["title"] = attack
    catalog["claims"][0]["limitations"] = [attack]
    build(project, tmp_path / "review")
    html = (tmp_path / "review/index.html").read_text()
    assert attack not in html
    assert "&lt;script&gt;" in html
    assert "Content-Security-Policy" in html
    assert "https://" not in html


def test_compare_maps_artifact_and_classification_changes_to_claims(project, tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    build(project, old)
    (project[0] / "sample.csv").write_text("time_ms,value\n0,2\n50,3\n")
    build(project, new)
    change = compare_reviews(old, new)
    assert change["changed_artifacts"] == ["sample.csv"]
    assert change["affected_claims"] == ["C1"]
    project[1]["artifacts"][0]["description"] = "Changed interpretation"
    build(project, tmp_path / "reclassified")
    change = compare_reviews(new, tmp_path / "reclassified")
    assert change["changed_artifacts"] == []
    assert change["affected_claims"] == ["C1"]


def test_compare_marks_scope_changes_for_review(project, tmp_path):
    build(project, tmp_path / "old")
    project[1]["scope"] = "A different authored interpretation."
    build(project, tmp_path / "new")
    change = compare_reviews(tmp_path / "old", tmp_path / "new")
    assert change["review_context_changed"] is True
    assert change["affected_claims"] == ["C1"]
    assert change["changed_artifacts"] == []


def test_live_and_recovered_rows_never_share_a_clock_or_sample_count():
    data = telemetry([{"time_ms": "1000"}, {"message_type": "LOG", "time_ms": "0"},
                      {"time_ms": "1050"}, {"message_type": "LOG", "time_ms": "50"}])
    audit = audit_bytes(data, origin="synthetic")
    assert audit["quality"] == "clean"
    assert [s["valid_samples"] for s in audit["streams"]] == [2, 2]
    assert all(s["median_positive_interval_ms"] == 50 for s in audit["streams"])


@pytest.mark.parametrize("value", ["NaN", "inf", "-inf", "garbage", "", "1e999"])
def test_invalid_measurements_are_visible_not_zero_filled(value):
    audit = audit_bytes(telemetry([{"roll_deg": value}]), origin="synthetic")
    assert audit["quality"] == "error"
    assert audit["invalid_rows"] == 1
    assert audit["streams"][0]["valid_samples"] == 0
    assert "no_valid_telemetry" in codes(audit)


@pytest.mark.parametrize("value", ["-1", "1.5", "4294967296", "NaN", "1e2", "１２"])
def test_device_time_must_be_uint32(value):
    assert audit_bytes(telemetry([{"time_ms": value}]), origin="synthetic")["quality"] == "error"


def test_duplicate_conflict_reset_and_gap_are_distinct():
    audit = audit_bytes(telemetry([
        {"time_ms": "0"}, {"time_ms": "0"}, {"time_ms": "0", "roll_deg": "1"},
        {"time_ms": "700"}, {"time_ms": "10"}, {"time_ms": "60"},
    ]), origin="bench")
    assert codes(audit) == {"duplicate_sample": 1, "timestamp_conflict": 1,
                            "device_time_gap": 1, "device_clock_regression": 1}
    assert audit["streams"][0]["segments"] == 2
    assert audit["origin_is_operator_declared"] is True
    assert "packet_loss" not in audit


def test_rollover_is_reported_without_guessing_its_cause():
    audit = audit_bytes(telemetry([{"time_ms": "4294967295"}, {"time_ms": "10"}]), origin="synthetic")
    assert codes(audit) == {"device_clock_regression": 1}
    assert audit["streams"][0]["max_positive_interval_ms"] is None


def test_receive_timestamps_require_timezone_and_regressions_are_visible():
    data = telemetry([{"received_at_iso": "2026-01-02T00:00:00+00:00", "time_ms": "0"},
                      {"received_at_iso": "2026-01-01T00:00:00+00:00", "time_ms": "50"},
                      {"received_at_iso": "2026-01-01T00:00:00", "time_ms": "100"}])
    audit = audit_bytes(data, origin="synthetic")
    assert codes(audit) == {"invalid_receive_timestamp": 1, "receive_clock_regression": 1}
    assert audit["invalid_rows"] == 1


@pytest.mark.parametrize("data", [b"", b"a,a\n1,2\n", b"a,b\n1\n", b"a,b\n1,2,3\n", b"a,b\n\xff,2\n"])
def test_malformed_csv_is_rejected(data):
    with pytest.raises(EvidenceError):
        audit_bytes(data)


def test_header_only_and_unknown_origin_are_not_clean():
    audit = audit_bytes(telemetry([]))
    assert audit["quality"] == "error"
    assert "undeclared_origin" in codes(audit)
    assert "no_valid_telemetry" in codes(audit)


@pytest.mark.parametrize("threshold", [0, -1, float("nan"), float("inf"), True, "500"])
def test_gap_threshold_must_be_finite_and_positive(threshold):
    with pytest.raises(EvidenceError):
        audit_bytes(telemetry([]), gap_ms=threshold)


def test_detail_limit_does_not_truncate_issue_counts():
    audit = audit_bytes(telemetry([{"roll_deg": "NaN"}] * 110), origin="synthetic")
    assert codes(audit)["invalid_numeric_sample"] == 110
    assert len(audit["details"]) == 100
    assert audit["details_truncated"]


def test_demo_detects_exact_faults_and_preserves_input(tmp_path):
    audit = demo(tmp_path / "demo")
    assert codes(audit) == {"duplicate_sample": 1, "invalid_numeric_sample": 1,
                            "device_time_gap": 1, "device_clock_regression": 1}
    assert audit["origin"] == "synthetic"
    assert audit["quality"] == "error"
    assert verify_bundle(tmp_path / "demo/review")["integrity"] == "ok"
    csv_path = tmp_path / "demo/synthetic-telemetry.csv"
    assert (tmp_path / "demo/review/telemetry.csv").read_bytes() == csv_path.read_bytes()
    assert audit["input_sha256"] == digest(csv_path.read_bytes())


def test_cli_reports_quality_failure_after_writing_a_verifiable_bundle(tmp_path, capsys):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_bytes(telemetry([{"roll_deg": "NaN"}]))
    result = main(["audit", str(csv_path), "--origin", "synthetic", "--output", str(tmp_path / "review")])
    assert result == 1
    assert verify_bundle(tmp_path / "review")["integrity"] == "ok"
    result = main(["verify", str(tmp_path / "missing")])
    assert result == 2
    assert "evidence:" in capsys.readouterr().err
