import importlib.util
from types import SimpleNamespace
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_generator():
    path = ROOT / "CAD Files" / "naca_fin_generator.py"
    spec = importlib.util.spec_from_file_location("naca_fin_generator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_naca_generator_scales_x_coordinates_to_configured_chord():
    generator = _load_generator()

    upper, lower = generator.naca_4digit_coordinates(
        m=0.0,
        p=0.0,
        t=0.12,
        c=0.060,
        num_points=10,
    )

    assert upper[0][0] == pytest.approx(0.0)
    assert lower[0][0] == pytest.approx(0.0)
    assert upper[-1][0] == pytest.approx(60.0)
    assert lower[-1][0] == pytest.approx(60.0)


def test_naca_0012_coordinates_are_symmetric_about_chord_line():
    generator = _load_generator()

    upper, lower = generator.naca_4digit_coordinates(
        m=0.0,
        p=0.0,
        t=0.12,
        c=0.060,
        num_points=20,
    )

    for upper_point, lower_point in zip(upper, lower):
        assert upper_point[0] == pytest.approx(lower_point[0])
        assert upper_point[1] == pytest.approx(-lower_point[1])


def test_naca_generator_rejects_invalid_geometry_inputs():
    generator = _load_generator()

    with pytest.raises(ValueError):
        generator.naca_4digit_coordinates(0.0, 0.0, 0.12, 0.0)

    with pytest.raises(ValueError):
        generator.naca_4digit_coordinates(0.02, 0.0, 0.12, 0.060)

    with pytest.raises(ValueError):
        generator.naca_4digit_coordinates(0.0, 0.0, 0.12, 0.060, num_points=1)


def test_fusion_point_generator_converts_millimeters_to_fusion_centimeters():
    generator = _load_generator()

    class FakePoint3D:
        @staticmethod
        def create(x, y, z):
            return (x, y, z)

    generator.adsk = SimpleNamespace(core=SimpleNamespace(Point3D=FakePoint3D))

    upper, lower = generator.naca_4digit_airfoil(
        m=0.0,
        p=0.0,
        t=0.12,
        c=0.060,
        num_points=10,
    )

    assert upper[-1][0] == pytest.approx(6.0)
    assert lower[-1][0] == pytest.approx(6.0)
