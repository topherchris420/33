import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'materials'))
import mass_rollup
import pytest

def test_mass_reduction_within_claim():
    yaml_path = Path(__file__).resolve().parents[1] / "materials" / "parts.yaml"
    parts = mass_rollup.load_parts(yaml_path)
    b_data, o_data, b_mass, o_mass = mass_rollup.generate_rollup(parts)
    
    delta_pct = (b_mass - o_mass) / b_mass
    
    assert 0.30 <= delta_pct <= 0.40, f"Mass reduction {delta_pct*100:.1f}% not in [30%, 40%]"

def test_densities_within_bounds():
    # CFRP density is typically 1500-1600
    assert 1500 <= mass_rollup.DENSITIES['CFRP_quasi_iso'] <= 1600
    # Ti-6Al-4V is around 4430
    assert 4400 <= mass_rollup.DENSITIES['Ti-6Al-4V'] <= 4500
    # 7075-T6 is around 2810
    assert 2750 <= mass_rollup.DENSITIES['7075-T6'] <= 2850
    
def test_no_negative_volumes_or_masses():
    yaml_path = Path(__file__).resolve().parents[1] / "materials" / "parts.yaml"
    parts = mass_rollup.load_parts(yaml_path)
    b_data, o_data, b_mass, o_mass = mass_rollup.generate_rollup(parts)
    
    assert b_mass > 0
    assert o_mass > 0
    
    for b in b_data:
        assert b['mass_kg'] > 0
    for o in o_data:
        assert o['mass_kg'] > 0
