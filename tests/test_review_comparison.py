"""Regression cases for changes that do not alter a headline claim status."""

import json

import pytest

from evidence.__main__ import main
from evidence.bundle import build_review, compare_reviews, drift
from evidence.common import canonical_json, digest
from evidence.comparison import comparison_markdown
from evidence_project import Project


def build(project, destination):
    project.save()
    return build_review(project.root, destination, "catalog.json")


def test_requirement_bound_change_is_visible_even_when_both_pass(tmp_path):
    project = Project(tmp_path / "project")
    build(project, tmp_path / "before")
    project.records["requirements.json"]["requirements"][0]["bound"]["min"] = 0.21
    build(project, tmp_path / "after")
    result = compare_reviews(tmp_path / "before", tmp_path / "after")
    assert result["requirement_changes"] == []  # Preserve the original result-change API.
    assert result["affected_claims"] == ["C1"]
    detail, = result["requirement_details"]
    assert "bound" in detail["changed_fields"]
    assert detail["before"]["bound"] == {"min": 0.2}
    assert detail["after"]["bound"] == {"min": 0.21}
    assert "records/requirements.json" in result["changed_record_files"]
    markdown = comparison_markdown(result)
    assert "0.21" in markdown and "Requirement changes" in markdown


def test_record_changes_outside_evaluated_results_remain_visible(tmp_path):
    project = Project(tmp_path / "project")
    build(project, tmp_path / "before")
    project.records["predictions.json"]["predictions"][0]["measurement_method"] = "Revised method."
    build(project, tmp_path / "after")
    result = compare_reviews(tmp_path / "before", tmp_path / "after")
    assert result["changed_artifacts"] == []
    assert "records/predictions.json" in result["changed_record_files"]


@pytest.mark.parametrize("action", ["add", "remove"])
def test_drift_catalog_membership_returns_nonzero_and_maps_claims(tmp_path, capsys, action):
    project = Project(tmp_path / "project")
    build(project, tmp_path / "before")
    if action == "add":
        (project.root / "extra.txt").write_text("implementation note")
        project.catalog["artifacts"].append({"id": "extra", "path": "extra.txt", "class": "implementation",
                                              "format": "file", "description": "Additional input"})
        project.claim["evidence"].append("extra")
        key, expected = "newly_cataloged", "extra.txt"
    else:
        project.catalog["artifacts"] = [a for a in project.catalog["artifacts"] if a["id"] != "fixture"]
        project.claim["evidence"].remove("fixture")
        key, expected = "no_longer_cataloged", "sample.csv"
    project.save()
    result = drift(tmp_path / "before", project.root, "catalog.json")
    assert result[key] == [expected]
    assert result["affected_claims"] == ["C1"]
    assert main(["--root", str(project.root), "--catalog", "catalog.json",
                 "drift", str(tmp_path / "before")]) == 1
    assert json.loads(capsys.readouterr().out)[key] == [expected]


def test_compare_cli_formats_and_identical_packet(tmp_path, capsys):
    project = Project(tmp_path / "project")
    packet = tmp_path / "review"
    build(project, packet)
    assert main(["compare", str(packet), str(packet)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["requirement_details"] == result["changed_record_files"] == result["affected_claims"] == []
    assert main(["compare", str(packet), str(packet), "--format", "markdown"]) == 0
    assert "No evaluated requirement changes detected." in capsys.readouterr().out
    assert "python -m evidence verify .." in (packet / "index.html").read_text()


def test_markdown_escapes_record_text(tmp_path):
    project = Project(tmp_path / "project")
    build(project, tmp_path / "before")
    project.records["requirements.json"]["requirements"][0]["text"] = '<script>x</script> | [click](evil)\n# title'
    build(project, tmp_path / "after")
    text = comparison_markdown(compare_reviews(tmp_path / "before", tmp_path / "after"))
    assert "<script>" not in text
    assert "&lt;script&gt;" in text
    assert r"\|" in text and r"\[click\]" in text


@pytest.mark.parametrize("kind", [[], {}])
def test_invalid_manifest_kind_is_a_controlled_cli_error(tmp_path, capsys, kind):
    project = Project(tmp_path / "project")
    packet = tmp_path / "review"
    build(project, packet)
    manifest = json.loads((packet / "manifest.json").read_bytes())
    manifest["kind"] = kind
    data = canonical_json(manifest)
    (packet / "manifest.json").write_bytes(data)
    (packet / "manifest.sha256").write_text(digest(data) + "\n")
    assert main(["verify", str(packet)]) == 2
    assert "Unknown manifest kind" in capsys.readouterr().err
