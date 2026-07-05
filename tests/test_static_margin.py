import sys
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Simulation'))
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
