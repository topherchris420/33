import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'structures'))
import fea_lite
import pytest

def test_clt_stiffness():
    Ex, Ey, Gxy = fea_lite.compute_clt_properties()
    # Typical quasi-isotropic CFRP has Ex in 50-70 GPa range
    assert 50 <= Ex <= 70
    assert 50 <= Ey <= 70

def test_hinge_pin_fos():
    fos, vm, tau, sig = fea_lite.compute_hinge_fos()
    # F.S. >= 1.5
    assert fos >= 1.5
    # Should be near paper's claimed 1.88 with the aligned parameters
    assert 1.5 <= fos <= 3.0, f'FoS={fos:.2f} outside expected range [1.5, 3.0]'
