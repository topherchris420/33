"""Cached simulation values must retain provenance, missingness and time scope."""

import json
from pathlib import Path
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Simulation"))
import openrocket_reference as reference
from evidence.common import digest


def make_ork(path, points=None, types=None):
    points = points or ["0,NaN,0.3,NaN", "1,0.4,0.3,1", "3,0.5,0.3,2"]
    types = types or "Time,CP location,CG location,Stability margin calibers"
    xml = ('<openrocket creator="Software test fixture" version="1.10"><simulations>'
           '<simulation status="loaded"><name>Fixture</name><flightdata>'
           f'<databranch name="Fixture" types="{types}">'
           '<event type="ignition" time="0"/><event type="burnout" time="2"/>'
           + ''.join(f'<datapoint>{p}</datapoint>' for p in points)
           + '</databranch></flightdata></simulation></simulations></openrocket>')
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("rocket.ork", xml)


def test_extract_keeps_missing_values_and_separates_burn_from_trajectory(tmp_path):
    path = tmp_path / "fixture.ork"
    make_ork(path)
    result = reference.extract(path)
    assert result["source_sha256"] == digest(path.read_bytes())
    assert result["evidence_class"] == "simulated"
    assert result["generating_geometry_sha256"] is None
    branch = result["simulations"][0]["branches"][0]
    assert branch["samples"][0]["cp_m"] is None
    assert branch["summary"]["cp_m"]["max"] == 0.5
    assert branch["burn_summary"]["cp_m"]["max"] == 0.4
    assert branch["burn_summary"]["cp_m"]["missing_samples"] == 1
    assert branch["single_motor_burn_window_s"] == [0, 2]
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("points", [["0,0.4,0.3"], ["1,0.4,0.3,1", "0,0.4,0.3,1"], ["NaN,0.4,0.3,1"]])
def test_malformed_or_unordered_cached_data_is_rejected(tmp_path, points):
    path = tmp_path / "fixture.ork"
    make_ork(path, points=points)
    with pytest.raises(ValueError):
        reference.extract(path)


def test_duplicate_or_absent_columns_are_rejected(tmp_path):
    path = tmp_path / "fixture.ork"
    make_ork(path, types="Time,CP location,CP location,CG location")
    with pytest.raises(ValueError, match="unique"):
        reference.extract(path)


def test_committed_archive_extraction_preserves_exact_file_identity():
    path = ROOT / "Simulation/Folding Stabilized Rocket.ork"
    result = reference.extract(path)
    assert result["source_sha256"] == digest(path.read_bytes())
    assert result["simulations"]
    assert any(b["samples"] for s in result["simulations"] for b in s["branches"])
