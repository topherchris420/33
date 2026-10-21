"""Synthetic metadata fixtures exercise review gates; no physical evidence is made."""

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from evidence import bench
from evidence.__main__ import main
from evidence.bundle import verify_bundle
from evidence.common import EvidenceError, canonical_json, digest, load_json


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "project"
    for path in ("evidence/catalog.json", "evidence/preregistrations.json", "evidence/fixture.py",
                 "specimen-design.txt", "Firmware/Rocket/src/main.cpp", "Firmware/Launcher/src/wifi_config.h"):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("SOFTWARE TEST FIXTURE ONLY\n", encoding="utf-8")
    records = SimpleNamespace(
        raw={"catalog": ("evidence/catalog.json", b"fixture"),
             "preregistrations": ("evidence/preregistrations.json", b"fixture")},
        artifacts={"drawing": {"path": "specimen-design.txt"}},
        preregistrations={key: {"status": "registered", "registered_on": "2000-01-01",
                               "question": "SYNTHETIC UNIT TEST ONLY", "interpretation_rule": "No real result"}
                          for key in bench.PROFILES},
    )
    monkeypatch.setattr(bench.R, "load", lambda *args, **kwargs: records)
    return root, records


def save(path, document):
    path.write_bytes(canonical_json(document))


def complete_case(project, tmp_path):
    root, _ = project
    directory = tmp_path / "plan"
    plan = bench.create_plan(root, directory)
    plan.update(created_utc="2000-01-02T00:00:00+00:00", hardware_revision="UNIT-TEST-REV")
    plan["specimen"] = {"id": "UNIT-TEST-SPECIMEN", "description": "Synthetic metadata fixture, not hardware"}
    for item in plan["installed_firmware"]:
        item["sha256"] = "a" * 64
    for item in plan["observables"]:
        item.update(conditions="Unit test only", method="Validate metadata structure only")
        item["interpretation"].update(rule="No physical performance evaluated", criterion_source="Unit test fixture")
    plan_path = directory / "plan.json"
    save(plan_path, plan)
    capture_dir = tmp_path / "capture"
    capture = bench.create_observation_template(plan_path, capture_dir)
    capture.update(origin="bench", operator="SOFTWARE TEST FIXTURE", captured_utc="2000-01-03T00:00:00+00:00",
                   hardware_revision=plan["hardware_revision"], specimen_id=plan["specimen"]["id"],
                   installed_firmware=deepcopy(plan["installed_firmware"]))
    raw = b"fixture,value\nsynthetic-unit-test,0.5\n"
    cal = b"UNIT TEST ONLY; NOT A REAL CALIBRATION CERTIFICATE\n"
    (capture_dir / "samples.csv").write_bytes(raw)
    (capture_dir / "calibration.txt").write_bytes(cal)
    for item in capture["observations"]:
        item.update(value=0.5, uncertainty=0.1, timebase="TEST-ONLY-CLOCK",
                    raw_file={"path": "samples.csv", "sha256": digest(raw)})
        if item["source_kind"] == "independent_instrument":
            item["instrument"] = {"id": "TEST-ONLY-INSTRUMENT", "calibrated_on": "2000-01-01", "valid_until": "2000-12-31",
                                  "calibration_file": {"path": "calibration.txt", "sha256": digest(cal)}}
    capture_path = capture_dir / "observations.json"
    save(capture_path, capture)
    return root, plan_path, plan, capture_path, capture


def codes(report):
    return {f["code"] for f in report["findings"]}


