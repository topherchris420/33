"""Phase 3 guidance and CEP model checks."""

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Simulation'))
import cep_model as cm


def test_pn_steers_toward_the_target():
    # Missile at origin moving east; target north of the flight path.
    # The command must accelerate TOWARD the target (north), not away.
    pos = [0.0, 0.0, 0.0]
    vel = [100.0, 0.0, 0.0]
    tgt = [1000.0, 100.0, 0.0]
    a = cm.pn_command(pos, vel, tgt, 100.0)
    assert a[1] > 0, f"PN must command northward accel, got {a}"


def test_pn_limits_to_authority():
    pos = [0.0, 0.0, 0.0]
    vel = [50.0, 0.0, 0.0]
    tgt = [50.0, 500.0, 0.0]  # nearly beam target: large LOS rate
    a = cm.pn_command(pos, vel, tgt, 9.6)
    mag = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2)
    assert mag <= 9.6 + 1e-9


def test_pn_holds_a_collision_course():
    # On an exact collision course the LOS rate is zero and PN commands zero.
    pos = [0.0, 0.0, 0.0]
    vel = [100.0, 0.0, 0.0]
    tgt = [1000.0, 0.0, 0.0]
    a = cm.pn_command(pos, vel, tgt, 9.6)
    assert all(abs(x) < 1e-9 for x in a)


def test_ballistic_impact_is_physical():
    motor = {'total_impulse_ns': 118.8, 'burn_s': 2.1, 'wet_kg': 0.151, 'dry_kg': 0.088}
    cd_a = 0.55 * math.pi * 0.0381 ** 2
    impact_30 = cm.ballistic_impact(30.0, motor, cd_a, 1.903, 1.840)
    impact_45 = cm.ballistic_impact(45.0, motor, cd_a, 1.903, 1.840)
    # Range grows with elevation on the ascending branch.
    assert impact_45 > impact_30 > 50.0
    # A hobby-class motor reaches hundreds of meters, not kilometers.
    assert impact_45 < 1500.0


def test_elevation_solve_finds_the_range_card():
    rng = np.random.default_rng(1)
    motor = {'total_impulse_ns': 800.0, 'burn_s': 2.0, 'wet_kg': 0.75, 'dry_kg': 0.35}
    cd_a = 0.55 * math.pi * 0.0381 ** 2
    m0 = 1.903 - 0.151 + 0.75
    elev, err = cm.solve_elevation(rng, motor, 2000.0, cd_a, m0, m0 - 0.40)
    impact = cm.ballistic_impact(elev, motor, cd_a, m0, m0 - 0.40)
    assert abs(impact - 2000.0) < 60.0
    assert 5.0 <= elev <= 65.0


def test_committed_record_is_reproducible():
    committed = json.loads((ROOT / 'docs/EVIDENCE/CEP_estimates.json').read_text())
    fresh = cm.build_record(trials=committed['trials'], seed=committed['seed'])
    assert committed == fresh
    assert committed['evidence_class'] == 'MODELED'


def test_guided_beats_ballistic_at_long_range():
    committed = json.loads((ROOT / 'docs/EVIDENCE/CEP_estimates.json').read_text())
    p4 = committed['PHASE4_MOTOR']['results']
    assert p4['2000_m']['cep_guided_m'] < p4['2000_m']['cep_ballistic_m']
    assert p4['3000_m']['cep_guided_m'] < p4['3000_m']['cep_ballistic_m']
