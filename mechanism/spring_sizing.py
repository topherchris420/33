"""Torsion-spring sizing for the Phase 1 militarized fin-deployment linkage.

Revision 2 (militarized). The spring drives the four-bar CRANK (pivot A), not
the fin directly. Sizing is done at the shared design point
(design_point.json, revision 2026-11-14-phase1), resolving D-010 and D-011:

1. LOCK requirement: at the deployed stop the spring preload torque must exceed
   the fin hinge moment reflected through the linkage by a factor of safety.
   The reflected fraction is the kinematic ratio dpsi/dt2 at the stop pose,
   from mechanism/four_bar.py (near-toggle, nominal 0.363).
2. ENERGY requirement: spring work over the crank stroke must cover the fin's
   kinetic energy at the target deployment time plus aerodynamic and friction
   work, with a deployment safety factor.
3. k_min is the max of the two; the supplied spring must exceed it by at least
   20 percent (requirement R-C6-MARGIN).

The legacy fin-direct sizing helper (compute_k_min) is kept for the historical
C6 record and tests; the militarized design point does not use it.
"""

import json
import math
import argparse
from pathlib import Path

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / 'mechanism'))
import four_bar  # noqa: E402


def load_design_point(path=REPO_ROOT / 'design_point.json'):
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def compute_k_min(v_egress, c_fin, S_fin, t_deploy, h_fin, m_fin, Cm_alpha_max, damping_ratio=0.7):
    """
    Legacy fin-direct minimum torsion spring rate k (N·m/rad). Kept for the
    historical C6 record; the militarized design sizes the spring on the crank.
    """
    if v_egress <= 0:
        raise ValueError("v_egress must be positive")
    if m_fin <= 0:
        raise ValueError("m_fin must be positive")
    if c_fin <= 0 or S_fin <= 0 or t_deploy <= 0 or h_fin <= 0 or Cm_alpha_max <= 0 or damping_ratio < 0 or damping_ratio >= 1:
        raise ValueError("All physical quantities must be positive, and damping_ratio in [0, 1)")

    rho = 1.225  # kg/m^3

    # Aerodynamic hinge moment
    M_aero = 0.5 * rho * (v_egress ** 2) * S_fin * c_fin * Cm_alpha_max

    # Fin inertia (thin rod about end)
    I_fin = (1.0 / 3.0) * m_fin * (h_fin ** 2)

    # Required angular acceleration to reach 90 deg (pi/2 rad) in t_deploy
    alpha = math.pi / (t_deploy ** 2)

    # Required spring torque (undamped)
    k_min_undamped = I_fin * alpha + M_aero

    # Including damping
    k_min = k_min_undamped / (1 - damping_ratio)

    return k_min


def validate_design_margin(k_required, k_supplied):
    margin = (k_supplied - k_required) / k_required if k_required > 0 else float('inf')
    meets_20_pct = margin >= 0.20
    return margin, meets_20_pct


# --- Militarized crank-spring sizing -----------------------------------------

RHO = 1.225            # kg/m^3
SF_LOCK = 2.0           # spring preload vs reflected hold moment
SF_DEPLOY = 1.5         # spring work vs deployment energy
R_TOLERANCE_FACTOR = 1.4  # worst-case back-drive ratio growth under link tolerance
GUST_ALPHA_RAD = 0.262  # 15 deg effective angle of attack for the hold case
FRICTION_N_M = 0.15      # hinge + pin friction, assumed (sampled in C7)
DEPLOY_TIME_S = 0.080    # target time to the 90 deg stop


def fin_inertia(m_fin, span):
    """Thin-plate fin about its hinge (root), span measured from the hinge."""
    return (1.0 / 3.0) * m_fin * span ** 2


def fin_normal_force_coefficient(alpha_rad, aspect_ratio):
    """Finite-wing lift slope estimate for the hold-moment case."""
    cn_alpha = 2 * math.pi * aspect_ratio / (aspect_ratio + 2.0)
    return cn_alpha * alpha_rad