def test_drafts_contain_unknowns_and_never_invent_observations(project, tmp_path):
    root, records = project
    records.preregistrations["P-001"]["status"] = "proposed"
    plan_dir = tmp_path / "draft"
    plan = bench.create_plan(root, plan_dir)
    assert plan["hardware_revision"] is None and plan["specimen"]["id"] is None
    assert not any(p["path"].endswith("wifi_config.h") for p in plan["source_snapshot"])
    capture = bench.create_observation_template(plan_dir / "plan.json", tmp_path / "empty")
    assert capture["origin"] == "unknown"
    assert all(row["value"] is None and row["uncertainty"] is None for row in capture["observations"])
    report, _ = bench.assess_plan(root, plan_dir / "plan.json", tmp_path / "empty/observations.json")
    assert {"not_recorded", "origin_not_bench", "preregistration_not_registered"} <= codes(report)
    assert report["stage"] == "blocked"
    with pytest.raises(EvidenceError, match="already exists"):
        bench.create_plan(root, plan_dir)


def test_complete_metadata_only_becomes_a_review_candidate(project, tmp_path):
    root, plan_path, _, capture_path, _ = complete_case(project, tmp_path)
    report = bench.build_readiness(root, plan_path, tmp_path / "packet", capture_path)
    assert report["stage"] == "observation_review_candidate"
    assert report["findings"] == []
    assert report["measurement_acceptance"] == "NOT PERFORMED"
    assert report["release_authorized"] is False and report["human_signoff"] is None
    assert all(o["performance_verdict"] == "NOT EVALUATED" for o in report["observations"])
    assert verify_bundle(tmp_path / "packet")["bundle_integrity"] == "verified"
    (tmp_path / "packet/inputs/capture/samples.csv").write_bytes(b"tampered")
    with pytest.raises(EvidenceError):
        verify_bundle(tmp_path / "packet")


@pytest.mark.parametrize("change", ["source", "omitted_source", "added_source", "plan", "preregistration"])
def test_configuration_and_interpretation_cannot_drift_silently(project, tmp_path, change):
    root, plan_path, plan, capture_path, _ = complete_case(project, tmp_path)
    if change == "source":
        (root / "specimen-design.txt").write_text("changed source")
    elif change == "omitted_source":
        plan["source_snapshot"].pop()
        save(plan_path, plan)
    elif change == "added_source":
        (root / "evidence/new.py").write_text("# new source")
    elif change == "plan":
        plan["observables"][0]["method"] = "Changed after capture"
        save(plan_path, plan)
    else:
        project[1].preregistrations["P-001"]["interpretation_rule"] = "Changed after capture"
    report, _ = bench.assess_plan(root, plan_path, capture_path)
    assert codes(report) & {"configuration_drift", "plan_binding_mismatch", "preregistration_changed"}


@pytest.mark.parametrize("key,value", [("unit", "kg/m^3"), ("source_kind", "command"),
                                       ("quantity", "elastic_modulus"), ("phenomenon", "mechanical_motion")])
def test_plan_types_cannot_conflate_units_sources_or_electrical_and_mechanical_events(project, tmp_path, key, value):
    root, plan_path, plan, _, _ = complete_case(project, tmp_path)
    plan["observables"][0][key] = value
    save(plan_path, plan)
    with pytest.raises(EvidenceError):
        bench.assess_plan(root, plan_path)


@pytest.mark.parametrize("key,value", [("unit", "ms"), ("source_kind", "command"),
                                       ("quantity", "density"), ("phenomenon", "mechanical_motion")])
def test_observation_types_must_match_the_plan(project, tmp_path, key, value):
    root, plan_path, _, capture_path, capture = complete_case(project, tmp_path)
    capture["observations"][0][key] = value
    save(capture_path, capture)
    report, _ = bench.assess_plan(root, plan_path, capture_path)
    assert "observation_type_mismatch" in codes(report)


