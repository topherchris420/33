"""Evidence integrity is separate from the scientific validity of a claim."""

import csv
import io
from pathlib import Path
import subprocess
import sys

import pytest

from evidence.__main__ import demo, main
from evidence.bundle import build_audit, build_review, compare_reviews, verify_bundle
from evidence.common import EvidenceError, digest, load_json, safe_path
from evidence.telemetry import audit_bytes
from evidence_project import Project

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path):
    return Project(tmp_path / "project")


def build(project, destination, **kwargs):
    project.save()
    return build_review(project.root, destination, "catalog.json", **kwargs)


def telemetry(samples, raw=False, gains=False):
    buffer = io.StringIO(newline="")
    fields = ["received_at_iso", "source", "message_type", "time_ms", "roll_deg", "rate_deg_s", "servo_output"]
    fields += ["raw"] if raw else []
    fields += ["kp", "kd"] if gains else []
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    for sample in samples:
        row = {"received_at_iso": "2026-01-01T00:00:00+00:00", "source": "fixture", "message_type": "T",
               "time_ms": "0", "roll_deg": "0", "rate_deg_s": "0", "servo_output": "0"}
        row.update(sample)
        writer.writerow({key: row.get(key, "") for key in fields})
    return buffer.getvalue().encode()


def codes(audit):
    return {item["code"]: item["count"] for item in audit["findings"]}


