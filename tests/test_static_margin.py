import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Simulation'))
import static_margin
import pytest
import csv
import json


def test_default_geometry_produces_physically_ordered_outputs(tmp_path):
    csv_path = tmp_path / "sm.csv"
    plot_path = tmp_path / "sm.png"
    static_margin.generate_reports(str(csv_path), str(plot_path))

    assert csv_path.exists()

    sm_vals, cg_vals, cp_vals = [], [], []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sm_vals.append(float(row['sm_calibers']))
            cg_vals.append(float(row['cg_m']))
            cp_vals.append(float(row['cp_m']))

    assert sm_vals
    # Motor burnout removes aft mass, so CG moves forward (decreases).
    for i in range(1, len(cg_vals)):
        assert cg_vals[i] <= cg_vals[i - 1]
    # CP is aft of CG at every sample.
    for cp, cg in zip(cp_vals, cg_vals):
        assert cp > cg


def test_ork_run_reproduces_committed_outputs(tmp_path):
    csv_path = tmp_path / "C5_static_margin.csv"
    ork_path = ROOT / "Simulation" / "Folding Stabilized Rocket.ork"
    static_margin.generate_reports(str(csv_path), str(tmp_path / "sm.png"), str(ork_path))
    committed = ROOT / "docs" / "EVIDENCE"
    assert csv_path.read_bytes() == (committed / "C5_static_margin.csv").read_bytes()
    produced = json.loads((tmp_path / "C5_static_margin_inputs.json").read_text())
    expected = json.loads((committed / "C5_static_margin_inputs.json").read_text())
    assert produced == expected
    assert produced["motor"]["designation"] == "G64W"
    assert produced["design_point_revision"] == "2026-11-14-phase1"


def test_ork_parser_extracts_real_geometry():
    ork_path = ROOT / "Simulation" / "Folding Stabilized Rocket.ork"
    geom = static_margin.parse_ork(str(ork_path))

    # 3-inch (76.2 mm) body, 38.1 mm ellipsoid nose
    assert abs(geom['d_ref'] - 0.0762) < 0.001
    assert abs(geom['L_n'] - 0.0381) < 0.001
    assert geom['ork_nose_shape'] == 'ellipsoid'
    assert geom['ork_motor'] == 'G64W'

    # Both the canard set and the (resized) main fin set are parsed.
    assert len(geom['finsets']) == 2
    main = max(geom['finsets'], key=lambda f: f['rootchord'])
    assert abs(main['rootchord'] - 0.160) < 0.001, f"main C_R={main['rootchord']} — expected 0.160 (militarized resize)"
    assert abs(main['height'] - 0.220) < 0.001, f"main span={main['height']} — expected 0.220"
    canard = min(geom['finsets'], key=lambda f: f['rootchord'])
    assert abs(canard['rootchord'] - 0.0254) < 0.001


def test_nose_cp_fraction_matches_published_values():
    # The derivation is validated against the published Barrowman table.
    assert static_margin.nose_cp_fraction('cone') == pytest.approx(2 / 3, abs=1e-3)
    assert static_margin.nose_cp_fraction('ogive') == pytest.approx(0.466, abs=1e-6)
    # The rocket's ellipsoid nose: derived by the same weighting.
    assert static_margin.nose_cp_fraction('ellipsoid') == pytest.approx(1 / 3, abs=2e-3)


def test_fin_terms_are_the_textbook_form():
    # Rectangular fin: CP must land on the quarter chord, which is the
    # textbook result the revision-2 script got wrong (it used the root chord
    # in the sweep term and the sweep length in the normal-force term).
    cn, x = static_margin.fin_terms(0.440, 0.160, 0.160, 0.220, 0.0,
                                     0.0381, 0.0762, 4)
    assert x == pytest.approx(0.440 + 0.160 / 4, abs=1e-9)
    assert cn > 0


def test_static_margin_stays_in_the_required_window():
    # Requirement R-C5-WINDOW is evaluated by the evidence record; this test
    # documents the Phase 1 gate for the militarized design point and fails
    # loudly if a design change breaks it.
    ork_path = ROOT / "Simulation" / "Folding Stabilized Rocket.ork"
    record = static_margin.generate_reports(
        str(ROOT / "docs" / "EVIDENCE" / "C5_static_margin.csv"),
        str(ROOT / "docs" / "EVIDENCE" / "C5_static_margin.png"), str(ork_path))
    assert 1.5 <= record['sm_min_calibers']
    assert record['sm_max_calibers'] <= 2.0
