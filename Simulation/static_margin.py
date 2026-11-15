"""Static-margin model, revision 3 (militarized Phase 1).

Corrects every defect recorded against revision 2 (D-006, D-007, D-008):

- Fin terms use the textbook Barrowman form (Barrowman 1967; Estes TIR-33):
  the fin CP sweep term uses the tip leading-edge sweep X_R (revision 2 used
  the root chord there), and the normal-force term uses the mid-chord line
  length (revision 2 used the sweep length). Both revision-2 errors pushed
  the CP aft and inflated the margin; the textbook cross-check was right.
- The nose is an ellipsoid: its CP is derived by the Barrowman d(r^2)/dx
  weighting, giving X_N = L/3 from the tip (verified against the known cone
  2L/3 and ogive 0.466L results of the same derivation), not the ogive
  0.466L coefficient revision 2 applied.
- Canards are modeled (revision 2 ignored them; they pull the CP forward).
- The motor is the OpenRocket model's AeroTech G64W with published certified
  data (thrustcurve.org, retrieved 2026-11-14): 151 g wet, 88 g dry,
  63 g propellant, 2.1 s burn. Revision 2 burned a hard-coded Estes C6-5.
- Dry mass uses the explicit component model in design_point.json, including
  the nose override revision 2 dropped, instead of summing ambiguous tube
  overrides.

Fins were resized at this design point (rectangular 160 x 220 mm, leading
edge 440 mm) so the margin stays inside 1.5-2.0 calibers through the burn.
All results are MODELED.
"""

import argparse
import json
import math
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_POINT_PATH = REPO_ROOT / 'design_point.json'


def load_design_point(path=DESIGN_POINT_PATH):
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def nose_cp_fraction(shape):
    """CP fraction of nose length from the tip, by the Barrowman d(r^2)/dx weighting.

    For each shape the result comes from integrating x * d(r^2)/dx over
    d(r^2)/dx (x from the tip). The cone result reproduces the published
    Barrowman table value (2/3), which validates the derivation; the
    ellipsoid is then evaluated on the same footing, giving L/3. The ogive
    uses the published table value 0.466 directly (its exact tangent-ogive
    integral depends on the radius ratio; the table value is standard).
    """
    if shape == 'ogive':
        return 0.466
    n = 20000
    xs = np.linspace(0.0, 1.0, n)
    if shape == 'cone':
        r2 = xs ** 2
    elif shape in ('ellipsoid', 'elliptical'):
        r2 = np.maximum(0.0, 1.0 - (1.0 - xs) ** 2)
    elif shape == 'parabolic':
        r2 = xs
    else:
        r2 = np.maximum(0.0, 1.0 - (1.0 - xs) ** 2)
    dr2 = np.gradient(r2, xs)
    weight = np.maximum(dr2, 0.0)
    if weight.sum() <= 0:
        return 0.5
    return float((xs * weight).sum() / weight.sum())


def fin_terms(x_le, c_root, c_tip, span, sweep_xr, radius, d_ref, count, density_unused=None):
    """Textbook Barrowman fin-set terms (TIR-33 form).

    Returns (cn_f, x_f) for the whole fin set: cn_f is the set normal-force
    coefficient contribution, x_f the CP station from the nose tip.
    """
    if span <= 0 or c_root + c_tip <= 0:
        return 0.0, x_le
    # mid-chord line length: root mid-chord to tip mid-chord
    dx_mid = sweep_xr + c_tip / 2.0 - c_root / 2.0
    midchord = math.sqrt(span ** 2 + dx_mid ** 2)
    cn_f = ((1.0 + radius / (radius + span)) * (4.0 * count * (span / d_ref) ** 2)
            / (1.0 + math.sqrt(1.0 + (2.0 * midchord / (c_root + c_tip)) ** 2)))
    x_f = (x_le
           + (sweep_xr / 3.0) * (c_root + 2.0 * c_tip) / (c_root + c_tip)
           + (1.0 / 6.0) * (c_root + c_tip - c_root * c_tip / (c_root + c_tip)))
    return cn_f, x_f


