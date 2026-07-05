import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mechanism'))
import four_bar
import pytest
import json
import math

def test_grashof_crank_rocker():
    # Classic crank-rocker: shortest + longest <= sum of others
    assert four_bar.grashof_condition(40, 20, 30, 35) == 'Grashof'

def test_grashof_non_grashof():
    # All links similar length -> non-Grashof
    assert four_bar.grashof_condition(30, 30, 30, 30.1) == 'non-Grashof'

def test_grashof_change_point():
    assert four_bar.grashof_condition(30, 20, 30, 20) == 'change-point'

def test_over_center_lock_detection():
    # At toggle angle, moment should be 0; past it, positive
    sign_before = four_bar.over_center_moment_sign(25, 60, 15, 15, 80.0, theta_toggle=92.0)
    sign_at = four_bar.over_center_moment_sign(25, 60, 15, 15, 92.0, theta_toggle=92.0)
    sign_after = four_bar.over_center_moment_sign(25, 60, 15, 15, 95.0, theta_toggle=92.0)
    assert sign_before == -1
    assert sign_at == 0
    assert sign_after == 1

def test_swept_envelope_within_body_radius():
    body_radius = 40.0  # mm, approximate rocket body radius
    tip_x, tip_y = four_bar.tip_trajectory(25, 60, 15, 15, 0.0, 92.0)
    envelope = four_bar.swept_envelope_radius(tip_x, tip_y)
    assert envelope <= body_radius * 2.5, f'Envelope {envelope:.1f} exceeds 2.5x body radius'

def test_transmission_angle_in_deployment_range():
    # Transmission angle should be between 40° and 140° throughout deployment
    for theta in range(0, 93, 5):
        mu = four_bar.transmission_angle(25, 60, 15, 15, float(theta))
        assert 40.0 <= mu <= 140.0, f'Transmission angle {mu:.1f}° at θ={theta}° out of [40,140]'

def test_parameter_study_emits_json(tmp_path):
    output = tmp_path / 'sweep.json'
    four_bar.parameter_study(str(output))
    assert output.exists()
    data = json.loads(output.read_text())
    assert len(data) > 0
    assert 'grashof' in data[0]