def test_project_record_states_what_is_and_is_not_established(tmp_path):
    review = build_review(ROOT, tmp_path / "review")
    counts = review["counts"]
    assert counts["claims"] == 8
    assert counts["declared_physical_artifacts"] == 0
    assert counts["accepted_physical_measurements"] == 0
    assert counts["predictions_not_measured"] == counts["predictions_total"]
    claims = {c["id"]: c for c in review["claims"]}
    # Unresolved claims stay unresolved; C6 and C8 are contradicted by their own records.
    assert {k for k, c in claims.items() if c["status"] in ("open", "contradicted")} >= {"C2", "C6", "C7", "C8"}
    assert not any(c["has_accepted_physical_evidence"] for c in claims.values())
    requirements = {r["id"]: r for r in review["requirements"]}
    assert requirements["R-C6-MARGIN"]["result"] == "not_satisfied"
    assert requirements["R-C5-WINDOW"]["result"] == "conflicting"
    assert requirements["R-C1-CLOSURE"]["result"] == "not_satisfied"
    assert requirements["R-C2-JITTER"]["result"] == "not_measured"
    artifacts = {a["id"]: a for a in review["artifacts"]}
    assert artifacts["reliability_failures"]["row_count"] == 0
    assert artifacts["timing_fixture"]["class"] == "synthetic"
    assert artifacts["timing_fixture"]["origins_in_data"] == ["synthetic-fixture"]
    scopes = {s["id"]: s["state"] for s in review["scopes"]}
    assert scopes["physical_performance"] == "not_established"
    assert scopes["flight_readiness"] == "not_assessed"
    assert scopes["software_tests"] == "not_run"
    assert review["violations"] == []
    assert verify_bundle(tmp_path / "review")["bundle_integrity"] == "verified"


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
    result = subprocess.run([sys.executable, "-B", "-m", "evidence", "verify", ".."],
                            cwd=relocated / "reviewer", capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("change", ["modify", "delete", "extra", "symlink", "manifest", "trusted", "record"])
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
        (output / "artifacts/unlisted.txt").write_text("not in manifest")
    elif change == "symlink":
        target.unlink()
        target.symlink_to(project.root / "sample.csv")
    elif change == "manifest":
        (output / "manifest.json").write_text("{}")
    elif change == "record":
        (output / "records/requirements.json").write_text("{}")
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
    (project.root / "sample.csv").unlink()
    with pytest.raises(EvidenceError):
        build(project, tmp_path / "missing")
    assert not (tmp_path / "missing").exists()


@pytest.mark.parametrize("name", ["../secret", "/etc/passwd", "a/../b", "a//b", "./a", "C:/a", "a\\b", ".", "a\x00b"])
def test_paths_cannot_escape_or_alias(tmp_path, name):
    with pytest.raises(EvidenceError):
        safe_path(tmp_path, name)


def test_source_symlink_is_rejected(project, tmp_path):
    (project.root / "sample.csv").unlink()
    external = tmp_path / "outside.csv"
    external.write_text("time_ms,value,origin\n0,1,synthetic\n")
    (project.root / "sample.csv").symlink_to(external)
    with pytest.raises(EvidenceError, match="Symlinks"):
        build(project, tmp_path / "review")


@pytest.mark.parametrize("change", ["duplicate_id", "unknown_ref", "old_basis", "unknown_key", "bool_rows",
                                    "empty_limits", "physical_class", "field_class", "verified_class", "kind_field",
                                    "execution_class", "cycle", "unlinked_requirement", "missing_record_file"])
def test_invalid_record_never_produces_a_report(project, tmp_path, change):
    catalog, claim = project.catalog, project.claim
    if change == "duplicate_id":
        catalog["claims"].append(dict(claim))
    elif change == "unknown_ref":
        claim["evidence"] = ["missing"]
    elif change == "old_basis":
        claim["basis"] = "physical"
    elif change == "unknown_key":
        claim["verified"] = True
    elif change == "bool_rows":
        catalog["artifacts"][2]["min_rows"] = True
    elif change == "empty_limits":
        claim["limitations"] = []
    elif change == "physical_class":
        catalog["artifacts"][2]["class"] = "physical"
    elif change == "field_class":
        catalog["artifacts"][2]["class"] = "field_measured"
    elif change == "verified_class":
        catalog["artifacts"][2]["class"] = "verified"
    elif change == "kind_field":
        catalog["artifacts"][2]["kind"] = "synthetic"
    elif change == "execution_class":
        catalog["artifacts"][3]["class"] = "execution_record"
    elif change == "cycle":
        catalog["artifacts"][0]["derived_from"] = ["out"]
    elif change == "unlinked_requirement":
        claim["requirements"] = []
    else:
        project.save()
        (project.root / "discrepancies.json").unlink()
        with pytest.raises((EvidenceError, OSError)):
            build_review(project.root, tmp_path / "review", "catalog.json")
        assert not (tmp_path / "review").exists()
        return
    with pytest.raises(EvidenceError):
        build(project, tmp_path / "review")
    assert not (tmp_path / "review").exists()


@pytest.mark.parametrize("text", ['{"a":1,"a":2}', '{"n":NaN}', '{"n":Infinity}', '{"n":1e999}'])
def test_ambiguous_or_nonfinite_json_is_rejected(text):
    with pytest.raises(EvidenceError):
        load_json(text)


def test_html_escapes_content_and_links(project, tmp_path):
    attack = '<script>alert("unsafe")</script>'
    project.claim["title"] = attack
    project.claim["limitations"] = [attack]
    build(project, tmp_path / "review")
    html = (tmp_path / "review/index.html").read_text()
    assert attack not in html
    assert "&lt;script&gt;" in html
    assert "Content-Security-Policy" in html
    assert "https://" not in html and "http://" not in html


def test_compare_maps_artifact_and_classification_changes_to_claims(project, tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    build(project, old)
    (project.root / "model.py").write_text(project.root.joinpath("model.py").read_text() + "# edited\n")
    build(project, new)
    change = compare_reviews(old, new)
    assert change["changed_artifacts"] == ["model.py"]
    assert change["affected_claims"] == ["C1"]
    project.catalog["artifacts"][2]["description"] = "Changed interpretation"
    build(project, tmp_path / "reclassified")
    change = compare_reviews(new, tmp_path / "reclassified")
    assert change["changed_artifacts"] == []
    assert change["changed_artifact_records"] == ["sample.csv"]
    assert change["affected_claims"] == ["C1"]


def test_compare_reports_requirement_result_changes(project, tmp_path):
    build(project, tmp_path / "old")
    (project.root / "out.json").write_text('{"value": 0.1, "flag": true, "missing": null}')
    project.claim["status"] = "contradicted"
    build(project, tmp_path / "new")
    change = compare_reviews(tmp_path / "old", tmp_path / "new")
    assert change["requirement_changes"] == [{"requirement": "R-1", "before": "satisfied", "after": "not_satisfied"}]
    assert change["claim_status_changes"] == [{"claim": "C1", "before": "supported_within_limits", "after": "contradicted"}]


def test_compare_marks_scope_changes_for_review(project, tmp_path):
    build(project, tmp_path / "old")
    project.catalog["scope"] = "A different authored interpretation."
    build(project, tmp_path / "new")
    change = compare_reviews(tmp_path / "old", tmp_path / "new")
    assert change["review_context_changed"] is True
    assert change["affected_claims"] == ["C1"]


def test_live_and_recovered_rows_never_share_a_clock_or_sample_count():
    data = telemetry([{"time_ms": "1000"}, {"message_type": "LOG", "time_ms": "0"},
                      {"time_ms": "1050"}, {"message_type": "LOG", "time_ms": "50"}])
    audit = audit_bytes(data, origin="synthetic")
    assert audit["quality"] == "clean"
    assert [s["valid_samples"] for s in audit["streams"]] == [2, 2]
    assert {s["message_type"]: s["clock_domain"] for s in audit["streams"]} == \
        {"LOG": "rocket_millis", "T": "launcher_relay_millis"}


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
    assert codes(audit) == {"duplicate_sample": 1, "timestamp_conflict": 1, "device_time_gap": 1,
                            "device_clock_regression": 1, "interval_differs_from_expected": 1}
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


def test_partial_log_dump_is_reported_not_assumed_complete():
    rows = [{"message_type": "RAW", "raw": "LOG_START,3", "time_ms": ""},
            {"message_type": "LOG", "time_ms": "0", "raw": "LOG,0"},
            {"message_type": "LOG", "time_ms": "50", "raw": "LOG,50"},
            {"message_type": "RAW", "raw": "LOG_END", "time_ms": ""},
            {"message_type": "RAW", "raw": "LOG_START,2", "time_ms": ""},
            {"message_type": "LOG", "time_ms": "0", "raw": "LOG,0"}]
    audit = audit_bytes(telemetry(rows, raw=True), origin="synthetic")
    assert [d["state"] for d in audit["log_dumps"]] == ["incomplete", "unterminated"]
    assert codes(audit)["log_dump_incomplete"] == 1
    assert codes(audit)["log_dump_unterminated"] == 1


def test_gain_windows_follow_changes_and_rejections_are_counted():
    rows = [{"message_type": "STATUS", "kp": "0.50", "kd": "0.20", "time_ms": ""},
            {"message_type": "STATUS", "kp": "0.50", "kd": "0.20", "time_ms": ""},
            {"message_type": "STATUS", "kp": "0.80", "kd": "0.30", "time_ms": ""},
            {"message_type": "RAW", "raw": "CMD_REJECT:dashboard_launch_disabled", "time_ms": ""},
            {"time_ms": "0"}]
    audit = audit_bytes(telemetry(rows, raw=True, gains=True), origin="synthetic")
    assert [(g["kp"], g["kd"], g["status_rows"]) for g in audit["gain_windows"]] == [("0.50", "0.20", 2), ("0.80", "0.30", 1)]
    assert audit["command_responses"] == [{"code": "CMD_REJECT:dashboard_launch_disabled", "count": 1}]


def test_missing_columns_are_not_recorded_rather_than_empty():
    audit = audit_bytes(telemetry([{"time_ms": "0"}]), origin="synthetic")
    assert audit["gain_windows"] is None and audit["log_dumps"] is None


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
    assert codes(audit) == {"duplicate_sample": 1, "invalid_numeric_sample": 1, "device_time_gap": 1,
                            "device_clock_regression": 1, "interval_differs_from_expected": 1,
                            "log_dump_unterminated": 1}
    assert audit["origin"] == "synthetic"
    assert audit["quality"] == "error"
    assert "series" not in load_json((tmp_path / "demo/review/audit.json").read_bytes())
    assert verify_bundle(tmp_path / "demo/review")["bundle_integrity"] == "verified"
    csv_path = tmp_path / "demo/synthetic-telemetry.csv"
    assert (tmp_path / "demo/review/telemetry.csv").read_bytes() == csv_path.read_bytes()
    assert audit["input_sha256"] == digest(csv_path.read_bytes())
    assert "<svg" in (tmp_path / "demo/review/index.html").read_text()


def test_cli_reports_quality_failure_after_writing_a_verifiable_bundle(tmp_path, capsys):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_bytes(telemetry([{"roll_deg": "NaN"}]))
    result = main(["audit", str(csv_path), "--origin", "synthetic", "--output", str(tmp_path / "review")])
    assert result == 1
    assert verify_bundle(tmp_path / "review")["bundle_integrity"] == "verified"
    assert main(["verify", str(tmp_path / "missing")]) == 2
    assert "evidence:" in capsys.readouterr().err


def test_repository_record_is_consistent_and_generated_docs_are_current(capsys):
    # Fails when evidence changes without a review snapshot, a prediction drifts,
    # or a generated passport/fragment no longer matches the record.
    assert main(["check"]) == 0, capsys.readouterr().out