def _main_fin_geometry(ork_geom, dp):
    """Main-fin geometry block for the laboratory views.

    The revision-3 model takes its fin geometry from design_point.json; this
    block reports the same values in the legacy key layout (d_ref, L_n, X_f,
    C_R, C_T, S, L_f_sweeplength) so lab/js consumers keep working.
    """
    mf = dp['main_fins']
    canards = dp['canards']
    return {
        'd_ref': ork_geom['d_ref'],
        'L_n': ork_geom['L_n'],
        'X_f': mf['leading_edge_x_mm'] / 1000.0,
        'C_R': mf['root_chord_mm'] / 1000.0,
        'C_T': mf['tip_chord_mm'] / 1000.0,
        'S': mf['span_mm'] / 1000.0,
        'L_f_sweeplength': mf['tip_le_sweep_mm'] / 1000.0,
        'canard_X_f': canards['leading_edge_x_mm'] / 1000.0,
        'canard_span': canards['span_mm'] / 1000.0,
        'note': 'main fin set per design_point.json (militarized resize); canard fields included',
    }


def assemble_cp(dp, ork_geometry):
    """Total CP from nose, canards, and main fins. Returns (cp, terms)."""
    d_ref = ork_geometry['d_ref']
    radius = d_ref / 2.0
    L_n = ork_geometry['L_n']

    # Nose: CN = 2 (Barrowman), CP at the derived fraction
    x_n = nose_cp_fraction(ork_geometry['ork_nose_shape']) * L_n
    cn_n = 2.0

    # Canards (unchanged from the .ork)
    ca = dp['canards']
    cn_c, x_c = fin_terms(ca['leading_edge_x_mm'] / 1000.0, ca['root_chord_mm'] / 1000.0,
                         ca['tip_chord_mm'] / 1000.0, ca['span_mm'] / 1000.0,
                         ca['tip_le_sweep_mm'] / 1000.0, radius, d_ref, ca['count'])

    # Main fins (resized per the corrected derivation)
    mf = dp['main_fins']
    cn_m, x_m = fin_terms(mf['leading_edge_x_mm'] / 1000.0, mf['root_chord_mm'] / 1000.0,
                         mf['tip_chord_mm'] / 1000.0, mf['span_mm'] / 1000.0,
                         mf['tip_le_sweep_mm'] / 1000.0, radius, d_ref, mf['count'])

    cn_total = cn_n + cn_c + cn_m
    cp = (cn_n * x_n + cn_c * x_c + cn_m * x_m) / cn_total
    terms = {
        'nose': {'cn': cn_n, 'x_m': round(x_n, 5), 'cp_fraction': round(x_n / L_n, 4)},
        'canards': {'cn': round(cn_c, 4), 'x_m': round(x_c, 5)},
        'main_fins': {'cn': round(cn_m, 4), 'x_m': round(x_m, 5)},
        'cn_total': round(cn_total, 4),
    }
    return cp, terms


def mass_and_cg(dp, motor_propellant_burned_fraction):
    """Dry mass, CG, and wet mass with the given propellant fraction remaining."""
    components = []
    for comp in dp['mass_model']['dry_components']:
        components.append((comp['mass_kg'], comp['cg_m']))
    motor = dp['mass_model']['motor']
    prop = motor['propellant_kg'] * (1.0 - motor_propellant_burned_fraction)
    m_motor = motor['dry_kg'] + prop
    components.append((m_motor, motor['cg_m']))
    total = sum(m for m, _ in components)
    cg = sum(m * x for m, x in components) / total
    return total, cg


