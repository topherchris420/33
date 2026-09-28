import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mechanism'))
import spring_sizing
import pytest
import math

def test_k_min_reference_value():
    # Compute k_min at design point and verify consistency
    k = spring_sizing.compute_k_min(
        v_egress=205.0, c_fin=0.120, S_fin=0.0216,
        t_deploy=0.050, h_fin=0.180, m_fin=0.154,
        Cm_alpha_max=0.8, damping_ratio=0.7
    )
    # k should be close to the paper's claimed 185 N·m/rad
    assert k > 0
    assert 180 <= k <= 200, f'k_min={k:.1f} not near paper claim of 185'

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

def test_margin_arithmetic_is_reported_not_rounded_up():
    # Revision 1 of this test was named for a 20% margin but only asserted
    # k_required <= 1.2 * k_supplied, which accepts negative margins. It is
    # preserved in evidence/archive/test_spring_sizing.v1.py.txt. Whether the
    # design point meets its stated margin is evaluated by requirement
    # R-C6-MARGIN in evidence/requirements.json, not asserted here.
    margin, meets = spring_sizing.validate_design_margin(100.0, 119.0)
    assert margin == pytest.approx(0.19)
    assert meets is False
    margin, meets = spring_sizing.validate_design_margin(100.0, 120.0)
    assert margin == pytest.approx(0.20)
    assert meets is True


def test_design_point_record_matches_direct_calculation():
    record = spring_sizing.design_point_record()
    k = spring_sizing.compute_k_min(**spring_sizing.DESIGN_POINT)
    assert record['k_min_N_m_rad'] == pytest.approx(k, abs=1e-4)
    assert record['margin_fraction'] == pytest.approx((220.0 - k) / k, abs=1e-6)
    assert record['inputs']['t_deploy'] == 0.050


def test_sensitivity_sweep_emits_json(tmp_path):
    output = tmp_path / 'sweep.json'
    spring_sizing.sensitivity_sweep(str(output))
    assert output.exists()
    import json
    data = json.loads(output.read_text())
    assert len(data) > 0
