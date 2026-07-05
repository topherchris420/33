import traceback
import yaml
import os

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
        
        yaml_path = os.path.join(os.path.dirname(__file__), 'parts.yaml')
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
            
        parts = data.get('parts', [])
        
        # Here we would iterate through bodies and apply materials based on parts.yaml
        # For this script, we just demonstrate the workflow
        msg = "Project 33 Material Application\n\n"
        for part in parts:
            msg += f"Tagging {part['name']} with {part['optimized_material']}\n"
            
        ui.messageBox(msg)
        
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
