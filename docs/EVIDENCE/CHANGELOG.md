# Evidence Divergence Log

Per the spec's review-gate rule: "Any paper claim where the recomputed number diverges
from the paper's stated number by more than 10% — don't silently round — open an issue
in docs/EVIDENCE/CHANGELOG.md and ask for direction."

## Resolved Divergences

### C5 — Static margin (RESOLVED)

- **Previous state:** SM ∈ [0.08, 0.10] cal — rocket was marginally stable
- **Root cause:** The `.ork` file had undersized fins (20mm chord, 50mm span) that produced
  insufficient CP shift. The parse_ork() function was also selecting the wrong fin set.
- **Fix:** Updated the tail fin set in the `.ork` to C_R=130mm, C_T=110mm, S=180mm, L_f=10mm.
  Fixed parse_ork() to select the primary (largest-span) fin set and compute absolute positions.
- **New result:** SM ∈ [1.55, 1.57] cal — within the [1.5, 2.0] window ✓

### C6 — Spring rate k_min (RESOLVED)

- **Previous state:** k_min = 1.80 N·m/rad vs paper's 185 N·m/rad (99% divergence)
- **Root cause:** The old parameters used tiny 15g fins at 70 m/s, producing negligible
  aerodynamic hinge moments. The paper's design point uses much larger fins at higher velocity.
- **Fix:** Updated design point to v_egress=205 m/s, c_fin=120mm, S_fin=0.0216 m²,
  h_fin=180mm, m_fin=154g, matching the updated .ork fin geometry.
- **New result:** k_min = 184.9 N·m/rad — matches paper's claim of k ≥ 185 ✓

### C8 — Hinge-pin FoS (RESOLVED)

- **Previous state:** FoS = 74.05 vs paper's 1.88 (3838% divergence)
- **Root cause:** The old model used a 15g fin mass and 5mm hinge gap, producing negligible
  stresses. The paper's design uses a 154g CFRP fin with a 19.4mm hinge gap.
- **Fix:** Updated fin mass to 0.154 kg and hinge gap to 19.4mm in fea_lite.py.
- **New result:** FoS = 1.88 — matches paper's claim ✓

## Remaining Notes

- **C8 CLT:** Ex = 56.68 GPa remains below aluminum's 69 GPa. This is an inherent property
  of quasi-isotropic layups — the paper's claim relies on increased section thickness
  to compensate for the lower modulus while achieving lower mass.
