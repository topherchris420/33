"""Phase 2 warhead model checks (all MODELED)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Simulation'))
import warheads
import pytest


@pytest.fixture(scope='module')
def record():
    ork = ROOT / 'Simulation' / 'Folding Stabilized Rocket.ork'
    return warheads.build_record(str(ork))


def test_every_loadout_holds_the_static_margin_window(record):
    assert record['static_margin_all_loadouts_in_window'] is True
    for name, v in record['static_margin_per_loadout'].items():
        assert 1.5 <= v['sm_ignition_cal'], name
        assert v['sm_burnout_cal'] <= 2.0, name


def test_constant_mass_bay_makes_loadouts_interchangeable(record):
    masses = {v['wet_mass_kg'] for v in record['static_margin_per_loadout'].values()}
    assert masses == {1.903}, masses


def test_gp_casualty_radius_is_spread_limited_not_energy_limited(record):
    gp = record['terminal_ballistics']['GP_HE_FRAG']
    assert gp['casualty_radius_m'] == gp['fragment_spread_radius_p50_m']
    assert 3.0 < gp['casualty_radius_m'] < 12.0
    assert gp['lethal_radius_energy_limit_58j_m'] > gp['casualty_radius_m']


def test_heat_penetration_band_is_defensible(record):
    heat = record['terminal_ballistics']['HEAT']
    lo, hi = heat['penetration_rha_mm']
    assert 40 <= lo < hi <= 120
    # Defeats IFV-class armor but is honestly below MBT frontal armor.
    assert lo > 30 and hi < 150


def test_gurney_velocity_scales_with_charge_to_case_ratio():
    v_low = warheads.gurney_velocity(2600.0, 0.05, 0.20)
    v_high = warheads.gurney_velocity(2600.0, 0.20, 0.05)
    assert v_low < v_high


def test_fragment_lethal_radius_increases_with_mass():
    # Heavier fragments have a smaller drag-deceleration constant
    # (k ~ rho*Cd*A/2m ~ 1/d), so at the same launch velocity they stay
    # above the energy criterion farther out.
    r_light = warheads.fragment_lethal_radius(2000.0, 0.10, 58.0)
    r_heavy = warheads.fragment_lethal_radius(2000.0, 0.50, 58.0)
    assert r_heavy > r_light


def test_committed_record_matches_model():
    committed = json.loads((ROOT / 'docs/EVIDENCE/WH_loadouts.json').read_text())
    ork = ROOT / 'Simulation' / 'Folding Stabilized Rocket.ork'
    fresh = warheads.build_record(str(ork))
    assert committed == fresh
    assert committed['evidence_class'] == 'MODELED'
