import traceback
try:
    import adsk.core
    import adsk.fusion
except ImportError:
    pass

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        rootComp = design.rootComponent
        
        # Project 33 Baseline Four-Bar Linkage
        ground_link = 2.5 # cm
        coupler_link = 6.0 # cm
        input_link = 1.5 # cm
        output_link = 1.5 # cm
        
        # Create sketch on XY plane
        sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
        sketch.name = "FourBar_Project33"
        
        lines = sketch.sketchCurves.sketchLines
        
        # A to D (Ground)
        pt_A = adsk.core.Point3D.create(0.0, 0.0, 0.0)
        pt_D = adsk.core.Point3D.create(ground_link, 0.0, 0.0)
        line_ground = lines.addByTwoPoints(pt_A, pt_D)
        line_ground.isConstruction = True
        
        # A to B (Input)
        pt_B = adsk.core.Point3D.create(0.0, input_link, 0.0)
        line_input = lines.addByTwoPoints(pt_A, pt_B)
        
        # B to C (Coupler)
        pt_C = adsk.core.Point3D.create(ground_link, output_link, 0.0)
        line_coupler = lines.addByTwoPoints(pt_B, pt_C)
        
        # D to C (Output)
        line_output = lines.addByTwoPoints(pt_D, pt_C)
        
        # Add dimensions
        sketch.sketchDimensions.addDistanceDimension(line_ground.startSketchPoint, line_ground.endSketchPoint,
                                                     adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
                                                     adsk.core.Point3D.create(ground_link/2, -1.0, 0))
        
        sketch.sketchDimensions.addDistanceDimension(line_input.startSketchPoint, line_input.endSketchPoint,
                                                     adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
                                                     adsk.core.Point3D.create(-1.0, input_link/2, 0))
                                                     
        sketch.sketchDimensions.addDistanceDimension(line_coupler.startSketchPoint, line_coupler.endSketchPoint,
                                                     adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
                                                     adsk.core.Point3D.create(ground_link/2, output_link + 1.0, 0))
                                                     
        sketch.sketchDimensions.addDistanceDimension(line_output.startSketchPoint, line_output.endSketchPoint,
                                                     adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
                                                     adsk.core.Point3D.create(ground_link + 1.0, output_link/2, 0))

        ui.messageBox("Project 33: Four-Bar Linkage sketch generated successfully.")
        
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