def militarized_sizing(design_point=None):
    """Crank-spring sizing record at the shared design point."""
    dp = design_point or load_design_point()
    fb = dp['four_bar']
    fins = dp['main_fins']
    regime = dp['flight_regime']
    spring = dp['spring']

    a, b, c, d = fb['ground_mm'], fb['crank_mm'], fb['coupler_mm'], fb['output_mm']
    chord = fins['root_chord_mm'] / 1000.0
    span = fins['span_mm'] / 1000.0
    area = chord * span
    m_fin = fins['mass_each_kg']
    v_max = regime['max_speed_m_s']
    v_deploy = regime['deploy_start_speed_m_s']

    # Kinematics from the verified linkage trace
    trace = four_bar.trace_deployment(a, b, c, d, fb['stowed_crank_deg'],
                                       fb['toggle_crank_deg'] + 15.0)
    r_stop = four_bar.backdrive_ratio(trace, fb['fin_stop_deg'])
    stroke_crank_rad = (fb['stop_crank_deg'] - fb['stowed_crank_deg']) * math.pi / 180.0
    preload_rad = spring['preload_beyond_stop_deg'] * math.pi / 180.0
    theta_free = stroke_crank_rad + preload_rad

    # Fin properties
    I_fin = fin_inertia(m_fin, span)
    aspect_ratio = 2.0 * span ** 2 / area

    # --- Hold (lock) requirement -------------------------------------------
    q_max = 0.5 * RHO * v_max ** 2
    cn_gust = fin_normal_force_coefficient(GUST_ALPHA_RAD, aspect_ratio)
    n_gust = cn_gust * q_max * area
    x_cp_from_le = 0.25 * chord          # subsonic quarter-chord
    m_hold = n_gust * x_cp_from_le         # fin hinge moment at max q, gust alpha
    r_worst = r_stop * R_TOLERANCE_FACTOR
    tau_stop_required = SF_LOCK * r_worst * m_hold
    k_lock = tau_stop_required / preload_rad

    # --- Deployment energy requirement ------------------------------------
    # Kinetic energy at the target deployment time (constant-acceleration model)
    omega_final = 2.0 * (fb['fin_stop_deg'] * math.pi / 180.0) / DEPLOY_TIME_S
    ke = 0.5 * I_fin * omega_final ** 2
    # Conservative aerodynamic work: peak hinge moment at deploy-start speed
    # (legacy C6 form) applied over half the stroke.
    m_aero_deploy = 0.5 * RHO * v_deploy ** 2 * area * chord * 0.8
    w_aero = 0.5 * m_aero_deploy * (fb['fin_stop_deg'] * math.pi / 180.0)
    w_fric = FRICTION_N_M * (fb['fin_stop_deg'] * math.pi / 180.0)
    energy_needed = ke + w_aero + w_fric
    spring_work = lambda k: 0.5 * k * (theta_free ** 2 - preload_rad ** 2)
    k_energy = SF_DEPLOY * energy_needed * 2.0 / (theta_free ** 2 - preload_rad ** 2)

    k_min = max(k_lock, k_energy)
    k_supplied = spring['rate_n_m_per_rad']
    margin, meets = validate_design_margin(k_min, k_supplied)

    return {
        'schema': 'project33.c6.design_point/2',
        'generator': 'mechanism/spring_sizing.py',
        'design_point_revision': dp.get('revision'),
        'units': {'spring_rate': 'N*m/rad', 'torque': 'N*m', 'energy': 'J',
                  'margin_fraction': '(k_supplied - k_min) / k_min'},
        'mechanism': {
            'backdrive_ratio_at_stop': round(r_stop, 4),
            'backdrive_ratio_worst_case': round(r_worst, 4),
            'crank_stroke_rad': round(stroke_crank_rad, 4),
            'preload_beyond_stop_rad': round(preload_rad, 4),
        },
        'hold_case': {
            'v_max_m_s': v_max,
            'gust_alpha_deg': round(math.degrees(GUST_ALPHA_RAD), 1),
            'fin_cn_at_gust': round(cn_gust, 3),
            'fin_normal_force_n': round(n_gust, 2),
            'hinge_moment_n_m': round(m_hold, 3),
            'required_stop_torque_n_m': round(tau_stop_required, 3),
            'k_lock_n_m_rad': round(k_lock, 3),
        },
        'deployment_case': {
            'target_time_s': DEPLOY_TIME_S,
            'fin_inertia_kg_m2': round(I_fin, 6),
            'kinetic_energy_j': round(ke, 3),
            'aero_work_j': round(w_aero, 3),
            'friction_work_j': round(w_fric, 3),
            'energy_needed_j': round(energy_needed, 3),
            'k_energy_n_m_rad': round(k_energy, 3),
        },
        'k_min_N_m_rad': round(k_min, 4),
        'k_supplied_N_m_rad': k_supplied,
        'k_supplied_basis': 'specified catalog-scale music-wire torsion spring; not a measured spring rate',
        'margin_fraction': round(margin, 6),
        'meets_20_pct_margin': meets,
        'spring_torques': {
            'at_stowed_n_m': round(k_supplied * theta_free, 2),
            'at_stop_n_m': round(k_supplied * preload_rad, 2),
            'stowage_note': 'stowed preload is carried by the launch rail/canister; fins are spring-loaded toward deployment whenever unrestrained',
        },
        'model_assumptions': [
            'spring drives the four-bar crank; fin loads reach the crank through the kinematic ratio dpsi/dt2 (virtual work)',
            'lock case uses max flight dynamic pressure with a 15 deg gust angle of attack and a 1.4x tolerance growth on the back-drive ratio',
            'deployment energy uses constant-acceleration kinematics to the stop in 80 ms plus conservative (C6-form) aerodynamic work',
            'hinge friction assumed 0.15 N*m (sampled in the C7 Monte Carlo)',
        ],
        'basis': 'analytical sizing at the shared design point; no spring has been measured',
    }


