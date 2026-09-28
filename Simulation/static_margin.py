import argparse
import json
import numpy as np
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

# Pure Barrowman Equations
def barrowman_cp(L_n, d, L_b, d_f, d_r, L_c, L_f, X_b, X_f, C_R, C_T, S, R):
    """
    Computes CP position (distance from nose tip).
    All dimensions in meters.
    
    L_n = Length of nose
    d   = Diameter at base of nose
    L_b = Length of body
    d_f = Diameter at front of transition
    d_r = Diameter at rear of transition
    L_c = Length of transition
    L_f = Length of fin mid-chord line
    X_b = Distance from nose tip to front of transition
    X_f = Distance from nose tip to fin root leading edge
    C_R = Fin root chord
    C_T = Fin tip chord
    S   = Fin span
    R   = Radius of body at fins (d_r / 2)
    """
    
    # 1. Nose Cone Term
    C_N_N = 2.0
    X_N = 0.466 * L_n # Assuming ogive
    
    # 2. Conical Transition Term
    C_N_T = 2 * ((d_r / d)**2 - (d_f / d)**2)
    if C_N_T == 0:
        X_T = 0
    else:
        X_T = X_b + (L_c / 3) * (1 + (1 - d_f/d_r) / (1 - (d_f/d_r)**2))
        
    # 3. Fin Term
    C_N_F = (1 + R / (R + S)) * (4 * 4 * (S / d)**2) / (1 + np.sqrt(1 + (2 * L_f / (C_R + C_T))**2))
    
    X_F = X_f + (C_R / 3) * ( (C_R + 2 * C_T) / (C_R + C_T) ) + (1 / 6) * ( (C_R + C_T - C_R * C_T / (C_R + C_T)) )
    
    # Total
    C_N_R = C_N_N + C_N_T + C_N_F
    X_CP = (C_N_N * X_N + C_N_T * X_T + C_N_F * X_F) / C_N_R
    
    return X_CP

def simulate_burn(m_dry, m_motor_wet, m_motor_dry, cg_dry, cg_motor):
    """
    Simulates CG movement over a generic solid motor burn.
    """
    burn_time = 1.8 # Estes C6-5
    dt = 0.1
    t = np.arange(0, burn_time + dt, dt)
    
    m_motor_t = np.linspace(m_motor_wet, m_motor_dry, len(t))
    m_t = m_dry + m_motor_t
    
    cg_t = (m_dry * cg_dry + m_motor_t * cg_motor) / m_t
    return t, cg_t

def static_margin(cp, cg, d_ref):
    return (cp - cg) / d_ref