@pytest.mark.parametrize("change,expected", [
    ("synthetic", "origin_not_bench"), ("raw_synthetic", "synthetic_raw_data"),
    ("commands", "not_independent"), ("bad_digest", "attachment_mismatch"),
    ("missing_file", "attachment_missing"), ("calibration", "attachment_mismatch"),
    ("expired", "calibration_out_of_date"), ("before_plan", "plan_created_after_capture"),
    ("future", "future_timestamp"), ("late_registration", "registration_after_capture"),
    ("hardware", "specimen_mismatch"), ("firmware", "firmware_mismatch"),
    ("partial", "observation_coverage"), ("unknown_value", "not_recorded"),
])
def test_incomplete_or_misidentified_observations_remain_blocked(project, tmp_path, change, expected):
    root, plan_path, _, capture_path, capture = complete_case(project, tmp_path)
    first = capture["observations"][0]
    if change == "synthetic":
        capture["origin"] = "synthetic"
    elif change == "raw_synthetic":
        raw = b"origin,value\nsynthetic-fixture,0.5\n"
        (capture_path.parent / "samples.csv").write_bytes(raw)
        for item in capture["observations"]:
            item["raw_file"]["sha256"] = digest(raw)
    elif change == "commands":
        raw = (capture_path.parent / "samples.csv").read_bytes()
        (capture_path.parent / "commands.csv").write_bytes(raw)
        first["raw_file"]["path"] = "commands.csv"
    elif change == "bad_digest":
        first["raw_file"]["sha256"] = "b" * 64
    elif change == "missing_file":
        first["raw_file"]["path"] = "missing.csv"
    elif change == "calibration":
        first["instrument"]["calibration_file"]["sha256"] = "b" * 64
    elif change == "expired":
        first["instrument"]["valid_until"] = "2000-01-02"
    elif change == "before_plan":
        capture["captured_utc"] = "1999-12-31T00:00:00+00:00"
    elif change == "future":
        capture["captured_utc"] = "2099-12-31T00:00:00+00:00"
    elif change == "late_registration":
        project[1].preregistrations["P-001"]["registered_on"] = "2000-01-04"
    elif change == "hardware":
        capture["hardware_revision"] = "UNRELATED"
    elif change == "firmware":
        capture["installed_firmware"][0]["sha256"] = "b" * 64
    elif change == "partial":
        capture["observations"].pop()
    else:
        first["value"] = None
    save(capture_path, capture)
    report, _ = bench.assess_plan(root, plan_path, capture_path)
    assert report["stage"] == "blocked" and expected in codes(report)


@pytest.mark.parametrize("change", ["escape", "duplicate", "negative_uncertainty", "bool_value", "naive_time", "invalid_date"])
def test_malformed_inputs_fail_closed(project, tmp_path, change):
    root, plan_path, _, capture_path, capture = complete_case(project, tmp_path)
    first = capture["observations"][0]
    if change == "escape":
        first["raw_file"]["path"] = "../outside.csv"
    elif change == "duplicate":
        capture["observations"].append(deepcopy(first))
    elif change == "negative_uncertainty":
        first["uncertainty"] = -0.1
    elif change == "bool_value":
        first["value"] = True
    elif change == "naive_time":
        capture["captured_utc"] = "2000-01-03T00:00:00"
    else:
        first["instrument"]["calibrated_on"] = "2000-02-31"
    save(capture_path, capture)
    with pytest.raises(EvidenceError):
        bench.assess_plan(root, plan_path, capture_path)


def test_cli_produces_inspectable_blocked_report_without_altering_sources(project, tmp_path, capsys):
    root, _ = project
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    args = ["--root", str(root), "bench"]
    plan = tmp_path / "cli-plan"
    assert main([*args, "init", "--output", str(plan)]) == 0
    assert main([*args, "template", str(plan / "plan.json"), "--output", str(tmp_path / "cli-capture")]) == 0
    packet = tmp_path / "cli-review"
    assert main([*args, "check", str(plan / "plan.json"), "--output", str(packet)]) == 1
    assert load_json((packet / "readiness.json").read_bytes())["stage"] == "blocked"
    assert verify_bundle(packet)["bundle_integrity"] == "verified"
    assert {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()} == before
    assert main([*args, "init", "--output", str(plan)]) == 2