# Historical design point, preserved for the legacy record and tests.
DESIGN_POINT = {
    'v_egress': 205.0, 'c_fin': 0.120, 'S_fin': 0.0216, 't_deploy': 0.050,
    'h_fin': 0.180, 'm_fin': 0.154, 'Cm_alpha_max': 0.8, 'damping_ratio': 0.7,
}
K_SUPPLIED = 220.0  # N·m/rad, stated in the source paper; no spring has been characterized


def design_point_record():
    """Legacy fin-direct record (schema /1), kept for traceability."""
    k_min = compute_k_min(**DESIGN_POINT)
    margin, _ = validate_design_margin(k_min, K_SUPPLIED)
    return {
        'schema': 'project33.c6.design_point/1',
        'generator': 'mechanism/spring_sizing.py',
        'units': {'v_egress': 'm/s', 'c_fin': 'm', 'S_fin': 'm^2', 't_deploy': 's', 'h_fin': 'm',
                  'm_fin': 'kg', 'k': 'N*m/rad', 'margin_fraction': '(k_supplied - k_min) / k_min'},
        'inputs': DESIGN_POINT,
        'model_assumptions': [
            'constant angular acceleration to 90 deg within t_deploy',
            'thin-rod fin inertia about its end',
            'peak aerodynamic hinge moment applied throughout deployment',
            'damping handled by dividing by (1 - damping_ratio), a heuristic inflation',
            'air density fixed at 1.225 kg/m^3',
        ],
        'k_min_N_m_rad': round(k_min, 4),
        'k_supplied_N_m_rad': K_SUPPLIED,
        'k_supplied_basis': 'stated in source paper; not a measured spring rate',
        'margin_fraction': round(margin, 6),
    }


def sensitivity_sweep(output_path):
    v_egress_vals = range(150, 251, 10)
    Cm_alpha_max_vals = [round(0.5 + 0.1 * i, 1) for i in range(8)]

    results = []

    for v in v_egress_vals:
        for cm in Cm_alpha_max_vals:
            k = compute_k_min(
                v_egress=float(v),
                c_fin=0.120,
                S_fin=0.0216,
                t_deploy=0.050,
                h_fin=0.180,
                m_fin=0.154,
                Cm_alpha_max=cm,
                damping_ratio=0.7
            )

            results.append({
                'v_egress_m_s': float(v),
                'Cm_alpha_max': float(cm),
                'k_min_N_m_rad': round(k, 2)
            })

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', newline='\n') as f:
        json.dump(results, f, indent=2)
    (output_file.parent / "C6_design_point.json").write_text(
        json.dumps(design_point_record(), indent=2) + '\n', encoding='utf-8')
    (output_file.parent / "C6_design_point_militarized.json").write_text(
        json.dumps(militarized_sizing(), indent=2) + '\n', encoding='utf-8')

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np

        V, CM = np.meshgrid(list(v_egress_vals), Cm_alpha_max_vals)
        K = np.zeros_like(V, dtype=float)

        for i in range(V.shape[0]):
            for j in range(V.shape[1]):
                K[i, j] = compute_k_min(
                    v_egress=float(V[i, j]),
                    c_fin=0.120,
                    S_fin=0.0216,
                    t_deploy=0.050,
                    h_fin=0.180,
                    m_fin=0.154,
                    Cm_alpha_max=float(CM[i, j]),
                    damping_ratio=0.7
                )

        plt.figure(figsize=(8, 6))
        cp = plt.contourf(V, CM, K, cmap='viridis')
        plt.colorbar(cp, label='Minimum Spring Rate k (N·m/rad)')
        plt.xlabel('Egress Velocity (m/s)')
        plt.ylabel('Max Hinge Moment Coefficient (Cm_alpha)')
        plt.title('Spring Sizing Sensitivity Sweep')

        plot_path = output_file.parent / 'C6_spring_sweep_plot.png'
        plt.savefig(plot_path, dpi=150)
        plt.close()
    except ImportError:
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--emit', required=True)
    args = parser.parse_args()
    sensitivity_sweep(args.emit)
