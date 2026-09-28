"""C4 model regression checks.

Whether the calculated reduction meets the 30-40% target is evaluated by
requirement R-C4-REDUCTION in the evidence record, not asserted by CI.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'materials'))
import mass_rollup


def _rollup():
    parts = mass_rollup.load_parts(ROOT / "materials" / "parts.yaml")
    return parts, mass_rollup.generate_rollup(parts)


def test_rollup_reproduces_committed_summary():
    parts, (_, _, b_mass, o_mass) = _rollup()
    committed = json.loads((ROOT / "docs/EVIDENCE/C4_mass_summary.json").read_text())
    assert mass_rollup.summarize(parts, b_mass, o_mass) == committed


def test_densities_within_handbook_ranges():
    assert 1500 <= mass_rollup.DENSITIES['CFRP_quasi_iso'] <= 1600
    assert 4400 <= mass_rollup.DENSITIES['Ti-6Al-4V'] <= 4500
    assert 2750 <= mass_rollup.DENSITIES['7075-T6'] <= 2850


def test_no_negative_volumes_or_masses():
    _, (b_data, o_data, b_mass, o_mass) = _rollup()
    assert b_mass > 0 and o_mass > 0
    assert all(row['mass_kg'] > 0 for row in b_data + o_data)


def test_unknown_material_is_an_error_not_zero_mass():
    with pytest.raises(ValueError):
        mass_rollup.compute_mass(1.0, "unobtainium")
