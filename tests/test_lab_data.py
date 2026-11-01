"""Provenance checks for the Living Engineering Laboratory (lab/).

The laboratory may only display values derived from committed sources. These tests fail if a
derived view is stale, if the OpenRocket placement semantics regress, if the CAD view stops
matching the recorded linkage, or if a vendored library changes without its recorded digest.
"""

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "lab"


def _json(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_every_derived_view_is_current_and_inputs_are_pinned():
    result = subprocess.run([sys.executable, "tools/export_lab_data.py", "--check"], cwd=ROOT,
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_evidence_view_is_the_assessment_without_provenance():
    view = _json("lab/data/evidence.json")
    assert "provenance" not in view
    assert view["counts"]["accepted_physical_measurements"] == 0
    assert {c["id"] for c in view["claims"]} == {f"C{i}" for i in range(1, 9)}
    assert view["inputs"], "the view must pin its input digests"


def test_openrocket_stations_follow_axial_method_semantics():
    rocket = _json("lab/data/openrocket.json")["current"]
    assert rocket["overall_length_m"] == 0.601
    fins = [c for c in rocket["components"] if c["kind"] == "trapezoidfinset"]
    forward = next(f for f in fins if f["axial_method"] == "absolute")
    aft = next(f for f in fins if f["axial_method"] == "bottom")
    assert forward["x_start_m"] == 0.18
    # 'bottom' aligns the fin set's aft end with the parent tube's aft end: 0.601 - 0.130.
    assert abs(aft["x_start_m"] - 0.471) < 1e-9 and abs(aft["x_end_m"] - 0.601) < 1e-9


def test_lab_observation_is_flagged_as_unreviewed_candidate():
    obs = _json("lab/data/openrocket.json")["lab_observations"][0]
    assert "not entered in the discrepancy register" in obs["status"]
    ids = {d["id"] for d in _json("evidence/discrepancies.json")["discrepancies"]}
    assert obs["id"] not in ids


def test_step_view_matches_recorded_linkage_and_source_digest():
    view = _json("lab/data/cad/four_bar.json")
    step = (ROOT / view["source"]).read_bytes()
    assert hashlib.sha256(step).hexdigest() == view["source_sha256"]
    spacing = {p["role"]: p["pin_spacing_mm_brep"] for p in view["parts"]}
    assert spacing == {"ground": 25.0, "input": 15.0, "coupler": 60.0, "output": 15.0}


def test_fusion_archives_are_inventoried_not_presented_as_translated():
    archives = _json("lab/data/cad/archives.json")["archives"]
    assert {a["path"] for a in archives} == {"CAD Files/Folding Rocket.f3z", "CAD Files/Launcher Platform.f3z",
                                             "CAD Files/Rocket Nozzle.f3z"}
    assert all(a["translation"]["status"] == "NOT TRANSLATED" for a in archives)


def test_vendored_bundle_matches_recorded_digest():
    readme = (LAB / "lib/README.md").read_text(encoding="utf-8")
    recorded = re.search(r"`three-lab\.min\.js`.*?`([0-9a-f]{64})`", readme).group(1)
    actual = hashlib.sha256((LAB / "lib/three-lab.min.js").read_bytes()).hexdigest()
    assert actual == recorded


def test_manual_scan_is_not_published():
    names = {p.name.lower() for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts}
    assert not any("f-117" in n or "nighthawk" in n or n.endswith("1f-117a-1a.pdf") for n in names)
