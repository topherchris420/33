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

def test_naca_00xx_symmetry_error():
    generator = _load_generator()
    upper, lower = generator.naca_4digit_coordinates(0.0, 0.0, 0.12, 0.060, num_points=50)
    for u, l in zip(upper, lower):
        assert abs(u[1] + l[1]) < 1e-9

def test_step_export_roundtrips(tmp_path):
    import cadquery as cq
    generator = _load_generator()
    upper, lower = generator.naca_4digit_coordinates(0.0, 0.0, 0.12, 0.060, num_points=50)
    
    step_file = tmp_path / "test_fin.step"
    generator.export_step(upper, lower, str(step_file), span=60.0)
    
    assert step_file.exists()
    
    imported = cq.importers.importStep(str(step_file))
    faces = imported.faces().vals()
    assert len(faces) > 0

def test_sweep_produces_unique_files(tmp_path):
    generator = _load_generator()
    params = [
        {'t': 0.10, 'c': 0.050, 'sweep_deg': 0.0},
        {'t': 0.12, 'c': 0.060, 'sweep_deg': 15.0},
        {'t': 0.15, 'c': 0.070, 'sweep_deg': 30.0}
    ]
    generator.sweep(params, str(tmp_path))
    
    files = list(tmp_path.glob("*.step"))
    assert len(files) == 3