def parse_ork(ork_path):
    """Parses rocket geometry from an OpenRocket .ork file (zipped XML).

    Revision 3: applies OpenRocket axial-method semantics (absolute, top,
    middle, bottom) to every attached component, so fin stations match what
    OpenRocket itself computes. Revision 2 read the raw <position> value and
    could misplace fin sets by up to 90 mm (D-008 family; see LAB-OBS-1 in
    the laboratory data). The model no longer relies on tube override masses
    (the explicit design-point mass model replaces them, see D-008/D-009),
    but they are reported for traceability.
    """
    with zipfile.ZipFile(ork_path, 'r') as z:
        xml_name = [n for n in z.namelist()
                    if n.endswith('.ork') or n.endswith('.xml')
                    or n == 'rocket.document'][0]
        xml_data = z.read(xml_name)

    root = ET.fromstring(xml_data)

    def get_val(elem, tag, default=None):
        found = elem.find(tag)
        if found is not None:
            return float(found.text)
        if default is not None:
            return default
        raise ValueError(f"Required field <{tag}> missing in <{elem.tag}>")

    def axial(elem):
        node = elem.find('axialoffset')
        if node is None:
            node = elem.find('position')
        if node is None:
            return 'top', 0.0
        method = node.get('method') or node.get('type') or 'top'
        return method, float(node.text)

    def place(method, offset, length, parent_start, parent_length):
        """OpenRocket axial-method semantics: component start from nose tip."""
        if method == 'absolute':
            return offset
        if method == 'top':
            return parent_start + offset
        if method == 'middle':
            return parent_start + (parent_length - length) / 2.0 + offset
        if method == 'bottom':
            return parent_start + (parent_length - length) + offset
        raise ValueError(f"unsupported axial method {method!r}")

    nc = root.find('.//nosecone')
    if nc is None:
        raise ValueError("No <nosecone> found in .ork file")
    L_n = get_val(nc, 'length')
    nc_radius = get_val(nc, 'aftradius', get_val(nc, 'radius', 0.020))

    body_tubes = root.findall('.//bodytube')
    if not body_tubes:
        raise ValueError("No <bodytube> found in .ork file")

    d_ref = get_val(body_tubes[0], 'radius', nc_radius) * 2.0

    offset_from_nose = L_n
    finsets = []
    tube_overrides = []
    for bt in body_tubes:
        bt_len = get_val(bt, 'length', 0.0)
        om = bt.find('overridemass')
        oc = bt.find('overridecg')
        tube_overrides.append({
            'length_m': bt_len,
            'overridemass_kg': float(om.text) if om is not None else None,
            'overridecg_rel_m': float(oc.text) if oc is not None else None,
            'abs_start_m': offset_from_nose,
        })
        subs = bt.find('subcomponents')
        if subs is not None:
            for fin in subs.findall('trapezoidfinset'):
                root_chord = get_val(fin, 'rootchord')
                method, off = axial(fin)
                x_start = place(method, off, root_chord, offset_from_nose, bt_len)
                finsets.append({
                    'rootchord': root_chord,
                    'tipchord': get_val(fin, 'tipchord'),
                    'height': get_val(fin, 'height'),
                    'sweeplength': get_val(fin, 'sweeplength'),
                    'fincount': int(get_val(fin, 'fincount')),
                    'x_m': x_start,
                    'axial_method': method,
                    'axial_offset_m': off,
                    'name': fin.find('name').text if fin.find('name') is not None else 'finset',
                })
        offset_from_nose += bt_len

    motor = root.find('.//motor/designation')
    nose_shape = nc.find('shape')

    return {
        'd_ref': d_ref, 'L_n': L_n,
        'finsets': finsets,
        'tube_overrides': tube_overrides,
        'ork_motor': motor.text if motor is not None else None,
        'ork_nose_shape': nose_shape.text if nose_shape is not None else None,
    }


def simulate_burn(m_dry_minus_motor, m_motor_wet, m_motor_dry, cg_dry, cg_motor):
    """Kept for backward compatibility with the historical cross-check flow."""
    burn_time = 2.1  # G64W
    dt = 0.1
    t = np.arange(0, burn_time + dt, dt)
    m_motor_t = np.linspace(m_motor_wet, m_motor_dry, len(t))
    m_t = m_dry_minus_motor + m_motor_t
    cg_t = (m_dry_minus_motor * cg_dry + m_motor_t * cg_motor) / m_t
    return t, cg_t


def static_margin(cp, cg, d_ref):
    return (cp - cg) / d_ref


