"""
Project 33: NACA 4-Digit Parametric Fin Generator
Vers3Dynamics

Generates true airfoil profiles for CFD preparation, replacing flat-plate geometry.
Target Environment: Autodesk Fusion 360 Python API
"""

import math
import traceback

try:
    import adsk.core
    import adsk.fusion
except ImportError:  # Allows CI to test the geometry without Fusion 360.
    adsk = None


def naca_4digit_coordinates(m, p, t, c, num_points=50):
    """
    Return upper/lower NACA 4-digit profile coordinates in millimeters.

    m: Max camber as a fraction of chord (0.0 for symmetric stabilizer)
    p: Location of max camber as a fraction of chord
    t: Max thickness as a fraction of chord (0.12 for NACA 0012)
    c: Chord length in meters (0.060 for 60 mm)
    """
    if num_points < 2:
        raise ValueError("num_points must be at least 2")
    if c <= 0:
        raise ValueError("chord length must be positive")
    if t <= 0:
        raise ValueError("thickness must be positive")
    if m < 0 or p < 0 or p >= 1:
        raise ValueError("camber parameters must be within valid NACA bounds")
    if m > 0 and p == 0:
        raise ValueError("non-zero camber requires a positive camber location")

    upper, lower = [], []
    for i in range(num_points + 1):
        # Cosine spacing for higher point density near the leading and trailing edges.
        x_norm = (1 - math.cos(math.pi * i / num_points)) / 2
        x_chord = x_norm * c

        yt = 5 * t * c * (
            0.2969 * math.sqrt(x_norm)
            - 0.1260 * x_norm
            - 0.3516 * x_norm**2
            + 0.2843 * x_norm**3
            - 0.1015 * x_norm**4
        )

        if m > 0 and p > 0:
            if x_norm < p:
                yc = (m * c / p**2) * (2 * p * x_norm - x_norm**2)
                dyc_dx = (2 * m / p**2) * (p - x_norm)
            else:
                yc = (m * c / (1 - p) ** 2) * ((1 - 2 * p) + 2 * p * x_norm - x_norm**2)
                dyc_dx = (2 * m / (1 - p) ** 2) * (p - x_norm)
        else:
            yc = 0.0
            dyc_dx = 0.0

        theta = math.atan(dyc_dx)
        upper.append(
            (
                (x_chord - yt * math.sin(theta)) * 1000,
                (yc + yt * math.cos(theta)) * 1000,
                0,
            )
        )
        lower.append(
            (
                (x_chord + yt * math.sin(theta)) * 1000,
                (yc - yt * math.cos(theta)) * 1000,
                0,
            )
        )

    return upper, lower

def naca_4digit_airfoil(m, p, t, c, num_points=50):
    """
    m: Max camber (e.g., 0.0 for symmetric stabilizer)
    p: Location of max camber (e.g., 0.0)
    t: Max thickness as a fraction of chord (e.g., 0.12 for NACA 0012)
    c: Chord length in meters (e.g., 0.060 for 60mm)
    """
    if adsk is None:
        raise RuntimeError("Autodesk Fusion 360 API is required to create Point3D objects")

    upper_coords, lower_coords = naca_4digit_coordinates(m, p, t, c, num_points)
    upper = [adsk.core.Point3D.create(x / 10.0, y / 10.0, z / 10.0) for x, y, z in upper_coords]
    lower = [adsk.core.Point3D.create(x / 10.0, y / 10.0, z / 10.0) for x, y, z in lower_coords]
    return upper, lower

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        rootComp = design.rootComponent
        
        # Project 33 Baseline: NACA 0012, 60mm chord
        m, p, t, chord = 0.0, 0.0, 0.12, 0.060 
        
        upper_pts, lower_pts = naca_4digit_airfoil(m, p, t, chord)
        
        # Create sketch on XY plane
        sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
        sketch.name = "NACA_0012_Project33"
        
        # Draw curves
        sketch.sketchCurves.sketchFittedSplines.add(upper_pts)
        sketch.sketchCurves.sketchFittedSplines.add(lower_pts[::-1]) # Reverse for closed loop
        
        # Close the airfoil profile
        lines = sketch.sketchCurves.sketchLines
        lines.addByTwoPoints(upper_pts[-1], lower_pts[-1]) # Trailing edge
        lines.addByTwoPoints(lower_pts[0], upper_pts[0])   # Leading edge
        
        ui.messageBox("Project 33: NACA 0012 Airfoil generated successfully.")
        
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
