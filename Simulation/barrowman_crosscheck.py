"""Independent re-derivation of the C5 fin centre-of-pressure terms.

This is a cross-check, not a replacement model. It reuses the geometry that
Simulation/static_margin.py parses from the OpenRocket file and the CG history
that script reports, then evaluates the fin terms in their textbook Barrowman
form (Barrowman 1967; also NASA/Estes TIR-33):

    X_F  = X_B + (X_R / 3) * (C_R + 2 C_T) / (C_R + C_T)
               + (1 / 6) * (C_R + C_T - C_R C_T / (C_R + C_T))
    CN_F = (1 + R / (S + R)) * 4 N (S / d)^2 / (1 + sqrt(1 + (2 L_F / (C_R + C_T))^2))

with X_R the tip leading-edge sweep distance and L_F the mid-chord line length.
Nose-cone and CG handling are deliberately identical to static_margin.py so that
the only difference between the two results is the fin-term formulation.

Neither this script nor static_margin.py has been independently reviewed.
Disagreement between them is recorded as a discrepancy, not resolved here.
"""

import argparse
import csv
import json
import math
from pathlib import Path

import static_margin


def textbook_fin_terms(geom, fin_count=4):
    d = geom['d_ref']
    radius = d / 2
    root, tip, span, sweep = geom['C_R'], geom['C_T'], geom['S'], geom['L_f']
    midchord = math.sqrt(span ** 2 + (sweep + tip / 2 - root / 2) ** 2)
    x_f = (geom['X_f'] + sweep / 3 * (root + 2 * tip) / (root + tip)
           + (root + tip - root * tip / (root + tip)) / 6)
    cn_f = ((1 + radius / (radius + span)) * (4 * fin_count * (span / d) ** 2)
            / (1 + math.sqrt(1 + (2 * midchord / (root + tip)) ** 2)))
    return x_f, cn_f, midchord


def crosscheck(ork_path, reference_csv):
    geom = static_margin.parse_ork(ork_path)
    x_f, cn_f, midchord = textbook_fin_terms(geom)
    cn_nose, x_nose = 2.0, 0.466 * geom['L_n']
    cp = (cn_nose * x_nose + cn_f * x_f) / (cn_nose + cn_f)
    with open(reference_csv, newline='') as handle:
        rows = list(csv.DictReader(handle))
    cgs = [float(row['cg_m']) for row in rows]
    margins = [(cp - cg) / geom['d_ref'] for cg in cgs]
    return {
        'schema': 'project33.c5.barrowman_crosscheck/1',
        'generator': 'Simulation/barrowman_crosscheck.py',
        'status': 'unreviewed cross-check; not a replacement for static_margin.py',
        'units': {'length': 'm', 'static_margin': 'calibers'},
        'differs_from_reference_in': ['fin CP sweep term uses X_R (tip leading-edge sweep)',
                                      'fin normal-force term uses mid-chord line length'],
        'shared_with_reference': ['parsed geometry', 'nose term (ogive coefficient)',
                                  'CG history from reference CSV', 'hard-coded motor assumption'],
        'fin_cp_m': round(x_f, 6),
        'fin_normal_force_coefficient': round(cn_f, 6),
        'midchord_length_m': round(midchord, 6),
        'cp_m': round(cp, 6),
        'sm_min_calibers': round(min(margins), 4),
        'sm_max_calibers': round(max(margins), 4),
    }


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