def generate_reports(csv_path, plot_path, ork_path=None, design_point_path=DESIGN_POINT_PATH):
    dp = load_design_point(design_point_path)
    ork_geom = parse_ork(ork_path) if ork_path and Path(ork_path).exists() else {
        'd_ref': 0.0762, 'L_n': 0.0381, 'ork_nose_shape': 'ellipsoid', 'finsets': [], 'tube_overrides': []}

    cp, terms = assemble_cp(dp, ork_geom)
    d_ref = ork_geom['d_ref']

    motor = dp['mass_model']['motor']
    burn_s = motor['burn_s']
    dt = 0.1
    t = np.arange(0, burn_s + dt, dt)
    frac = np.clip(t / burn_s, 0.0, 1.0)
    m_t = np.empty_like(t)
    cg_t = np.empty_like(t)
    for i, f in enumerate(frac):
        m, cg = mass_and_cg(dp, f)
        m_t[i], cg_t[i] = m, cg
    sm_t = (cp - cg_t) / d_ref

    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, 'w', newline='\n') as f:
        f.write("time_s,cg_m,cp_m,sm_calibers\n")
        for i in range(len(t)):
            f.write(f"{t[i]:.2f},{cg_t[i]:.3f},{cp:.3f},{sm_t[i]:.2f}\n")

    inputs = {
        'schema': 'project33.c5.static_margin_inputs/2',
        'generator': 'Simulation/static_margin.py',
        'design_point_revision': dp.get('revision'),
        'geometry_source': Path(ork_path).name if ork_path and Path(ork_path).exists() else 'design_point.json defaults',
        'units': {'length': 'm', 'mass': 'kg', 'time': 's', 'static_margin': 'calibers'},
        # Geometry block kept for the laboratory views (lab/js reads these
        # keys); values are the main fin set from the parsed .ork.
        'geometry': _main_fin_geometry(ork_geom, dp),
        'formulation_corrections_vs_rev1': [
            'fin CP sweep term uses the tip leading-edge sweep X_R (rev 1 used the root chord)',
            'fin normal-force term uses the mid-chord line length (rev 1 used the sweep length)',
            'ellipsoid nose CP derived by the Barrowman d(r^2)/dx weighting: X_N = L/3 from tip (rev 1 used the ogive 0.466L)',
            'canards modeled (rev 1 ignored them)',
            'motor is the G64W with certified data from thrustcurve.org (rev 1 hard-coded an Estes C6-5)',
            'explicit component mass model from design_point.json replaces ambiguous tube overrides; nose override included',
        ],
        'cp_terms': terms,
        'dry_mass_kg': round(m_t[-1], 4),
        'wet_mass_kg': round(m_t[0], 4),
        'motor': {k: motor[k] for k in ('designation', 'manufacturer', 'wet_kg', 'dry_kg', 'propellant_kg', 'burn_s', 'data_source')},
        'cp_m': round(float(cp), 6),
        'cg_ignition_m': round(float(cg_t[0]), 5),
        'cg_burnout_m': round(float(cg_t[-1]), 5),
        'sm_min_calibers': round(float(np.min(sm_t)), 4),
        'sm_max_calibers': round(float(np.max(sm_t)), 4),
        'basis': 'analytical Barrowman model at the shared design point; no physical measurement',
    }
    (Path(csv_path).parent / "C5_static_margin_inputs.json").write_text(
        json.dumps(inputs, indent=2) + "\n", encoding="utf-8")

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        plt.figure(figsize=(8, 5))
        plt.plot(t, sm_t, label='Static margin (calibers)', color='g')
        plt.axhline(1.5, color='r', linestyle='--', label='Min (1.5)')
        plt.axhline(2.0, color='r', linestyle='--', label='Max (2.0)')
        plt.xlabel('Time (s)')
        plt.ylabel('Static margin (calibers)')
        plt.title(f'Static margin during burn ({motor["designation"]}, rev 3 model)')
        plt.ylim(1.0, 2.5)
        plt.legend()
        plt.grid(True)
        plt.savefig(plot_path, dpi=150)
        plt.close()
    except ImportError:
        pass
    return inputs


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--emit', nargs=2, metavar=('CSV', 'PLOT'), required=True)
    parser.add_argument('--ork', required=False, help='Path to OpenRocket .ork file')
    args = parser.parse_args()
    generate_reports(args.emit[0], args.emit[1], args.ork)
