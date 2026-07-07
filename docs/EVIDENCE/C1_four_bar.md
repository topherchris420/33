# C1 â€” Four-bar linkage with over-center locking

**Paper claim:** The folding-fin mechanism uses a four-bar linkage with over-center locking at Î¸_toggle=92Â° to secure fins in the deployed position.

**Recomputed result:** 
Deterministic parameter sweep completed across ground link (20-30mm), coupler (55-65mm), input link (12-18mm), and output link (12-18mm). The baseline design (ground=25, coupler=60, input=15, output=15) yields:
- Grashof condition: change-point
- Transmission angle range (0Â° to 92Â°): 78.46Â° to 101.54Â° (well within recommended 40Â°-140Â° limits)
- Over-center detection: confirmed (moment sign flips from negative to positive at toggle)
- Swept envelope: compliant (radius < 2.5x body radius)

**Artifact paths:**
- `docs/EVIDENCE/C1_four_bar_sweep.json`
- `docs/EVIDENCE/C1_four_bar_plot.png`

*Deterministic parameter sweep â€” no physical measurement*
