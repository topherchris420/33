"""C8 calculation checks. Requirement outcomes live in the evidence record."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'structures'))
import fea_lite


def test_quasi_isotropic_laminate_is_in_plane_isotropic():
    Ex, Ey, Gxy = fea_lite.compute_clt_properties()
    assert Ex == pytest.approx(Ey, rel=1e-9)
    # For an in-plane isotropic laminate G = E / (2 (1 + nu)) with 0 < nu < 0.5.
    assert Ex / 3 < Gxy < Ex / 2


def test_hinge_record_reproduces_committed_values(tmp_path):
    fea_lite.generate_reports(tmp_path / "clt.csv", tmp_path / "fos.json")
    assert json.loads((tmp_path / "fos.json").read_text()) == \
        json.loads((ROOT / "docs/EVIDENCE/C8_hinge_fos.json").read_text())
    assert (tmp_path / "clt.csv").read_bytes() == (ROOT / "docs/EVIDENCE/C8_clt.csv").read_bytes()
