"""Install the Project 33 Fusion script package into Fusion's API Scripts folder."""

import argparse
import os
import shutil
from pathlib import Path


PACKAGE_NAME = "Project33NacaFin"


def default_fusion_scripts_dir(appdata=None):
    appdata_root = Path(appdata) if appdata is not None else Path(os.environ["APPDATA"])
    autodesk_root = appdata_root / "Autodesk"
    fusion_360_dir = autodesk_root / "Autodesk Fusion 360" / "API" / "Scripts"
    fusion_dir = autodesk_root / "Autodesk Fusion" / "API" / "Scripts"

    if fusion_360_dir.parent.exists():
        return fusion_360_dir
    return fusion_dir


def fusion_package_dir(repo_root):
    return Path(repo_root) / "CAD Files" / "FusionScripts" / PACKAGE_NAME


def _copy_contents(source_dir, target_dir):
    target_dir.mkdir(parents=True, exist_ok=True)
    for source in source_dir.iterdir():
        target = target_dir / source.name
        if source.is_dir():
            _copy_contents(source, target)
        else:
            shutil.copy2(source, target)


def install_fusion_script(repo_root=None, scripts_dir=None):
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[1]
    source_dir = fusion_package_dir(root)
    if not source_dir.exists():
        raise FileNotFoundError(f"Missing Fusion script package: {source_dir}")

    target_root = Path(scripts_dir) if scripts_dir is not None else default_fusion_scripts_dir()
    target_dir = target_root / PACKAGE_NAME

    _copy_contents(source_dir, target_dir)
    shutil.copy2(root / "CAD Files" / "naca_fin_generator.py", target_dir / "naca_fin_generator.py")
    return target_dir


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project 33 repository root.",
    )
    parser.add_argument(
        "--scripts-dir",
        type=Path,
        default=None,
        help=(
            "Fusion API Scripts directory. Defaults to the active Autodesk Fusion "
            "360 API profile when present, otherwise %%APPDATA%%\\Autodesk\\Autodesk "
            "Fusion\\API\\Scripts."
        ),
    )
    args = parser.parse_args(argv)

    installed_dir = install_fusion_script(repo_root=args.repo_root, scripts_dir=args.scripts_dir)
    print(f"Installed {PACKAGE_NAME} to {installed_dir}")


if __name__ == "__main__":
    main()
