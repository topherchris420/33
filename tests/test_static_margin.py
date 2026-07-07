import sys
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Simulation'))
import static_margin
import pytest
import csv

def test_static_margin_in_window(tmp_path):
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
            
    sm_min = min(sm_vals)
    sm_max = max(sm_vals)
    
    assert 1.5 <= sm_min <= 2.0, f"Min SM {sm_min} not in [1.5, 2.0]"
    assert 1.5 <= sm_max <= 2.0, f"Max SM {sm_max} not in [1.5, 2.0]"
    
    # Assert monotonic mass decrease -> cg moves forward (decreases value)
    for i in range(1, len(cg_vals)):
        assert cg_vals[i] <= cg_vals[i-1]
        
    # Assert CP is aft of CG
    for cp, cg in zip(cp_vals, cg_vals):
        assert cp > cg

def test_static_margin_with_ork(tmp_path):
    csv_path = tmp_path / "sm_ork.csv"
    plot_path = tmp_path / "sm_ork.png"
    ork_path = ROOT / "Simulation" / "Folding Stabilized Rocket.ork"
    
    static_margin.generate_reports(str(csv_path), str(plot_path), str(ork_path))
    
    assert csv_path.exists()
    
    sm_vals = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sm_vals.append(float(row['sm_calibers']))
            
    sm_min = min(sm_vals)
    sm_max = max(sm_vals)
    
    # With the updated .ork fin geometry (C_R=130mm, C_T=110mm, S=180mm),
    # the static margin should now be within the paper's claimed [1.5, 2.0] window
    assert 1.0 <= sm_min, f"SM_min={sm_min:.2f} too low — expected >= 1.0"
    assert sm_max <= 2.5, f"SM_max={sm_max:.2f} too high — expected <= 2.5"
    assert len(sm_vals) > 0


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
