import numpy as np
import argparse
import json
from pathlib import Path

def compute_clt_properties():
    """
    Computes equivalent E (GPa) for a [0/45/90/-45]s quasi-isotropic CFRP laminate.
    Typical unidirectional lamina properties (e.g. AS4/3501-6):
    E1 = 142 GPa, E2 = 10.3 GPa, G12 = 7.2 GPa, nu12 = 0.27
    Thickness per ply = 0.125 mm
    """
    E1 = 142e9
    E2 = 10.3e9
    G12 = 7.2e9
    nu12 = 0.27
    nu21 = (nu12 * E2) / E1
    
    Q11 = E1 / (1 - nu12 * nu21)
    Q22 = E2 / (1 - nu12 * nu21)
    Q12 = (nu12 * E2) / (1 - nu12 * nu21)
    Q66 = G12
    
    Q = np.array([
        [Q11, Q12, 0],
        [Q12, Q22, 0],
        [0, 0, Q66]
    ])
    
    angles = [0, 45, 90, -45, -45, 90, 45, 0] # [0/45/90/-45]s
    t_ply = 0.125e-3
    t_total = len(angles) * t_ply
    
    A = np.zeros((3, 3))
    
    for theta_deg in angles:
        theta = np.radians(theta_deg)
        c = np.cos(theta)
        s = np.sin(theta)
        
        T = np.array([
            [c**2, s**2, -2*s*c],
            [s**2, c**2, 2*s*c],
            [s*c, -s*c, c**2 - s**2]
        ])
        
        Q_bar = np.linalg.inv(T) @ Q @ (np.linalg.inv(T).T)
        A += Q_bar * t_ply
        
    a = np.linalg.inv(A)
    Ex = 1 / (a[0,0] * t_total)
    Ey = 1 / (a[1,1] * t_total)
    Gxy = 1 / (a[2,2] * t_total)
    
    return Ex / 1e9, Ey / 1e9, Gxy / 1e9

def compute_hinge_fos():
    """
    Computes Factor of Safety for Ti-6Al-4V hinge pin under 50g axial load.
    Ti-6Al-4V Yield Strength = 880 MPa
    Pin diameter = 2 mm -> r = 1 mm
    Fin mass = 154 g (CFRP fin: 130mm root, 110mm tip, 180mm span, 4mm thick).
    Under 50g acceleration -> F = m * a = 0.154 * 50 * 9.81 = 75.5 N
    Assuming pin is in double shear, and experiences some bending moment.
    Simplified bending moment M = F * L / 4, with L = 19.4 mm hinge gap.
    """
    Sy = 880e6 # Yield strength (Pa)
    r = 1e-3
    d = 2 * r
    A = np.pi * r**2
    I = (np.pi * d**4) / 64
    
    F = 0.154 * 50 * 9.81
    L = 19.4e-3
    
    # Shear stress (double shear)
    tau = (F / 2) / A
    
    # Bending stress (point load in middle)
    M = F * L / 4
    sigma_b = (M * r) / I
    
    # Von Mises
    sigma_vm = np.sqrt(sigma_b**2 + 3 * tau**2)
    
    fos = Sy / sigma_vm
    return fos, sigma_vm, tau, sigma_b

def generate_reports(clt_csv_path, fos_json_path):
    """Emit calculation outputs only; interpretation lives in the evidence record."""
    Ex, Ey, Gxy = compute_clt_properties()
    fos, vm, tau, sig = compute_hinge_fos()

    Path(clt_csv_path).parent.mkdir(parents=True, exist_ok=True)
    with open(clt_csv_path, 'w', newline='\n') as f:
        f.write("Property,Value_GPa\n")
        f.write(f"Ex,{Ex:.2f}\n")
        f.write(f"Ey,{Ey:.2f}\n")
        f.write(f"Gxy,{Gxy:.2f}\n")

    record = {
        'schema': 'project33.c8.hinge_fos/1',
        'generator': 'structures/fea_lite.py',
        'units': {'stress': 'MPa', 'force': 'N', 'length': 'mm'},
        'inputs': {'pin_material': 'Ti-6Al-4V', 'yield_strength_MPa': 880.0, 'pin_diameter_mm': 2.0,
                   'fin_mass_kg': 0.154, 'axial_load_g': 50.0, 'hinge_gap_mm': 19.4},
        'load_case': 'double shear with central point-load bending, M = F L / 4',
        'bending_stress_MPa': round(sig / 1e6, 2),
        'shear_stress_MPa': round(tau / 1e6, 2),
        'von_mises_stress_MPa': round(vm / 1e6, 2),
        'factor_of_safety': round(float(fos), 4),
        'reference_values': {'aluminum_6061_T6_modulus_GPa': 69.0,
                             'note': 'handbook comparison value used by the historical C8 note'},
        'basis': 'closed-form calculation; no load test or material coupon was measured',
    }
    Path(fos_json_path).parent.mkdir(parents=True, exist_ok=True)
    Path(fos_json_path).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--emit', nargs=2, metavar=('CLT_CSV', 'FOS_JSON'), required=True)
    args = parser.parse_args()
    generate_reports(args.emit[0], args.emit[1])
