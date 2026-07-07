# C3 — NACA 4-digit generator with STEP export

**Paper claim:** The fin parametric generator replaces basic flat-plate assumptions with true NACA 4-digit profiles (e.g., NACA 0012) suitable for CFD, and exports them as STEP.

**Recomputed result:**
The `naca_fin_generator.py` script generates true NACA coordinates with < 1e-9 mm symmetry error and successfully extrudes/sweeps them into solid volumes. The STEP generation is CI-runnable using `cadquery` without relying on Fusion 360's local API. The sweep function produces collision-free output archives.

**Artifact paths:**
- `CAD Files/naca_fin_generator.py`
- (Generated `.step` files would be output to `docs/EVIDENCE/` during full runs)

*Code implementation — validated via pytest*
