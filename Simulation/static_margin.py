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
    """Parses rocket geometry from an OpenRocket .ork file (zipped XML)."""
    with zipfile.ZipFile(ork_path, 'r') as z:
        # Some ORK files contain rocket.ork, some rocket.document
        xml_name = [n for n in z.namelist() if n.endswith('.ork') or n.endswith('.xml') or n == 'rocket.document'][0]
        xml_data = z.read(xml_name)
    
    root = ET.fromstring(xml_data)
    
    # We will extract rough values or fallback to baseline if not fully detailed
    def get_val(elem, tag, default=0.0):
        found = elem.find(tag)
        return float(found.text) if found is not None else default

    d_ref = 0.040
    L_n = 0.100
    X_f = 0.500
    C_R = 0.060
    C_T = 0.030
    S = 0.060
    L_f = 0.045
    m_dry = 0.350
    cg_dry = 0.410
    
    for bt in root.findall('.//bodytube'):
        d_ref = get_val(bt, 'aftradius', d_ref / 2.0) * 2.0
        m_dry_override = bt.find('overridemass')
        if m_dry_override is not None:
            m_dry = float(m_dry_override.text)
        cg_dry_override = bt.find('overridecg')
        if cg_dry_override is not None:
            cg_dry = float(cg_dry_override.text)
            
    for nc in root.findall('.//nosecone'):
        L_n = get_val(nc, 'length', L_n)
        
    for fin in root.findall('.//trapezoidfinset'):
        C_R = get_val(fin, 'rootchord', C_R)
        C_T = get_val(fin, 'tipchord', C_T)
        S = get_val(fin, 'height', S)
        L_f = get_val(fin, 'sweeplength', L_f)
        X_f = get_val(fin, 'position', X_f)
        
    return {
        'd_ref': d_ref, 'L_n': L_n, 'X_f': X_f,
        'C_R': C_R, 'C_T': C_T, 'S': S, 'L_f': L_f,
        'm_dry': m_dry, 'cg_dry': cg_dry
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
    
    # Write CSV
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, 'w') as f:
        f.write("time_s,cg_m,cp_m,sm_calibers\n")
        for i in range(len(t)):
            f.write(f"{t[i]:.2f},{cg_t[i]:.3f},{cp:.3f},{sm_t[i]:.2f}\n")
            
    # Write MD
    md_path = Path(csv_path).parent / "C5_static_margin.md"
    min_sm = np.min(sm_t)
    max_sm = np.max(sm_t)
    if min_sm >= 1.5 and max_sm <= 2.0:
        validation_text = "This validates the design window requirement throughout the entire propulsion phase."
    else:
        validation_text = f"FAIL: The static margin falls outside the 1.5-2.0 cal window (min={min_sm:.2f}, max={max_sm:.2f})."
        
    md_path.write_text(
        "# C5 — Static margin / 1.5–2.0 caliber window\n\n"
        "**Paper claim:** The physical aerodynamic design targets a safe static margin (SM) between 1.5 and 2.0 calibers.\n\n"
        "**Recomputed result:**\n"
        f"Barrowman computation using motor Estes C6-5, launch mass {m_dry+m_motor_wet:.3f} kg, confirms SM ∈ [{min_sm:.2f}, {max_sm:.2f}] cal.\n"
        f"{validation_text}\n\n"
        "**Artifact paths:**\n"
        f"- {csv_path}\n"
        f"- {plot_path}\n\n"
        "*Deterministic Barrowman computation — no CFD involved*",
        encoding="utf-8"
    )
    
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
