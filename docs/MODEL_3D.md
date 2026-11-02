# Faceted 3D model

`model.html` is an interactive three.js model of the folding-fin rocket and the launcher platform, drawn in a faceted (octagonal) skin. Viewers can switch the fins between deployed and folded, the view between exploded and assembled, and the launcher on or off. The page exports the current model as OBJ + MTL or GLB.

**This is a design visualization. It is not evidence.** It is not a CAD source, a measured geometry, a mass model, or a demonstration that the folding mechanism works. Nothing on this page should be cited in a claim passport.

## Files

- `model.html`: the page and the model geometry (all dimensions in mm, scaled to metres for export).
- `assets/model/three-d-stage.js`: the viewer (renderer, lighting, orbit controls, OBJ/GLB export).
- `assets/model/industry.css`: the page's stylesheet (Industry design system).

three.js 0.184.0 loads from unpkg through a pinned import map with subresource-integrity hashes.

## Where the numbers come from

| Feature | Value in the model | Source |
|---|---|---|
| Overall length | 683 mm, all of it modelled as body tube | "Length 68.3 cm" printed on `Simulation/Side_View.png` |
| Body diameter | 76.2 mm (octagon circumradius 38.1 mm) | `docs/EVIDENCE/C5_static_margin_inputs.json` (`d_ref`) |
| Nose length | 38.1 mm, ellipsoid profile | `C5_static_margin_inputs.json` (`L_n`, `ork_nose_shape`) |
| Fin root / tip chord, span | 130 / 110 mm, 180 mm | `C5_static_margin_inputs.json` (`C_R`, `C_T`, `S`) |
| Fin section | NACA 0012, faceted | `CAD Files/naca_fin_generator.py` |
| Canards | 4 × 28 × 57 mm, 209 mm aft of the nose tip, SG90-driven | Measured from `Simulation/Side_View.png`; servo from `docs/BOM.md` |
| Internals and launcher layout | ESP32, MPU6050, regulator, switches, GPS, compass, barometer | `docs/BOM.md`, `materials/bom.csv`, `materials/parts.yaml`, `docs/CAD_ASSEMBLIES.md` |

## Assumptions that are not in the repository

- **Faceting.** The octagonal body, faceted nose and flat-faceted fin sections are a styling choice, not an airframe change.
- **Overall length.** `Simulation/Folding Stabilized Rocket.ork` sums to 601 mm (38.1 mm nose + 342.9 mm + 220 mm body tubes). The 683 mm printed on the side view appears to include the swept fins that reach past the tail. The model stretches the body tube to 683 mm and also hangs the fins below it, so it is about 80 mm longer than the `.ork` airframe.
- **Canard size and position.** The `.ork` canard set is 25.4 mm root and tip chord, 50.8 mm span, 5 mm sweep, at 180 mm from the nose tip. The model uses 28 × 57 mm at 209 mm, measured from the side view.
- **Fin sweep.** The model uses a 90 mm leading-edge sweep read from `Simulation/Side_View.png`. The `.ork` and `C5_static_margin_inputs.json` both record a 10 mm sweep length (`sweeplength` / `L_f_sweeplength`), so the image and the model file disagree; the 3D model follows the image.
- **Fin fold.** Each fin turns 120° about a skewed hinge axis to lie along the body. At these fin sizes the folded fins still stand well proud of the tube, so this is not a tube-stowable shape.
- **C1 four-bar linkage.** Omitted, because `mechanism/four_bar.py` shows the loop does not close (claim C1 is contradicted).
- **Board and battery sizes.** Typical stock dimensions for the listed parts.
- **Materials.** PLA+/PETG prints with stock steel hardware; colours only.
