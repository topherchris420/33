import traceback
try:
    import adsk.core
    import adsk.fusion
except ImportError:
    pass

# Project 33 Militarized Four-Bar Linkage (Phase 1 redesign, design_point.json
# revision 2026-11-14-phase1). Resolves D-002: the historical 25/60/15/15 mm
# linkage could not close at any pose; this one is verified to close over the
# full stroke and to lock over-center (see docs/EVIDENCE/C1_four_bar_military.json).
# Coupler resized from 60 mm to 15.5 mm; crank from 15 to 14 mm.
#
# Sketch draws the LINKAGE in the deployed-stop pose so the dimensions are the
# verified kinematic ones. Link lengths are pin-centre distances.
GROUND_LINK = 2.5   # cm, crank pivot A (forward) to fin hinge D (aft)
CRANK_LINK = 1.4     # cm, input link AB driven by the torsion spring
COUPLER_LINK = 1.55  # cm, coupler BC
OUTPUT_LINK = 1.5    # cm, output link DC carrying the fin

# Deployed-stop pose crank angle (fin at its 90 deg hard stop), from the
# kinematic analysis: crank 381.7 deg (= 21.7 deg past top-dead-aft through 360).
CRANK_ANGLE_STOP_DEG = 21.7


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        rootComp = design.rootComponent

        sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
        sketch.name = "FourBar_Project33_Militarized"

        lines = sketch.sketchCurves.sketchLines

        import math as _m
        # A at origin, D at (ground, 0); +x from A (nose side) to D (tail side).
        pt_A = adsk.core.Point3D.create(0.0, 0.0, 0.0)
        pt_D = adsk.core.Point3D.create(GROUND_LINK, 0.0, 0.0)
        line_ground = lines.addByTwoPoints(pt_A, pt_D)
        line_ground.isConstruction = True

        # Crank AB at the deployed-stop pose
        t2 = _m.radians(CRANK_ANGLE_STOP_DEG)
        pt_B = adsk.core.Point3D.create(CRANK_LINK * _m.cos(t2), CRANK_LINK * _m.sin(t2), 0.0)
        line_input = lines.addByTwoPoints(pt_A, pt_B)

        # Joint C at the stop pose (fin perpendicular on +y): C = D + output * (cos90, sin90)
        pt_C = adsk.core.Point3D.create(GROUND_LINK, OUTPUT_LINK, 0.0)
        line_coupler = lines.addByTwoPoints(pt_B, pt_C)
        line_output = lines.addByTwoPoints(pt_D, pt_C)

        # Add dimensions
        sketch.sketchDimensions.addDistanceDimension(line_ground.startSketchPoint, line_ground.endSketchPoint,
                                                     adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
                                                     adsk.core.Point3D.create(GROUND_LINK/2, -1.0, 0))
        sketch.sketchDimensions.addDistanceDimension(line_input.startSketchPoint, line_input.endSketchPoint,
                                                     adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
                                                     adsk.core.Point3D.create(-1.0, CRANK_LINK/2, 0))
        sketch.sketchDimensions.addDistanceDimension(line_coupler.startSketchPoint, line_coupler.endSketchPoint,
                                                     adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
                                                     adsk.core.Point3D.create(GROUND_LINK/2, OUTPUT_LINK + 1.0, 0))
        sketch.sketchDimensions.addDistanceDimension(line_output.startSketchPoint, line_output.endSketchPoint,
                                                     adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
                                                     adsk.core.Point3D.create(GROUND_LINK + 1.0, OUTPUT_LINK/2, 0))

        ui.messageBox("Project 33: militarized four-bar sketch generated (deployed-stop pose).")

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def export_step(path):
    import cadquery as cq
    import math as m
    # Parameters: pin-centre distances from design_point.json (mm)
    ground = 25.0
    crank = 14.0
    coupler = 15.5
    output_l = 15.0
    width = 6.0
    thick = 3.0
    hole = 2.0

    # Assembly at the deployed-stop pose: A=(0,0), D=(25,0),
    # B=(14*cos(21.7deg), 14*sin(21.7deg)), C=(25,+15) (fin perpendicular, +y side).
    t2 = m.radians(21.7)
    ax, ay = 0.0, 0.0
    dx_, dy_ = ground, 0.0
    bx, by = crank * m.cos(t2), crank * m.sin(t2)
    cx, cy = ground, output_l

    # Build each bar along X, then rotate/translate to its pose.
    def bar(length, x1, y1, x2, y2, z):
        ang = m.degrees(m.atan2(y2 - y1, x2 - x1))
        solid = (cq.Workplane("XY")
                 .box(length + width, width, thick)
                 .faces(">Z").workplane()
                 .pushPoints([(-length/2, 0), (length/2, 0)])
                 .hole(hole))
        solid = solid.rotate((0, 0, 0), (0, 0, 1), ang)
        solid = solid.translate(((x1 + x2) / 2, (y1 + y2) / 2, z))
        return solid

    l_ground = bar(ground, ax, ay, dx_, dy_, 0.0)
    l_input = bar(crank, ax, ay, bx, by, thick)
    l_coupler = bar(coupler, bx, by, cx, cy, 2 * thick)
    l_output = bar(output_l, dx_, dy_, cx, cy, thick)

    assm = (cq.Assembly()
            .add(l_ground, name="ground", color=cq.Color("gray"))
            .add(l_input, name="crank", color=cq.Color("red"))
            .add(l_coupler, name="coupler", color=cq.Color("blue"))
            .add(l_output, name="output_fin_arm", color=cq.Color("green")))
    assm.save(path)

if __name__ == '__main__':
    import sys
    from pathlib import Path
    if len(sys.argv) > 1 and sys.argv[1] == '--export':
        out_path = Path(sys.argv[2])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        export_step(str(out_path))
        print(f"Exported militarized four-bar linkage to {out_path}")
