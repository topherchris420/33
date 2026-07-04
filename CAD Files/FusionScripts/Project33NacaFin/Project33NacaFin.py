"""
Fusion 360 entrypoint for the Project 33 NACA fin profile generator.

This script is intentionally CAD-only. It creates a 60 mm NACA 0012 sketch
profile and does not touch firmware, launch, ignition, or actuator behavior.
"""

import importlib.util
import os
import traceback

import adsk.core
import adsk.fusion


SCRIPT_NAME = "Project33NacaFin"


def _load_geometry_module():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "naca_fin_generator.py"),
        os.path.abspath(os.path.join(script_dir, "..", "..", "naca_fin_generator.py")),
    ]

    for path in candidates:
        if os.path.exists(path):
            spec = importlib.util.spec_from_file_location("project33_naca_geometry", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

    raise FileNotFoundError("Could not find naca_fin_generator.py")


def _points_from_mm(coords):
    points = adsk.core.ObjectCollection.create()
    for x, y, z in coords:
        points.add(adsk.core.Point3D.create(x / 10.0, y / 10.0, z / 10.0))
    return points


def _reversed_points(points):
    reversed_points = adsk.core.ObjectCollection.create()
    for index in range(points.count - 1, -1, -1):
        reversed_points.add(points.item(index))
    return reversed_points


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        if design is None:
            ui.messageBox("Open or create a Fusion design before running Project33NacaFin.")
            return

        root_comp = design.rootComponent
        geometry = _load_geometry_module()

        upper_coords, lower_coords = geometry.naca_4digit_coordinates(
            m=0.0,
            p=0.0,
            t=0.12,
            c=0.060,
            num_points=50,
        )
        upper_pts = _points_from_mm(upper_coords)
        lower_pts = _points_from_mm(lower_coords)

        sketch = root_comp.sketches.add(root_comp.xYConstructionPlane)
        sketch.name = "NACA_0012_Project33_60mm"

        sketch.sketchCurves.sketchFittedSplines.add(upper_pts)
        sketch.sketchCurves.sketchFittedSplines.add(_reversed_points(lower_pts))

        lines = sketch.sketchCurves.sketchLines
        lines.addByTwoPoints(upper_pts.item(upper_pts.count - 1), lower_pts.item(lower_pts.count - 1))
        lines.addByTwoPoints(lower_pts.item(0), upper_pts.item(0))

        ui.messageBox("Project 33: NACA 0012 60 mm fin profile sketch generated.")

    except Exception:
        if ui:
            ui.messageBox("Failed:\n{}".format(traceback.format_exc()))
        else:
            raise
