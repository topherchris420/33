"""Try to fool the reviewer. Each test is a way a reasonable reader could be misled."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from evidence import docs as D
from evidence import evaluate as E
from evidence import records as R
from evidence import session as S
from evidence.bundle import build_review, drift, load_assessment
from evidence.common import EvidenceError, canonical_json, digest
from evidence.records import preregistration_fingerprint
from evidence.workflow import reproduce, snapshot
from evidence_project import Project

ROOT = Path(__file__).resolve().parents[1]
JUNIT = """<?xml version="1.0"?><testsuites><testsuite name="pytest">
<testcase classname="tests.test_model" name="test_value"{status}</testsuite></testsuites>"""


@pytest.fixture
def project(tmp_path):
    return Project(tmp_path / "project")


def assess(project, **kwargs):
    project.save()
    return load_assessment(project.root, "catalog.json", **kwargs)[2]


def codes(review):
    return {v["code"] for v in review["violations"]}


def snap(project, note="baseline"):
    project.save()
    snapshot(project.root, ["C1"], note, catalog_path="catalog.json", today="2026-01-02")
    project.records["reviews.json"] = json.loads((project.root / "reviews.json").read_text())


# ----------------------------------------------------------------- staleness

def test_changed_source_bytes_make_the_review_insufficient_not_false(project):
    snap(project)
    assert assess(project)["claims"][0]["freshness"]["state"] == "current"
    (project.root / "model.py").write_text("# retuned\n" + (project.root / "model.py").read_text())
    review = assess(project)
    claim = review["claims"][0]
    assert claim["freshness"]["states"] == ["source_changed"]
    assert claim["freshness"]["changed"] == ["model"]
    assert claim["status"] == "supported_within_limits"  # a change is not a refutation
    assert "review_not_current" in codes(review)


def test_changed_assumption_without_changed_data_is_detected(project):
    snap(project)
    project.claim["assumptions"] = ["A different, weaker assumption."]
    assert assess(project)["claims"][0]["freshness"]["states"] == ["assumption_changed"]


def test_changed_requirement_bound_counts_as_assumption_change(project):
    snap(project)
    project.records["requirements.json"]["requirements"][0]["bound"] = {"min": 0.1}
    assert "assumption_changed" in assess(project)["claims"][0]["freshness"]["states"]


def test_claim_wording_changed_while_evidence_stayed_constant(project):
    snap(project)
    project.claim["statement"] = "The calculated value comfortably exceeds 0.2 in all conditions."
    assert assess(project)["claims"][0]["freshness"]["states"] == ["statement_changed"]


def test_new_discrepancy_requires_another_review(project):
    snap(project)
    project.records["discrepancies.json"]["discrepancies"].append({
        "id": "D-001", "kind": "model_vs_model", "claims": ["C1"], "effect": "informational", "status": "open",
        "title": "Another model disagrees", "sides": [{"artifact": "out", "says": "0.25"}, {"artifact": "model", "says": "?"}],
        "found_by": "Test", "next_action": "Review", "resolution": None, "resolved_by": None})
    assert "assumption_changed" in assess(project)["claims"][0]["freshness"]["states"]


def test_missing_dependency_is_reported_by_freshness(project):
    snap(project)
    records = R.load(project.root, "catalog.json")
    (project.root / "model.py").unlink()
    data = E.load_artifact_data(records)
    state = E.freshness(records.claims["C1"], records, data)
    assert "missing_dependency" in state["states"] and state["missing"] == ["model"]


def test_never_reviewed_is_its_own_state(project):
    review = assess(project)
    assert review["claims"][0]["freshness"]["state"] == "never_reviewed"
    assert "review_missing" in codes(review)


def test_source_replaced_after_report_generation_is_visible(project, tmp_path):
    project.save()
    build_review(project.root, tmp_path / "review", "catalog.json")
    (project.root / "out.json").write_text('{"value": 0.3, "flag": true, "missing": null}')
    result = drift(tmp_path / "review", project.root, "catalog.json")
    assert result["changed_since_bundle"] == ["out.json"]
    assert result["impact"][0]["claims"] == ["C1"]


def test_stale_generated_passport_is_detected(project):
    review = assess(project)
    D.write(project.root, review)
    assert D.check(project.root, review) == []
    project.claim["statement"] = "Edited after the passport was generated."
    assert "docs/claims/C1.md" in D.check(project.root, assess(project))


def test_generated_output_does_not_depend_on_hash_seed(project, tmp_path):
    project.save()
    outputs = []
    for seed in ("1", "2"):
        destination = tmp_path / f"seed{seed}"
        subprocess.run([sys.executable, "-m", "evidence", "--root", str(project.root), "--catalog", "catalog.json",
                        "build", "--output", str(destination)], check=True, capture_output=True, cwd=ROOT,
                       env={**os.environ, "PYTHONHASHSEED": seed})
        outputs.append((destination / "manifest.sha256").read_text())
    assert outputs[0] == outputs[1]


# ----------------------------------------------------------------- promotion and relabeling

def test_synthetic_rows_cannot_be_relabeled_as_analytical_or_physical(project, tmp_path):
    project.catalog["artifacts"][2]["class"] = "analytical"
    with pytest.raises(EvidenceError, match="synthetic data cannot be relabeled"):
        assess(project)


def test_rows_claiming_bench_origin_inside_a_synthetic_artifact_are_rejected(project):
    (project.root / "sample.csv").write_text("time_ms,value,origin\n0,1,bench\n")
    with pytest.raises(EvidenceError, match="declared synthetic"):
        assess(project)


def test_physical_class_needs_an_accepted_session_to_count(project):
    project.add_session("S1", "raw bytes\n", stage="review_candidate")
    project.catalog["artifacts"].append({"id": "photo", "path": "sessions/S1/telemetry.csv", "class": "bench_observed",
                                         "format": "file", "session": "S1", "description": "Bench file"})
    project.claim["evidence"].append("photo")
    review = assess(project)
    assert review["claims"][0]["support"] == "model"  # unaccepted physical evidence lifts nothing


def test_physical_class_without_a_session_is_refused(project):
    project.catalog["artifacts"][2]["class"] = "bench_measured"
    project.catalog["artifacts"][2].pop("origin_column")
    with pytest.raises(EvidenceError, match="must name the bench session"):
        assess(project)


def test_supported_status_with_a_failing_requirement_is_refused(project):
    (project.root / "out.json").write_text('{"value": 0.1, "flag": true, "missing": null}')
    with pytest.raises(EvidenceError, match="promotes beyond its evidence"):
        assess(project)


def test_supported_status_with_open_concern_is_refused(project):
    project.claim["concerns"] = ["Unexplained discrepancy."]
    with pytest.raises(EvidenceError, match="promotes beyond its evidence"):
        assess(project)


@pytest.mark.parametrize("gate", ["inert_bench_setup", "inert_physical_measurement", "repeated_measurement",
                                  "independent_review"])
def test_gates_cannot_be_authored_past_the_evidence(project, gate):
    project.claim["gate"] = gate
    with pytest.raises(EvidenceError, match="claims gate"):
        assess(project)


def test_gate_needs_the_matching_evidence_even_below_physical(project):
    project.claim["evidence"] = ["model", "out", "tests"]
    project.claim["gate"] = "synthetic_test"
    with pytest.raises(EvidenceError, match="claims gate"):
        assess(project)


def test_duplicate_measurements_do_not_count_as_repeats(project):
    project.add_session("S1", "same raw bytes\n")
    project.add_session("S2", "same raw bytes\n")
    project.add_measurement("M1", "S1")
    project.add_measurement("M2", "S2")
    project.claim["gate"] = "repeated_measurement"
    with pytest.raises(EvidenceError, match="claims gate"):
        assess(project)
    (project.root / "sessions/S2/telemetry.csv").write_text("different raw bytes\n")
    project.records["sessions.json"]["sessions"][1]["raw_files"][0]["sha256"] = digest(b"different raw bytes\n")
    review = assess(project)
    assert review["claims"][0]["support"] == "bench_measured"
    assert review["claims"][0]["gate"] == "repeated_measurement"


def test_measurement_from_unaccepted_session_is_refused(project):
    project.add_session("S1", "raw\n", stage="review_candidate")
    project.add_measurement("M1", "S1")
    with pytest.raises(EvidenceError, match="human-accepted session"):
        assess(project)


def test_accepted_session_must_be_declared_bench(project):
    project.add_session("S1", "raw\n", origin="synthetic")
    with pytest.raises(EvidenceError, match="bench origin"):
        assess(project)


def test_raw_session_bytes_cannot_change_after_registration(project):
    project.add_session("S1", "raw\n")
    project.save()
    (project.root / "sessions/S1/telemetry.csv").write_text("edited\n")
    with pytest.raises(EvidenceError, match="raw file changed"):
        R.load(project.root, "catalog.json")


def test_bench_measured_needs_uncertainty_and_calibration(project):
    project.add_session("S1", "raw\n")
    project.add_measurement("M1", "S1", uncertainty=None)
    with pytest.raises(EvidenceError, match="uncertainty"):
        assess(project)


# ----------------------------------------------------------------- pre-registration

def _prereg(project, status="registered"):
    entry = {"id": "PR-1", "status": status, "title": "Fixture test", "claims": ["C1"], "predictions": ["P-1"],
             "requirements": ["R-1"], "proposed_by": "Tester", "registered_by": "A. Person" if status != "proposed" else None,
             "registered_on": "2026-01-10" if status != "proposed" else None, "question": "Q?", "prediction": "0.25",
             "variables": {"controlled": [], "measured": ["value"], "recorded": []}, "interpretation_rule": "Within 0.05.",
             "measurement_method": "Gauge", "known_limitations": ["Fixture."], "safety": "Inert."}
    project.records["preregistrations.json"]["preregistrations"].append(entry)
    project.records["predictions.json"]["predictions"][0]["preregistration"] = "PR-1"
    project.add_session("S1", "raw\n")
    return entry


def test_success_criteria_cannot_be_changed_after_the_result(project):
    entry = _prereg(project)
    project.add_measurement("M1", "S1", preregistration="PR-1", preregistration_fingerprint=preregistration_fingerprint(entry))
    assert assess(project)["claims"][0]["support"] == "bench_measured"
    entry["interpretation_rule"] = "Within 0.5 (loosened after seeing the result)."
    with pytest.raises(EvidenceError, match="changed after this result"):
        assess(project)


def test_measurement_before_registration_is_refused(project):
    entry = _prereg(project)
    project.add_measurement("M1", "S1", recorded="2026-01-05", preregistration="PR-1",
                            preregistration_fingerprint=preregistration_fingerprint(entry))
    with pytest.raises(EvidenceError, match="before its preregistration"):
        assess(project)


def test_proposed_preregistration_cannot_back_a_measurement(project):
    entry = _prereg(project, status="proposed")
    project.add_measurement("M1", "S1", preregistration="PR-1", preregistration_fingerprint=preregistration_fingerprint(entry))
    with pytest.raises(EvidenceError, match="never registered by a human"):
        assess(project)


def test_proposed_entry_cannot_carry_a_registrar(project):
    entry = _prereg(project, status="proposed")
    entry["registered_by"] = "Automated assistant"
    with pytest.raises(EvidenceError, match="proposed entry"):
        assess(project)


# ----------------------------------------------------------------- unknown is not zero

def test_unmeasured_prediction_is_not_zero(project):
    prediction = assess(project)["predictions"][0]
    assert prediction["result"] == "not_measured"
    assert prediction["measurements"] == []


def test_null_model_output_is_not_evaluable_not_satisfied(project):
    project.records["requirements.json"]["requirements"][0]["value"] = {"artifact": "out", "json": "/missing"}
    project.claim["status"] = "open"
    review = assess(project)
    result = review["requirements"][0]
    assert result["result"] == "not_evaluable"
    assert result["observed"] is None
    assert "no value exists" in result["reason"]


def test_misspelled_pointer_is_a_record_finding_not_a_quiet_pass(project):
    project.records["requirements.json"]["requirements"][0]["value"] = {"artifact": "out", "json": "/valeu"}
    project.claim["status"] = "open"
    review = assess(project)
    assert review["requirements"][0]["result"] == "not_evaluable"
    assert "missing_value" in codes(review)


def test_relative_error_against_zero_prediction_is_not_computable(project):
    (project.root / "out.json").write_text('{"value": 0.0, "flag": true, "missing": null}')
    project.records["predictions.json"]["predictions"][0]["value"] = 0.0
    project.records["requirements.json"]["requirements"][0]["bound"] = {"min": 0.0}
    project.records["predictions.json"]["predictions"][0]["acceptance"] = {"type": "relative", "tolerance": 0.1}
    project.add_session("S1", "raw\n")
    project.add_measurement("M1", "S1", value=0.01)
    row = assess(project)["predictions"][0]["measurements"][0]
    assert row["relative_error"] is None and row["result"] == "not_comparable"


def test_retuned_model_output_is_prediction_drift(project):
    (project.root / "out.json").write_text('{"value": 0.31, "flag": true, "missing": null}')
    review = assess(project)
    assert "prediction_drift" in codes(review)
    assert "registered 0.25" in review["predictions"][0]["drift"]


def test_incomplete_denominator_fails_numerical_consistency(project):
    (project.root / "record.json").write_text('{"trials": 100, "successes": 99, "failures": 0}')
    project.catalog["artifacts"].append({"id": "record", "path": "record.json", "class": "simulated", "format": "json",
                                         "description": "Run record"})
    project.catalog["consistency"].append({
        "id": "K-1", "claims": ["C1"], "description": "Denominator", "tolerance": 0,
        "left": {"artifact": "record", "json": ["/successes", "/failures"], "reduce": "sum"},
        "right": {"artifact": "record", "json": "/trials"}})
    assert "consistency_failed" in codes(assess(project))


# ----------------------------------------------------------------- execution and reproduction records

@pytest.mark.parametrize("status,expected", [(" />", "satisfied"), ("><skipped/></testcase>", "not_evaluated"),
                                             ("><failure/></testcase>", "not_satisfied")])
def test_execution_record_scopes_software_claims(project, tmp_path, status, expected):
    project.records["requirements.json"]["requirements"].append({
        "id": "R-2", "claims": ["C1"], "check": "test", "text": "Tests pass.", "source": "Fixture",
        "tests_required": ["test_model::test_value"], "assumptions": [], "implementation": [], "tests": ["tests"]})
    project.claim["requirements"].append("R-2")
    if expected == "not_satisfied":
        project.claim["status"] = "contradicted"
    record = tmp_path / "junit.xml"
    record.write_text(JUNIT.format(status=status))
    review = assess(project, execution_record=record)
    result = {r["id"]: r for r in review["requirements"]}["R-2"]
    assert result["result"] == expected
    assert review["claims"][0]["support"] == ("software" if expected == "satisfied" else "model")
    scope = {s["id"]: s for s in review["scopes"]}["software_tests"]
    assert "SOFTWARE TESTS" in scope["text"] and scope["state"] in ("passed", "failed")


def test_execution_record_with_entities_is_refused(project, tmp_path):
    record = tmp_path / "junit.xml"
    record.write_text('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><testsuites>&a;</testsuites>')
    with pytest.raises(EvidenceError, match="DTD"):
        assess(project, execution_record=record)


def test_reproduction_detects_a_committed_output_that_the_model_does_not_produce(project):
    project.save()
    assert [r["result"] for r in reproduce(project.root, catalog_path="catalog.json")["results"]] == ["reproduced"]
    (project.root / "out.json").write_text('{"value": 0.2500001, "flag": true, "missing": null}')
    rows = reproduce(project.root, catalog_path="catalog.json")["results"]
    assert rows[0]["result"] == "differs" and "/value" in rows[0]["detail"]


def test_attached_reproduction_record_goes_stale_when_artifacts_change(project, tmp_path):
    project.save()
    record = tmp_path / "repro.json"
    record.write_bytes(canonical_json(reproduce(project.root, catalog_path="catalog.json")))
    assert {s["id"]: s["state"] for s in assess(project, reproduction_record=record)["scopes"]}["model_reproduction"] == "passed"
    (project.root / "out.json").write_text('{"value": 0.25, "flag": true, "missing": null} ')
    assert {s["id"]: s["state"] for s in assess(project, reproduction_record=record)["scopes"]}["model_reproduction"] == "stale"


# ----------------------------------------------------------------- archive and reviews

def test_archived_history_cannot_be_edited(project):
    (project.root / "archive").mkdir(exist_ok=True)
    (project.root / "archive/old.json").write_text('{"value": 0.9}')
    project.records["archive/index.json"]["entries"].append({
        "path": "archive/old.json", "original_path": "out.json", "sha256": digest(b'{"value": 0.9}'),
        "kind": "superseded_model_output", "archived": "2026-01-01", "reason": "Superseded", "discrepancies": [],
        "superseded_by": "out"})
    project.save()
    R.load(project.root, "catalog.json")
    (project.root / "archive/old.json").write_text('{"value": 0.25}')
    with pytest.raises(EvidenceError, match="append-only"):
        R.load(project.root, "catalog.json")


def test_superseded_artifacts_cannot_be_cited_as_current(project):
    project.catalog["artifacts"][1]["status"] = "superseded"
    with pytest.raises(EvidenceError):
        assess(project)


def test_tooling_cannot_record_an_independent_review(project):
    project.save()
    with pytest.raises(EvidenceError, match="named human"):
        snapshot(project.root, ["C1"], "note", catalog_path="catalog.json", independent=True)
    result = snapshot(project.root, ["C1"], "note", catalog_path="catalog.json")
    assert result["kind"] == "snapshot"
    stored = json.loads((project.root / "reviews.json").read_text())["reviews"]["C1"]["current"]
    assert stored["recorded_by"].startswith("tooling snapshot")


def test_snapshot_history_is_kept(project):
    snap(project, "first")
    snap(project, "second")
    entry = json.loads((project.root / "reviews.json").read_text())["reviews"]["C1"]
    assert entry["current"]["note"] == "second" and entry["history"][0]["note"] == "first"


def test_impact_lists_claims_checks_and_stale_docs(project):
    project.save()
    records = R.load(project.root, "catalog.json")
    result = E.impact(records, ["model.py", "unrelated.txt"])
    assert result[0]["derived_artifacts"] == ["out"]
    assert result[0]["claims"] == ["C1"] and result[0]["requirements"] == ["R-1"] and result[0]["predictions"] == ["P-1"]
    assert "docs/claims/C1.md" in result[0]["stale_generated_docs"]
    assert any("reproduce --only model" in step for step in result[0]["rerun"])
    assert result[1]["tracked"] is False


# ----------------------------------------------------------------- sessions

def _session(tmp_path, *, metadata=None, declaration=None):
    folder = tmp_path / "bench_20260101_000000"
    folder.mkdir()
    (folder / "telemetry.csv").write_text(
        "received_at_iso,source,message_type,time_ms,roll_deg,rate_deg_s,servo_output,raw\n"
        '2026-01-01T00:00:00.000+00:00,udp,T,0,0.1,0.0,0,"T,0"\n'
        '2026-01-01T00:00:00.050+00:00,udp,T,50,0.2,0.0,0,"T,50"\n')
    if metadata is not None:
        (folder / "session.json").write_text(json.dumps(metadata))
    if declaration is not None:
        S.declare(folder, declaration)
    return folder


def test_session_without_metadata_or_declaration_is_only_audited(tmp_path):
    document, audit, _ = S.passport(_session(tmp_path))
    found = {w["code"] for w in document["warnings"]}
    assert document["stage"] == "audited"
    assert {"no_declaration", "origin_not_bench", "session_metadata_missing", "firmware_revision_not_recorded",
            "calibration_not_recorded"} <= found
    assert document["versions"]["firmware_commit"] == "NOT RECORDED"
    assert audit["origin"] == "unknown"


def test_partial_capture_and_version_mismatch_are_flagged(tmp_path):
    metadata = {"closed_cleanly": False, "dashboard": {"sha256": "0" * 64}, "protocol": {"sha256": "1" * 64}}
    document, _, _ = S.passport(_session(tmp_path, metadata=metadata), root=ROOT)
    found = {w["code"] for w in document["warnings"]}
    assert {"capture_not_closed", "dashboard_revision_mismatch", "protocol_revision_mismatch"} <= found
    assert document["versions"]["dashboard_matches_current_checkout"] is False


def test_synthetic_declaration_never_becomes_a_review_candidate(tmp_path):
    folder = _session(tmp_path, metadata={"closed_cleanly": True},
                      declaration={"operator": "A", "origin": "synthetic", "purpose": "p", "inert_configuration": "inert"})
    assert S.passport(folder)[0]["stage"] == "audited"


def test_declarations_are_not_rewritten(tmp_path):
    folder = _session(tmp_path, declaration={"operator": "A", "origin": "bench"})
    with pytest.raises(EvidenceError, match="already exists"):
        S.declare(folder, {"operator": "B", "origin": "bench"})


def test_session_ingestion_requires_a_named_human(project, tmp_path):
    folder = _session(tmp_path, metadata={"closed_cleanly": True},
                      declaration={"operator": "A. Operator", "origin": "bench", "purpose": "Timing", "tests": ["timing"],
                                   "inert_configuration": "No energetics; ignition servo disconnected"})
    project.save()
    S.build_passport(folder, tmp_path / "passport", root=project.root)
    entry = S.register(tmp_path / "passport", project.root, catalog_path="catalog.json")
    assert entry["stage"] == "review_candidate"
    with pytest.raises(EvidenceError, match="reviewer"):
        S.accept(project.root, entry["id"], "  ", catalog_path="catalog.json")
    accepted = S.accept(project.root, entry["id"], "A. Reviewer", catalog_path="catalog.json", today="2026-02-01")
    assert accepted["stage"] == "human_accepted" and accepted["accepted_by"] == "A. Reviewer"
    with pytest.raises(EvidenceError, match="Only a review candidate"):
        S.accept(project.root, entry["id"], "Someone Else", catalog_path="catalog.json")
    # The raw bytes in the record are the passport's bytes.
    stored = project.root / f"evidence/sessions/{entry['id']}/telemetry.csv"
    assert stored.read_bytes() == (folder / "telemetry.csv").read_bytes()
