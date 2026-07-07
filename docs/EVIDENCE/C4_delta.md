# C4 â€” Material substitution matrix

**Paper claim:** Material optimization (quasi-isotropic CFRP, Ti-6Al-4V) yields a 30-40% total mass reduction compared to the baseline 3D printed/aluminum assembly.

**Recomputed result:**
Baseline Mass: 98.1 g
Optimized Mass: 62.8 g
Mass Reduction: 36.0%

| Part | Baseline Material | Optimized Material | Baseline Mass (g) | Optimized Mass (g) | Delta (g) |
|---|---|---|---|---|---|
| Body Tube | 7075-T6 | CFRP_quasi_iso | 42.7 | 23.6 | 19.2 |
| Nose Cone | PLA | PLA | 15.5 | 15.5 | 0.0 |
| Fin (x4) | 7075-T6 | CFRP_quasi_iso | 38.2 | 21.1 | 17.1 |
| Hinge Pin (x4) | 7075-T6 | Ti-6Al-4V | 1.7 | 2.7 | -1.0 |

**Artifact paths:**
- `docs/EVIDENCE/C4_mass_baseline.csv`
- `docs/EVIDENCE/C4_mass_optimized.csv`

*Deterministic computation â€” no physical measurement*
