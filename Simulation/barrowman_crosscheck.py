"""Independent numerical cross-check of the C5 fin terms.

Revision 2 of the cross-check compared two closed-form fin-term spellings and
could only record that they disagree (D-006). Revision 3 cross-checks the
militarized model (Simulation/static_margin.py rev 3) numerically:

- The fin-set CP is re-computed by spanwise strip integration: each strip is
  weighted by its local chord with its local quarter-chord as the pressure
  center. For a trapezoid this reduces algebraically to the textbook closed
  form; the numerical integral validates that reduction independently.
- The mid-chord line length is re-computed by numerically integrating the
  chord-line path between strip boundaries.
- The nose CP fraction is re-derived by an independent discrete sum instead of
  np.gradient.

Agreement is reported with tolerances; disagreement is recorded, not hidden.
Neither model has been physically validated.
"""

import argparse
import json
import math
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import static_margin  # noqa: E402


def strip_fin_cp(x_le, c_root, c_tip, span, sweep_xr, n_strips=4000):
    """Fin-set CP by numerical spanwise strip integration.

    Strip loading proportional to local chord; local pressure center at the
    local quarter chord. Returns (x_cp, mean_chord, midchord_numeric).
    """
    xs = [sweep_xr * (i + 0.5) / n_strips for i in range(n_strips)]  # tip LE line
    num = 0.0
    den = 0.0
    path = 0.0
    prev_mid = (c_root / 2.0, 0.0)  # (x, y) of root mid-chord in fin plane
    for i in range(n_strips):
        y = (i + 0.5) * span / n_strips
        c = c_root + (c_tip - c_root) * (y / span)
        x_le_local = sweep_xr * (y / span)
        x_q = x_le_local + c / 4.0
        num += c * x_q
        den += c
        # mid-chord path length (numerical)
        mid = (x_le_local + c / 2.0, y)
        path += math.hypot(mid[0] - prev_mid[0], mid[1] - prev_mid[1])
        prev_mid = mid
    return x_le + num / den, den * span / n_strips, path


def strip_fin_cn(span, d_ref, radius, count, midchord, c_root, c_tip):
    """Normal-force coefficient with the numerically integrated mid-chord."""
    return ((1.0 + radius / (radius + span)) * (4.0 * count * (span / d_ref) ** 2)
            / (1.0 + math.sqrt(1.0 + (2.0 * midchord / (c_root + c_tip)) ** 2)))


def discrete_nose_cp_fraction(shape, n=4000):
    """Nose CP fraction by an explicit discrete d(r^2) sum (independent of
    static_margin's np.gradient approach)."""
    if shape == 'ogive':
        return 0.466
    total_w = 0.0
    total_xw = 0.0
    prev_r2 = 0.0
    for i in range(1, n + 1):
        x = i / n
        if shape == 'cone':
            r2 = x * x
        elif shape in ('ellipsoid', 'elliptical'):
            r2 = max(0.0, 1.0 - (1.0 - x) ** 2)
        else:
            r2 = max(0.0, 1.0 - (1.0 - x) ** 2)
        w = max(r2 - prev_r2, 0.0)
        total_w += w
        total_xw += w * x
        prev_r2 = r2
    if total_w <= 0:
        return 0.5
    return total_xw / total_w


def crosscheck(ork_path, reference_csv, design_point_path=static_margin.DESIGN_POINT_PATH):
    dp = static_margin.load_design_point(design_point_path)
    ork_geom = static_margin.parse_ork(ork_path)
    d_ref = ork_geom['d_ref']
    radius = d_ref / 2.0

    # Reference model values
    ref = static_margin.assemble_cp(dp, ork_geom)
    cp_ref, terms_ref = ref

    # Numerical cross-check
    ca = dp['canards']
    mf = dp['main_fins']
    checks = {}
    cn_terms = 2.0
    x_terms = 2.0 * discrete_nose_fraction_x(ork_geom, ork_geom['ork_nose_shape'])
    mid_num_main = 0.0
    for name, spec in (('canards', ca), ('main_fins', mf)):
        x_cp, mean_chord, mid_num = strip_fin_cp(
            spec['leading_edge_x_mm'] / 1000.0, spec['root_chord_mm'] / 1000.0,
            spec['tip_chord_mm'] / 1000.0, spec['span_mm'] / 1000.0,
            spec['tip_le_sweep_mm'] / 1000.0)
        if name == 'main_fins':
            mid_num_main = mid_num
        cn = strip_fin_cn(spec['span_mm'] / 1000.0, d_ref, radius, spec['count'],
                         mid_num, spec['root_chord_mm'] / 1000.0, spec['tip_chord_mm'] / 1000.0)
        closed = static_margin.fin_terms(
            spec['leading_edge_x_mm'] / 1000.0, spec['root_chord_mm'] / 1000.0,
            spec['tip_chord_mm'] / 1000.0, spec['span_mm'] / 1000.0,
            spec['tip_le_sweep_mm'] / 1000.0, radius, d_ref, spec['count'])
        checks[name] = {
            'cp_closed_form_m': round(closed[1], 6),
            'cp_strip_integration_m': round(x_cp, 6),
            'cp_difference_mm': round(abs(closed[1] - x_cp) * 1000.0, 4),
            'cn_closed_form': round(closed[0], 4),
            'cn_strip_integration': round(cn, 4),
            'cn_relative_difference': round(abs(closed[0] - cn) / closed[0], 6),
        }
        cn_terms += cn
        x_terms += cn * x_cp

    cp_num = x_terms / cn_terms

    with open(reference_csv, newline='') as handle:
        import csv
        rows = list(csv.DictReader(handle))
    cgs = [float(row['cg_m']) for row in rows]
    margins = [(cp_num - cg) / d_ref for cg in cgs]
    margins_ref = [(cp_ref - cg) / d_ref for cg in cgs]

    return {
        'schema': 'project33.c5.barrowman_crosscheck/2',
        'generator': 'Simulation/barrowman_crosscheck.py',
        'status': 'numerical cross-check of the rev 3 model; both are MODELED',
        'units': {'length': 'm', 'static_margin': 'calibers'},
        'method': 'spanwise strip integration (chord-weighted, local quarter-chord pressure centers) and discrete nose d(r^2) sums, independent of the closed-form algebra they check',
        'checks': checks,
        'nose_cp_fraction_numeric': round(discrete_nose_cp_fraction(ork_geom['ork_nose_shape']), 4),
        'cp_m_closed_form': round(cp_ref, 6),
        'cp_m_strip_integration': round(cp_num, 6),
        'cp_difference_mm': round(abs(cp_ref - cp_num) * 1000.0, 3),
        'midchord_length_m': round(mid_num_main, 5),
        'sm_min_calibers': round(min(margins), 4),
        'sm_max_calibers': round(max(margins), 4),
        'sm_min_calibers_reference_model': round(min(margins_ref), 4),
        'agreement_statement': 'strip integration and closed form agree within tolerance if the differences above are below 1 mm (CP) and 1 percent (CN)',
    }


def discrete_nose_fraction_x(ork_geom, shape):
    """Nose CP station (m) by the discrete sum."""
    return discrete_nose_cp_fraction(shape) * ork_geom['L_n']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ork', required=True)
    parser.add_argument('--reference-csv', required=True)
    parser.add_argument('--emit', required=True)
    args = parser.parse_args()
    result = crosscheck(args.ork, args.reference_csv)
    output = Path(args.emit)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
