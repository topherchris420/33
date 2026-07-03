"""
Project 33: NACA 4-Digit Parametric Fin Generator
Vers3Dynamics

Generates true airfoil profiles for CFD preparation, replacing flat-plate geometry.
Target Environment: Autodesk Fusion 360 Python API
"""

import adsk.core, adsk.fusion, traceback, math

def naca_4digit_airfoil(m, p, t, c, num_points=50):
    """
    m: Max camber (e.g., 0.0 for symmetric stabilizer)
    p: Location of max camber (e.g., 0.0)
    t: Max thickness as a fraction of chord (e.g., 0.12 for NACA 0012)
    c: Chord length in meters (e.g., 0.060 for 60mm)
    """
    upper, lower = [], []
    for i in range(num_points + 1):
        # Cosine spacing for CFD boundary layer accuracy
        x = (1 - math.cos(math.pi * i / num_points)) / 2 
        
        # Standard NACA 4-digit thickness distribution
        yt = 5 * t * c * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4)
        
        # Camber calculations (kept minimal for tail fins, but structurally included)
        yc = 0
        if p > 0 and m > 0:
            yc = m * c * ((1/p**2) * (2*p*x - x**2)) if x < p else m * c * ((1-2*p) + 2*p*x - x**2) / ((1-p)**2)
            
        # Scale to mm for Fusion 360
        upper.append(adsk.core.Point3D.create(x * 1000, (yc + yt) * 1000, 0))
        lower.append(adsk.core.Point3D.create(x * 1000, (yc - yt) * 1000, 0))
        
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
