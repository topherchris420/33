import sys
import numpy as np
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
    
    sm_vals = []
    cg_vals = []
    cp_vals = []
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sm_vals.append(float(row['sm_calibers']))
            cg_vals.append(float(row['cg_m']))
            cp_vals.append(float(row['cp_m']))
            
    # Built-in defaults are not the modeled rocket; no window is asserted here.
    assert sm_vals
    # Assert monotonic mass decrease -> cg moves forward (decreases value)
    for i in range(1, len(cg_vals)):
        assert cg_vals[i] <= cg_vals[i-1]
        
    # Assert CP is aft of CG
    for cp, cg in zip(cp_vals, cg_vals):
        assert cp > cg

def test_ork_run_reproduces_committed_outputs(tmp_path):
    # Requirement R-C5-WINDOW (1.5-2.0 cal) is evaluated by the evidence record,
    # together with the textbook cross-check that disagrees with this model.
    csv_path = tmp_path / "C5_static_margin.csv"
    ork_path = ROOT / "Simulation" / "Folding Stabilized Rocket.ork"
    static_margin.generate_reports(str(csv_path), str(tmp_path / "sm.png"), str(ork_path))
    committed = ROOT / "docs" / "EVIDENCE"
    assert csv_path.read_bytes() == (committed / "C5_static_margin.csv").read_bytes()
    produced = json.loads((tmp_path / "C5_static_margin_inputs.json").read_text())
    expected = json.loads((committed / "C5_static_margin_inputs.json").read_text())
    assert produced == expected
    assert produced["ork_motor_designation"] == "G64W"


def test_ork_parser_extracts_real_geometry():
    """Verify parse_ork() doesn't silently fall back to defaults."""
    ork_path = ROOT / "Simulation" / "Folding Stabilized Rocket.ork"
    geom = static_margin.parse_ork(str(ork_path))
    
    # The .ork has a 3-inch (76.2mm) body tube, not the 40mm default
    assert abs(geom['d_ref'] - 0.0762) < 0.001, f"d_ref={geom['d_ref']} — expected ~0.0762"
    
    # Nose cone is 38.1mm, not the 100mm default
    assert abs(geom['L_n'] - 0.0381) < 0.001, f"L_n={geom['L_n']} — expected ~0.0381"
    
    # Total dry mass should be sum of both body tubes' override masses
    assert geom['m_dry'] > 1.0, f"m_dry={geom['m_dry']} — expected >1.0 (sum of two body tubes)"
    
    # X_f should be well past the nose (absolute position from nose tip)
    assert geom['X_f'] > 0.30, f"X_f={geom['X_f']} — expected >0.30m from nose"
    
    # Fin dimensions should match the updated .ork (C_R=130mm, C_T=110mm, S=180mm)
    assert abs(geom['C_R'] - 0.130) < 0.01, f"C_R={geom['C_R']} — expected ~0.130"
    assert abs(geom['S'] - 0.180) < 0.01, f"S={geom['S']} — expected ~0.180"
