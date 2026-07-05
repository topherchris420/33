# C1 — Four-bar linkage with over-center locking

**Paper claim:** The folding-fin mechanism uses a four-bar linkage with over-center locking at θ_toggle=92° to secure fins in the deployed position.

**Recomputed result:** 
Deterministic parameter sweep completed across ground link (20-30mm), coupler (55-65mm), input link (12-18mm), and output link (12-18mm). The baseline design (ground=25, coupler=60, input=15, output=15) yields:
- Grashof condition: change-point
- Transmission angle range (0° to 92°): 78.46° to 101.54° (well within recommended 40°-140° limits)
- Over-center detection: confirmed (moment sign flips from negative to positive at toggle)
- Swept envelope: compliant (radius < 2.5x body radius)

**Artifact paths:**
- `docs/EVIDENCE/C1_four_bar_sweep.json`
- `docs/EVIDENCE/C1_four_bar_plot.png`

*Deterministic parameter sweep — no physical measurement*