def parse_ork(ork_path):
    """Parses rocket geometry from an OpenRocket .ork file (zipped XML).

    Walks the XML hierarchy to compute absolute positions from the nose tip,
    picks the primary (largest-span) fin set, and aggregates dry mass across
    all body tubes.  Raises ValueError if critical geometry is missing.
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

    # --- Nose cone ---
    nc = root.find('.//nosecone')
    if nc is None:
        raise ValueError("No <nosecone> found in .ork file")
    L_n = get_val(nc, 'length')
    nc_radius = get_val(nc, 'aftradius', get_val(nc, 'radius', 0.020))

    # --- Body tubes: walk in document order, accumulate length for absolute positions ---
    body_tubes = root.findall('.//bodytube')
    if not body_tubes:
        raise ValueError("No <bodytube> found in .ork file")

    d_ref = get_val(body_tubes[0], 'radius', nc_radius) * 2.0

    # Aggregate dry mass: sum of all overridemass fields
    total_dry_mass = 0.0
    mass_sources = 0
    weighted_cg_sum = 0.0
    offset_from_nose = L_n  # running absolute position from nose tip

    # Collect body tubes with their absolute offsets
    bt_offsets = []
    for bt in body_tubes:
        bt_offsets.append(offset_from_nose)
        bt_len = get_val(bt, 'length', 0.0)

        override_mass = bt.find('overridemass')
        override_cg = bt.find('overridecg')
        if override_mass is not None:
            m = float(override_mass.text)
            total_dry_mass += m
            mass_sources += 1
            if override_cg is not None:
                # overridecg is relative to the component, convert to absolute
                weighted_cg_sum += m * (offset_from_nose + float(override_cg.text))
            else:
                weighted_cg_sum += m * (offset_from_nose + bt_len / 2.0)

        offset_from_nose += bt_len

    if mass_sources == 0:
        total_dry_mass = 0.350  # fallback
        weighted_cg_sum = total_dry_mass * 0.410
    m_dry = total_dry_mass
    cg_dry = weighted_cg_sum / m_dry if m_dry > 0 else 0.410

    # --- Fins: find the primary (largest-span) trapezoidfinset ---
    best_fin = None
    best_span = -1.0
    best_fin_abs_x = 0.0

    for bt_idx, bt in enumerate(body_tubes):
        bt_abs_offset = bt_offsets[bt_idx]
        subs = bt.find('subcomponents')
        if subs is None:
            continue
        for fin in subs.findall('trapezoidfinset'):
            span = get_val(fin, 'height', 0.0)
            if span > best_span:
                best_span = span
                best_fin = fin
                fin_pos_in_tube = get_val(fin, 'position', 0.0)
                best_fin_abs_x = bt_abs_offset + fin_pos_in_tube

    if best_fin is None:
        raise ValueError("No <trapezoidfinset> found in .ork file")

    C_R = get_val(best_fin, 'rootchord')
    C_T = get_val(best_fin, 'tipchord')
    S = get_val(best_fin, 'height')
    L_f = get_val(best_fin, 'sweeplength')
    X_f = best_fin_abs_x

    motor = root.find('.//motor/designation')
    nose_shape = nc.find('shape')

    return {
        'd_ref': d_ref, 'L_n': L_n, 'X_f': X_f,
        'C_R': C_R, 'C_T': C_T, 'S': S, 'L_f': L_f,
        'm_dry': m_dry, 'cg_dry': cg_dry,
        'ork_motor': motor.text if motor is not None else None,
        'ork_nose_shape': nose_shape.text if nose_shape is not None else None,
    }

def generate_reports(csv_path, plot_path, ork_path=None):
    # Default Geometry
    d_ref = 0.040 # 40mm body tube
    L_n = 0.100 # 100mm nose
    d = d_ref
    X_f = 0.500 # Fins at rear
    C_R = 0.060
    C_T = 0.030
    S = 0.060
    L_f = 0.045
    R = d_ref / 2
    
    m_dry = 0.350 # 350g
    cg_dry = 0.410 # 410mm from nose
    
    ork_geom = {}
    if ork_path and Path(ork_path).exists():
        ork_geom = parse_ork(ork_path)
        d_ref = ork_geom['d_ref']
        L_n = ork_geom['L_n']
        d = d_ref
        m_dry = ork_geom['m_dry']
        cg_dry = ork_geom['cg_dry']
        R = d_ref / 2
        X_f = ork_geom['X_f']
        C_R = ork_geom['C_R']
        C_T = ork_geom['C_T']
        S = ork_geom['S']
        L_f = ork_geom['L_f']
        
    cp = barrowman_cp(L_n, d, 0, d, d, 0, L_f, 0, X_f, C_R, C_T, S, R)
    
    m_motor_wet = 0.024
    m_motor_dry = 0.011
    cg_motor = 0.520 # 520mm from nose
    
    t, cg_t = simulate_burn(m_dry, m_motor_wet, m_motor_dry, cg_dry, cg_motor)
    sm_t = static_margin(cp, cg_t, d_ref)
    
    # Write CSV (LF line endings on every platform)
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, 'w', newline='\n') as f:
        f.write("time_s,cg_m,cp_m,sm_calibers\n")
        for i in range(len(t)):
            f.write(f"{t[i]:.2f},{cg_t[i]:.3f},{cp:.3f},{sm_t[i]:.2f}\n")

    # Structured record of what the calculation actually used. No verdict is
    # written here: interpretation belongs to the reviewed evidence record.
    inputs = {
        'schema': 'project33.c5.static_margin_inputs/1',
        'generator': 'Simulation/static_margin.py',
        'geometry_source': Path(ork_path).name if ork_path and Path(ork_path).exists() else 'built-in defaults',
        'units': {'length': 'm', 'mass': 'kg', 'time': 's', 'static_margin': 'calibers'},
        'geometry': {'d_ref': d_ref, 'L_n': L_n, 'X_f': X_f, 'C_R': C_R, 'C_T': C_T,
                     'S': S, 'L_f_sweeplength': L_f},
        'dry_mass_kg': m_dry, 'dry_cg_m': cg_dry,
        'motor_assumed': {'designation': 'Estes C6-5 (hard-coded)', 'wet_kg': m_motor_wet,
                          'dry_kg': m_motor_dry, 'cg_m': cg_motor, 'burn_s': 1.8},
        'ork_motor_designation': ork_geom.get('ork_motor'),
        'ork_nose_shape': ork_geom.get('ork_nose_shape'),
        'nose_cp_coefficient_used': 0.466,
        'formula_notes': [
            'Fin CP term uses C_R/3*(C_R+2C_T)/(C_R+C_T) as the sweep term; the textbook Barrowman '
            'form uses the tip leading-edge sweep distance X_R in that position.',
            'Fin normal-force term uses the sweep length where the textbook form uses the mid-chord line length.',
            'Nose CP coefficient 0.466 is the ogive value.',
            'Only body-tube override masses are summed for dry mass.',
        ],
        'cp_m': round(float(cp), 6),
        'sm_min_calibers': round(float(np.min(sm_t)), 4),
        'sm_max_calibers': round(float(np.max(sm_t)), 4),
    }
    (Path(csv_path).parent / "C5_static_margin_inputs.json").write_text(
        json.dumps(inputs, indent=2) + "\n", encoding="utf-8")

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        plt.figure(figsize=(8, 5))
        plt.plot(t, sm_t, label='Static Margin (calibers)', color='g')
        plt.axhline(1.5, color='r', linestyle='--', label='Min (1.5)')
        plt.axhline(2.0, color='r', linestyle='--', label='Max (2.0)')
        plt.xlabel('Time (s)')
        plt.ylabel('Static Margin (calibers)')
        plt.title('Static Margin during Motor Burn (Estes C6-5)')
        plt.ylim(1.0, 2.5)
        plt.legend()
        plt.grid(True)
        plt.savefig(plot_path, dpi=150)
        plt.close()
    except ImportError:
        pass
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--emit', nargs=2, metavar=('CSV', 'PLOT'), required=True)
    parser.add_argument('--ork', required=False, help='Path to OpenRocket .ork file')
    args = parser.parse_args()
    generate_reports(args.emit[0], args.emit[1], args.ork)
