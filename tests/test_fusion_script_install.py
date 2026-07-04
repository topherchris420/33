import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "Project33NacaFin"


def _load_installer():
    path = ROOT / "tools" / "install_fusion_script.py"
    spec = importlib.util.spec_from_file_location("install_fusion_script", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fusion_script_package_uses_fusion_naming_contract():
    package_dir = ROOT / "CAD Files" / "FusionScripts" / PACKAGE_NAME

    script_path = package_dir / f"{PACKAGE_NAME}.py"
    manifest_path = package_dir / f"{PACKAGE_NAME}.manifest"

    assert script_path.exists()
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["autodeskProduct"] == "Fusion"
    assert manifest["type"] == "script"
    assert manifest["id"]
    assert manifest["supportedOS"] == "windows|mac"
    assert manifest["editEnabled"] is True


def test_fusion_script_builds_splines_from_object_collections():
    script_path = ROOT / "CAD Files" / "FusionScripts" / PACKAGE_NAME / f"{PACKAGE_NAME}.py"
    source = script_path.read_text(encoding="utf-8")

    assert "adsk.core.ObjectCollection.create()" in source
    assert "sketchFittedSplines.add(upper_pts)" in source
    assert "sketchFittedSplines.add(_reversed_points(lower_pts))" in source


def test_default_fusion_scripts_dir_prefers_active_fusion_360_profile(tmp_path):
    installer = _load_installer()
    fusion_360_api = tmp_path / "Autodesk" / "Autodesk Fusion 360" / "API"
    fusion_360_api.mkdir(parents=True)

    assert installer.default_fusion_scripts_dir(appdata=tmp_path) == (
        fusion_360_api / "Scripts"
    )


def test_default_fusion_scripts_dir_falls_back_to_legacy_fusion_profile(tmp_path):
    installer = _load_installer()

    assert installer.default_fusion_scripts_dir(appdata=tmp_path) == (
        tmp_path / "Autodesk" / "Autodesk Fusion" / "API" / "Scripts"
    )


def test_installer_copies_script_package_and_geometry_module(tmp_path):
    installer = _load_installer()

    installed_dir = installer.install_fusion_script(
        repo_root=ROOT,
        scripts_dir=tmp_path,
    )

    assert installed_dir == tmp_path / PACKAGE_NAME
    assert (installed_dir / f"{PACKAGE_NAME}.py").exists()
    assert (installed_dir / f"{PACKAGE_NAME}.manifest").exists()
    assert (installed_dir / "naca_fin_generator.py").exists()
