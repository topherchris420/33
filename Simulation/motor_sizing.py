"""Phase 4 military motor sizing (all MODELED).

Sizes a military-class solid motor for the 1-3 km tactical envelope with
margin, replacing the AeroTech G64W (118.8 N*s) used through Phase 3.

Method: bisection on total impulse using the same drag model as the CEP
simulation, requiring the BALLISTIC impact (unguided, best elevation) to
reach the target range plus a 10 percent envelope margin. The motor class
assumptions (burn time, mass ratio) come from the composite-airframe mass
model below; every number is MODELED.

Also emits a RASP .eng thrust curve file so the motor can be imported into
OpenRocket, and the budgets for the MIL-STD-810-style environmental checks.
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / 'Simulation'))
import cep_model  # noqa: E402

G = 9.80665


def phase4_mass_model():
    """Phase 4 composite-airframe mass model (kg, positions from nose).

    Changes vs the Phase 1-3 model (MIL-DEV-007):
    - tubes: G-10/epoxy 2.0 mm walls instead of 2.54 mm fiberglass (C8 spec)
    - load-path metallics stay 7075-T6 (hinges, rings, warhead case)
    - militarized motor: 76 mm class, sized by this script
    """
    return {
        'components': [
            {'name': 'nose_and_warhead_bay', 'mass_kg': 0.317, 'cg_m': 0.030},
            {'name': 'forward_body_composite', 'mass_kg': 0.560, 'cg_m': 0.158},
            {'name': 'aft_body_composite_and_mounts', 'mass_kg': 0.280, 'cg_m': 0.550},
            {'name': 'main_fins_molded_cfrp', 'mass_kg': 0.480, 'cg_m': 0.520},
        ],
        'note': 'composite tubes shave ~0.13 kg vs the Phase 1 fiberglass model; '
                'fins unchanged (already molded CFRP); warhead bay unchanged',
    }


def motor_from_impulse(total_impulse, burn_s, propellant_isp_s=200.0):
    """Motor with the given total impulse; propellant mass from a
    conservative solid-propellant specific impulse of 200 s."""
    propellant = total_impulse / (propellant_isp_s * G)
    case = 0.45 + 0.25 * propellant  # 76 mm case + nozzle, scaled
    return {
        'total_impulse_ns': total_impulse,
        'burn_s': burn_s,
        'wet_kg': round(propellant + case, 3),
        'dry_kg': round(case, 3),
    }


def envelope_for(total_impulse, burn_s, cd_a, trials_elev=range(20, 70, 5)):
    """Best ballistic range over elevations for the given motor."""
    mm = phase4_mass_model()
    m0 = sum(c['mass_kg'] for c in mm['components']) + 0.15  # +avionics/battery misc
    motor = motor_from_impulse(total_impulse, burn_s)
    m0 += motor['wet_kg'] - 0.15
    m_bo = m0 - (motor['wet_kg'] - motor['dry_kg'])
    best = 0.0
    for elev in trials_elev:
        impact = cep_model.ballistic_impact(float(elev), motor, cd_a, m0, m_bo)
        best = max(best, impact)
    return best, motor, m0, m_bo


def size_motor(target_range_m=3000.0, margin=1.10, burn_s=2.0, cd_a=0.0022):
    """Bisection on total impulse for the required envelope with margin."""
    lo, hi = 600.0, 4000.0
    for _ in range(18):
        mid = 0.5 * (lo + hi)
        reach, *_ = envelope_for(mid, burn_s, cd_a)
        if reach >= target_range_m * margin:
            hi = mid
        else:
            lo = mid
    impulse = hi
    reach, motor, m0, m_bo = envelope_for(impulse, burn_s, cd_a)
    return {
        'impulse_ns': round(impulse, 0),
        'burn_s': burn_s,
        'avg_thrust_n': round(impulse / burn_s, 0),
        'propellant_kg': round(motor['wet_kg'] - motor['dry_kg'], 3),
        'motor_wet_kg': motor['wet_kg'],
        'motor_dry_kg': motor['dry_kg'],
        'round_wet_kg': round(m0, 3),
        'round_burnout_kg': round(m_bo, 3),
        'ballistic_envelope_m': round(reach, 0),
        'target_plus_margin_m': round(target_range_m * margin, 0),
        'initial_accel_g': round((impulse / burn_s) / m0 / G, 1),
        'burnout_speed_mps_est': round(impulse / ((m0 + m_bo) / 2) * 0.88, 0),
    }


def rasp_eng(spec, designation='MIL-33', diameter_mm=76.0, length_mm=420.0):
    """RASP .eng file text for the sized motor (average-thrust curve)."""
    thrust = spec['avg_thrust_n']
    lines = [
        f'{designation} {int(diameter_mm)} {int(length_mm)} 1.0 4.0 0.015 {spec["propellant_kg"]:.4f} {spec["motor_dry_kg"]:.4f}',
        'PREDICTED single thrust plateau; not a measured curve',
    ]
    n = 20
    for i in range(n + 1):
        t = spec['burn_s'] * i / n
        # plateau with ignition ramp and tail-off
        if i < 2:
            f = thrust * (i / 2)
        elif i > n - 2:
            f = thrust * ((n - i) / 2)
        else:
            f = thrust
        lines.append(f'{t:.3f} {f:.1f}')
    return '\n'.join(lines) + '\n'


def environmental_budgets(spec):
    """MIL-STD-810-style budgets (METHOD-derived targets, not test results)."""
    m0 = spec['round_wet_kg']
    fin_mass_kg = 0.120
    fin_cg_from_hinge_m = 0.11
    # launch shock: initial acceleration on the fin set
    a_launch = spec['initial_accel_g'] * G
    shock_load_n = fin_mass_kg * a_launch * 1.5  # 1.5 shock factor
    hinge_m_n = shock_load_n * fin_cg_from_hinge_m
    # canard servo load: dynamic pressure at burnout speed, 15 deg alpha
    rho = 1.225
    v = spec['burnout_speed_mps_est']
    q = 0.5 * rho * v * v
    canard_area = 0.0254 * 0.0508
    cn = 0.95
    canard_load_n = cn * q * canard_area
    return {
        'launch_shock': {
            'initial_accel_g': spec['initial_accel_g'],
            'fin_hinge_load_n': round(shock_load_n, 1),
            'fin_hinge_moment_n_m': round(hinge_m_n, 2),
            'budget': '3x motor initial acceleration on the fin set and canards, '
                      'per MIL-STD-810 method 516 style shock budgets',
        },
        'vibration': {
            'canard_load_n_at_burnout_15deg': round(canard_load_n, 1),
            'canard_servo_torque_n_m': round(canard_load_n * 0.0127, 2),
            'budget': 'random vibration 20-2000 Hz per MIL-STD-810 method 514 style; '
                      'canard servos must hold position under the burnout dynamic load',
        },
        'storage_temperature': {
            'range_c': [-40, 60],
            'budget': 'MIL-STD-810 method 503 style storage; motor, spring, and '
                      'electronics rated over the range; PLA+ parts are superseded '
                      '(MIL-DEV-007) precisely because they leave this window',
        },
    }


def build_record():
    spec = size_motor()
    return {
        'schema': 'project33.mil.motor/1',
        'generator': 'Simulation/motor_sizing.py',
        'evidence_class': 'MODELED',
        'mass_model': phase4_mass_model(),
        'motor': spec,
        'eng_file': 'Simulation/MIL-33.eng (RASP average-thrust curve, PREDICTED)',
        'environmental_budgets': environmental_budgets(spec),
        'basis': 'bisection sizing on the CEP drag model; no motor has been built or static-fired',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--emit', required=True)
    parser.add_argument('--emit-eng', required=False)
    args = parser.parse_args()
    rec = build_record()
    out = Path(args.emit)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=2) + '\n', encoding='utf-8')
    eng_path = Path(args.emit_eng) if args.emit_eng else out.parent / 'MIL-33.eng'
    eng_path.write_text(rasp_eng(rec['motor']), encoding='utf-8')
    print('wrote', out, 'and', eng_path)
    print(json.dumps(rec['motor'], indent=1))
    print(json.dumps(rec['environmental_budgets'], indent=1))
