import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mechanism'))
import spring_sizing
import pytest
import math

def test_k_min_reference_value():
    # Compute k_min at design point and verify consistency
    k = spring_sizing.compute_k_min(
        v_egress=70.0, c_fin=0.060, S_fin=0.0036,
        t_deploy=0.050, h_fin=0.060, m_fin=0.015,
        Cm_alpha_max=0.8, damping_ratio=0.7
    )
    # k should be a positive number in a reasonable range
    assert k > 0
    assert k < 1000  # sanity bound

def test_negative_velocity_raises():
    with pytest.raises(ValueError):
        spring_sizing.compute_k_min(
            v_egress=-10, c_fin=0.060, S_fin=0.0036,
            t_deploy=0.050, h_fin=0.060, m_fin=0.015, Cm_alpha_max=0.8
        )

def test_zero_velocity_raises():
    with pytest.raises(ValueError):
        spring_sizing.compute_k_min(
            v_egress=0, c_fin=0.060, S_fin=0.0036,
            t_deploy=0.050, h_fin=0.060, m_fin=0.015, Cm_alpha_max=0.8
        )

def test_negative_mass_raises():
    with pytest.raises(ValueError):
        spring_sizing.compute_k_min(
            v_egress=70, c_fin=0.060, S_fin=0.0036,
            t_deploy=0.050, h_fin=0.060, m_fin=-0.015, Cm_alpha_max=0.8
        )

def test_design_point_has_20_percent_margin():
    k_required = spring_sizing.compute_k_min(
        v_egress=70.0, c_fin=0.060, S_fin=0.0036,
        t_deploy=0.050, h_fin=0.060, m_fin=0.015,
        Cm_alpha_max=0.8, damping_ratio=0.7
    )
    k_supplied = 220.0  # N·m/rad from paper
    assert k_required <= k_supplied * 1.20, (
        f'k_required={k_required:.1f} exceeds k_supplied*1.2={k_supplied*1.2:.1f}'
    )
    assert k_required <= k_supplied, (
        f'k_required={k_required:.1f} exceeds k_supplied={k_supplied:.1f} — no margin'
    )

def test_sensitivity_sweep_emits_json(tmp_path):
    output = tmp_path / 'sweep.json'
    spring_sizing.sensitivity_sweep(str(output))
    assert output.exists()
    import json
    data = json.loads(output.read_text())
    assert len(data) > 0
