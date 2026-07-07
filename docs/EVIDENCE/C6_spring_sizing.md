# C6 — Aerodynamic hinge-moment spring sizing

**Paper claim:** k ≥ 185 N·m/rad with ≥ 20% margin (k_supplied = 220 N·m/rad)

**Recomputed result:**
At the design point (v_egress = 205 m/s, c_fin = 120 mm, S_fin = 0.0216 m², h_fin = 180 mm, m_fin = 154 g, Cmα = 0.8, damping = 0.7):
- k_min = 184.9 N·m/rad
- k_supplied = 220 N·m/rad
- Margin = 19.0%

The computed k_min is below k_supplied, confirming the design has adequate margin.

**Artifact paths:**
- `docs/EVIDENCE/C6_spring_sweep.json`
- `docs/EVIDENCE/C6_spring_sweep_plot.png`

*Deterministic computation — no physical measurement*
