"""C1 model correctness tests.

These check the software (geometry, honest null handling). Whether the baseline
design satisfies its requirements is evaluated by the evidence record
(evidence/requirements.json), not asserted here.
"""

import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mechanism'))
import four_bar


def test_grashof_crank_rocker():
    assert four_bar.grashof_condition(40, 20, 30, 35) == 'Grashof'


def test_grashof_non_grashof():
    assert four_bar.grashof_condition(30, 30, 30, 30.1) == 'non-Grashof'


def test_grashof_change_point():
    assert four_bar.grashof_condition(30, 20, 30, 20) == 'change-point'


@pytest.mark.parametrize("theta", [0, 30, 60, 90, 150])
def test_closure_points_satisfy_link_lengths(theta):
    a, b, c, d = 40.0, 20.0, 35.0, 30.0
    points = four_bar.closure_points(a, b, c, d, math.radians(theta))
    assert points is not None
    bx, by = b * math.cos(math.radians(theta)), b * math.sin(math.radians(theta))
    for x, y in points:
        assert math.hypot(x - bx, y - by) == pytest.approx(c)
        assert math.hypot(x - a, y) == pytest.approx(d)


def test_transmission_angle_matches_closed_pose_geometry():
    a, b, c, d = 40.0, 20.0, 35.0, 30.0
    theta = 60.0
    (x, y), _ = four_bar.closure_points(a, b, c, d, math.radians(theta))
    bx, by = b * math.cos(math.radians(theta)), b * math.sin(math.radians(theta))
    coupler = (bx - x, by - y)
    output = (a - x, -y)
    cos_mu = (coupler[0] * output[0] + coupler[1] * output[1]) / (c * d)
    assert four_bar.transmission_angle(a, c, b, d, theta) == pytest.approx(math.degrees(math.acos(cos_mu)))


def test_unassemblable_pose_has_no_values_rather_than_placeholders():
    # Coupler longer than the other three links combined: the loop can never close.
    assert four_bar.closure_points(10, 10, 100, 10, 0.5) is None
    assert four_bar.compute_theta4(10, 10, 100, 10, 0.5) is None
    assert four_bar.transmission_angle(10, 100, 10, 10, 30.0) is None
    xs, ys = four_bar.tip_trajectory(10, 100, 10, 10, 0, 92)
    assert xs == [] and ys == []
    assert four_bar.swept_envelope_radius(xs, ys) is None
    row = four_bar.evaluate_linkage(10, 100, 10, 10)
    assert row['poses_closed'] == 0
    assert row['assemblable_over_range'] is False
    assert row['min_transmission_angle'] is None
    assert row['max_envelope_radius'] is None


def test_over_center_helper_is_only_an_angle_comparison():
    # Identical result for any geometry, including one that cannot assemble:
    # this helper cannot be cited as evidence of a locking moment.
    for links in [(25, 60, 15, 15), (40, 35, 20, 30), (10, 100, 10, 10)]:
        assert four_bar.over_center_moment_sign(*links, 80.0) == -1
        assert four_bar.over_center_moment_sign(*links, 95.0) == 1


def test_parameter_study_emits_structured_result(tmp_path):
    output = tmp_path / 'sweep.json'
    result = four_bar.parameter_study(str(output))
    data = json.loads(output.read_text())
    assert data == result
    assert data['schema'] == 'project33.c1.four_bar_sweep/2'
    assert data['summary']['configurations'] == len(data['rows']) == 81
    assert 'over_center_detect' not in data['rows'][0]
    for row in data['rows']:
        if not row['assemblable_over_range']:
            assert row['poses_closed'] < row['poses_evaluated']
