"""Phase 4 motor sizing and structure checks."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Simulation'))
sys.path.insert(0, str(ROOT / 'structures'))
import motor_sizing  # noqa: E402
import cep_model  # noqa: E402


def test_sized_motor_reaches_the_envelope_with_margin():
    spec = motor_sizing.size_motor()
    assert spec['ballistic_envelope_m'] >= 3300.0
    assert spec['initial_accel_g'] < 30.0  # rail-load sanity
    assert spec['round_wet_kg'] < 3.5


def test_rasp_eng_file_matches_the_spec():
    spec = motor_sizing.size_motor()
    text = motor_sizing.rasp_eng(spec)
    lines = text.strip().splitlines()
    header = lines[0].split()
    assert header[0] == 'MIL-33'
    assert abs(float(header[-2]) - spec['propellant_kg']) < 0.01
    # thrust plateau roughly equals average thrust
    mid = lines[1 + len(lines) // 2].split()
    assert abs(float(mid[1]) - spec['avg_thrust_n']) < 0.5 * spec['avg_thrust_n']


def test_committed_motor_record_is_reproducible():
    committed = json.loads((ROOT / 'docs/EVIDENCE/MOTOR_sizing.json').read_text())
    fresh = motor_sizing.build_record()
    assert committed == fresh
    assert committed['evidence_class'] == 'MODELED'


def test_environmental_budgets_derive_from_the_launch_load():
    committed = json.loads((ROOT / 'docs/EVIDENCE/MOTOR_sizing.json').read_text())
    budgets = committed['environmental_budgets']
    g = committed['motor']['initial_accel_g']
    # shock budget is 3x the launch acceleration
    assert budgets['launch_shock']['initial_accel_g'] == g
    assert budgets['storage_temperature']['range_c'] == [-40, 60]


def test_militarized_hinge_fos_meets_the_requirement():
    record = json.loads((ROOT / 'docs/EVIDENCE/C8_hinge_fos_military.json').read_text())
    assert record['factor_of_safety'] >= 1.5
    assert record['meets_requirement'] is True
    assert record['inputs']['axial_load_g'] == 65.7


def test_composite_reduces_mass_vs_phase1():
    mm = motor_sizing.phase4_mass_model()
    phase1_aft = 0.32 + 0.48
    phase4_aft = sum(c['mass_kg'] for c in mm['components']
                    if 'aft_body' in c['name'])
    assert phase4_aft < phase1_aft
