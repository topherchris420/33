"""Deployment-reliability Monte Carlo, revision 2 (militarized Phase 1).

Rebuilds the C7 simulation so that every counted failure mode can occur
(resolves D-013) and runs it at the shared design point (resolves D-010):

- The spring drives the four-bar crank; fin motion follows the verified
  kinematic trace psi(s), r(s) = dpsi/dt2 from mechanism/four_bar.py. The
  fin's equation of motion is integrated in the crank coordinate with the
  exact chain-rule inertia term (I_fin * (r * s_ddot + dr/ds * s_dot^2)).
- Aerodynamic hinge moment follows the fin's effective angle of attack during
  deployment (largest while folded, smallest deployed), not a constant peak.
- Sampled: spring rate and preload, fin mass and inertia, egress speed,
  friction, aero coefficient, trigger latency, stop-angle scatter, and link
  tolerances (through a numerically derived toggle-position gradient).
- Failure modes: stall short of the stop, deployment slower than the window,
  under-deployment when tolerances move the toggle inside the stop, and
  fold-back at the stop when the reflected hold moment exceeds the spring
  preload. Each of these outcomes is reachable on the sampled ranges.
"""

import argparse
import csv
import json
import math
import time
from pathlib import Path

import numpy as np

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / 'mechanism'))
import four_bar  # noqa: E402

RHO = 1.225
DEPLOY_WINDOW_S = 0.150
DEPLOY_TIME_DT = 2.0e-5
PSI_SUCCESS_MIN_DEG = 89.0


def load_design_point(path=REPO_ROOT / 'design_point.json'):
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def kinematic_profile(dp):
    """psi(s), r(s) = dpsi/dt2, and dr/ds from the verified linkage trace.

    s is crank travel in radians from the stowed pose.
    """
    fb = dp['four_bar']
    a, b, c, d = fb['ground_mm'], fb['crank_mm'], fb['coupler_mm'], fb['output_mm']
    trace = four_bar.trace_deployment(a, b, c, d, fb['stowed_crank_deg'],
                                      fb['toggle_crank_deg'] + 15.0)
    t2 = np.array([row[0] for row in trace])
    psi = np.array([row[1] for row in trace])
    s = np.radians(t2 - fb['stowed_crank_deg'])
    # restrict to the monotone deployment segment (up to the toggle)
    itoggle = int(np.argmax(psi))
    s_m, psi_m = s[:itoggle + 1], psi[:itoggle + 1]
    # r = dpsi/dt2 in rad/rad via finite differences on the monotone segment
    r = np.gradient(np.radians(psi_m), s_m, edge_order=2)
    drds = np.gradient(r, s_m, edge_order=2)
    toggle_psi_deg = float(psi_m[-1])
    return s_m, np.radians(psi_m), r, drds, toggle_psi_deg


def toggle_gradient(dp, tol=0.15):
    """Numerical gradient of the toggle fin angle w.r.t. each link length (deg/mm)."""
    fb = dp['four_bar']
    a, b, c, d = fb['ground_mm'], fb['crank_mm'], fb['coupler_mm'], fb['output_mm']

    def toggle_for(deltas):
        a2, b2, c2, d2 = a + deltas[0], b + deltas[1], c + deltas[2], d + deltas[3]
        trace = four_bar.trace_deployment(a2, b2, c2, d2, fb['stowed_crank_deg'],
                                         fb['toggle_crank_deg'] + 15.0, steps=400)
        psis = [row[1] for row in trace]
        return max(psis) if psis else 0.0

    base = toggle_for((0, 0, 0, 0))
    grad = []
    for i in range(4):
        deltas = [0.0] * 4
        deltas[i] = tol
        grad.append((toggle_for(deltas) - base) / tol)
    return np.array(grad), base


def run_monte_carlo(num_trials=10000, seed=33, output_dir=None, design_point_path=REPO_ROOT / 'design_point.json'):
    dp = load_design_point(design_point_path)
    rng = np.random.default_rng(seed)

    s_m, psi_m, r_m, drds_m, toggle_psi_nominal = kinematic_profile(dp)
    grad_toggle, _ = toggle_gradient(dp)
    fb = dp['four_bar']
    fins = dp['main_fins']
    spring = dp['spring']
    regime = dp['flight_regime']

    chord = fins['root_chord_mm'] / 1000.0
    span = fins['span_mm'] / 1000.0
    area = chord * span
    x_cp = 0.25 * chord
    cn_alpha = 2 * math.pi * (2 * span ** 2 / area) / (2 * span ** 2 / area + 2.0)
    cn_cap = 1.2

    stroke_rad = (fb['stop_crank_deg'] - fb['stowed_crank_deg']) * math.pi / 180.0
    preload_rad = spring['preload_beyond_stop_deg'] * math.pi / 180.0
    theta_free = stroke_rad + preload_rad

    # --- sampling -----------------------------------------------------------
    k_s = rng.uniform(0.9, 1.1, num_trials) * spring['rate_n_m_per_rad']
    preload_s = rng.uniform(-3.0, 3.0, num_trials) * math.pi / 180.0 + preload_rad
    m_fin_s = rng.uniform(0.9, 1.1, num_trials) * fins['mass_each_kg']
    i_fin_s = rng.uniform(0.85, 1.15, num_trials) * (1.0 / 3.0) * fins['mass_each_kg'] * span ** 2
    v_egress_s = rng.uniform(8.0, 35.0, num_trials)
    fric_s = rng.uniform(0.05, 0.35, num_trials)
    cn_scale_s = rng.uniform(0.8, 1.2, num_trials)
    latency_s = rng.uniform(0.010, 0.060, num_trials)
    stop_s = rng.normal(90.0, 0.3, num_trials)
    link_deltas = rng.uniform(-0.15, 0.15, (num_trials, 4))
    toggle_shift_deg = link_deltas @ grad_toggle  # deg
    toggle_psi_deg_trial = toggle_psi_nominal + toggle_shift_deg
    accel_s = rng.uniform(20.0, 40.0, num_trials)  # m/s^2 motor acceleration

    n_steps = int(DEPLOY_WINDOW_S / DEPLOY_TIME_DT)
    failures = []
    successes = 0

    # vectorized state
    s = np.zeros(num_trials)
    sd = np.zeros(num_trials)
    running = np.ones(num_trials, dtype=bool)
    reached = np.full(num_trials, np.nan)
    t_reach = np.full(num_trials, np.nan)

    stop_rad = np.radians(stop_s)
    toggle_rad = np.radians(np.minimum(toggle_psi_deg_trial, stop_s + 5.0))
    # effective stop: the fin cannot pass the toggle even if the stop is beyond it
    stop_eff = np.minimum(stop_rad, toggle_rad)

    # interpolants (shared, monotone)
    psi_of_s = lambda sv: np.interp(sv, s_m, psi_m)
    r_of_s = lambda sv: np.interp(sv, s_m, r_m)
    drds_of_s = lambda sv: np.interp(sv, s_m, drds_m)

    for step in range(n_steps):
        idx = np.where(running)[0]
        if idx.size == 0:
            break
        t = step * DEPLOY_TIME_DT
        sv = s[idx]
        psiv = psi_of_s(sv)
        rv = np.maximum(r_of_s(sv), 1e-3)
        drdsv = drds_of_s(sv)

        v = v_egress_s[idx] + accel_s[idx] * (latency_s[idx] + t)
        q = 0.5 * RHO * v ** 2
        alpha_eff = np.radians(90.0) - psiv + np.radians(5.0)
        cn = np.minimum(cn_alpha * np.sin(alpha_eff), cn_cap) * cn_scale_s[idx]
        m_aero = q * area * x_cp * cn

        # spring torque relative to its free position; s = 0 at stowed
        tau_spring = k_s[idx] * np.maximum(theta_free - sv, 0.0)

        rhs = (tau_spring / rv - m_aero - fric_s[idx]) / i_fin_s[idx] - drdsv * sd[idx] ** 2
        sdd = rhs / rv

        sd[idx] = sd[idx] + sdd * DEPLOY_TIME_DT
        s[idx] = sv + sd[idx] * DEPLOY_TIME_DT
        psinew = psi_of_s(s[idx])

        # stop / toggle contact
        contact = psinew >= stop_eff[idx]
        if np.any(contact):
            ci = idx[contact]
            reached[ci] = np.minimum(psinew[contact], stop_eff[ci])
            t_reach[ci] = t + DEPLOY_TIME_DT
            running[ci] = False
            s[ci] = s_m[-1]  # park at end of monotone segment

        # stall detection: velocity collapsed below threshold while short of stop
        stalled = (~contact) & (np.abs(sd[idx]) < 1e-4) & (psinew < np.radians(88.0)) & (t > 0.03)
        if np.any(stalled):
            si = idx[stalled]
            reached[si] = psinew[stalled]
            t_reach[si] = np.inf
            running[si] = False

        # overspeed guard: crank ran past the trace end without the fin flagging
        overrun = (~contact) & (s[idx] > s_m[-1])
        if np.any(overrun):
            oi = idx[overrun]
            reached[oi] = psi_m[-1]
            t_reach[oi] = t + DEPLOY_TIME_DT
            running[oi] = False

    # remaining running trials never reached the stop in the window
    still = np.where(running)[0]
    reached[still] = psi_of_s(s[still])
    t_reach[still] = np.inf

    # static hold check at the stop (reflected gust moment vs spring preload)
    v_hold = regime['max_speed_m_s']
    q_hold = 0.5 * RHO * v_hold ** 2
    gust_alpha = np.radians(rng.uniform(0.0, 15.0, num_trials))
    cn_hold = np.minimum(cn_alpha * np.sin(gust_alpha), cn_cap) * cn_scale_s
    m_hold = q_hold * area * x_cp * cn_hold
    r_stop = float(np.interp(stroke_rad, s_m, r_m))
    r_worst = r_stop * 1.4
    reflected = m_hold * r_worst
    tau_stop = k_s * preload_s
    hold_ok = tau_stop >= reflected

    psi_final_deg = np.degrees(reached)
    deployed_ok = psi_final_deg >= PSI_SUCCESS_MIN_DEG
    fast_enough = np.isfinite(t_reach)
    success = deployed_ok & fast_enough & hold_ok

    successes = int(success.sum())
    for i in np.where(~success)[0]:
        bounded_by_toggle = stop_eff[i] < stop_rad[i] - 1e-9
        if not fast_enough[i] and not np.isfinite(t_reach[i]) and psi_final_deg[i] >= PSI_SUCCESS_MIN_DEG:
            reason = 'window_timeout'
        elif psi_final_deg[i] < PSI_SUCCESS_MIN_DEG and bounded_by_toggle:
            reason = 'toggle_inside_stop_underdeploy'
        elif psi_final_deg[i] < PSI_SUCCESS_MIN_DEG and np.isfinite(t_reach[i]):
            # the fin reached its own stop; the stop or its tolerance sit below the
            # acceptance angle (stop scatter tail), so the deployment is short
            reason = 'stop_angle_under_tolerance'
        elif psi_final_deg[i] < PSI_SUCCESS_MIN_DEG:
            reason = 'stalled_short'
        elif not hold_ok[i]:
            reason = 'foldback_at_stop'
        else:
            reason = 'window_timeout'
        failures.append({
            'trial': int(i),
            'psi_final_deg': round(float(psi_final_deg[i]), 2),
            't_reach_s': round(float(t_reach[i]), 4) if np.isfinite(t_reach[i]) else None,
            'v_egress': round(float(v_egress_s[i]), 2),
            'k_spring': round(float(k_s[i]), 3),
            'friction_n_m': round(float(fric_s[i]), 3),
            'reason': reason,
        })

    success_rate = successes / num_trials if num_trials else 0.0

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        csv_path = out / "C7_reliability.csv"
        with open(csv_path, 'w', newline='\n') as f:
            writer = csv.DictWriter(f, fieldnames=['trial', 'psi_final_deg', 't_reach_s', 'v_egress',
                                                  'k_spring', 'friction_n_m', 'reason'],
                                    lineterminator='\n')
            writer.writeheader()
            writer.writerows(failures)

        record = {
            'schema': 'project33.c7.run_record/2',
            'generator': 'Simulation/reliability_sweep.py',
            'design_point_revision': dp.get('revision'),
            'trials': num_trials,
            'successes': successes,
            'failures': len(failures),
            'seed': seed,
            'rng': 'numpy.random.default_rng',
            'kinematics': 'verified four-bar trace psi(s), r(s)=dpsi/dt2 from mechanism/four_bar.py',
            'sampled_ranges': {
                'k_spring_n_m_rad': [round(0.9 * spring['rate_n_m_per_rad'], 2), round(1.1 * spring['rate_n_m_per_rad'], 2)],
                'preload_beyond_stop_deg': ['nominal 30 minus/plus 3', None],
                'fin_mass_kg': [round(0.9 * fins['mass_each_kg'], 4), round(1.1 * fins['mass_each_kg'], 4)],
                'v_egress_m_s': [8.0, 35.0],
                'friction_n_m': [0.05, 0.35],
                'cn_scale': [0.8, 1.2],
                'trigger_latency_ms': [10.0, 60.0],
                'stop_angle_deg': 'N(90, 0.3)',
                'link_tolerance_mm': [-0.15, 0.15],
            },
            'failure_modes_modeled': ['stalled_short', 'window_timeout', 'toggle_inside_stop_underdeploy',
                                      'stop_angle_under_tolerance', 'foldback_at_stop'],
            'failure_counts': {r: sum(1 for f_ in failures if f_['reason'] == r) for r in
                               ('stalled_short', 'window_timeout', 'toggle_inside_stop_underdeploy',
                                'stop_angle_under_tolerance', 'foldback_at_stop')},
            'success_criterion': f'psi_final >= {PSI_SUCCESS_MIN_DEG} deg within {DEPLOY_WINDOW_S} s and static hold at stop',
            'fixed_parameters': {
                'fin_chord_m': chord, 'fin_span_m': span, 'fin_area_m2': area,
                'x_cp_from_le_m': x_cp, 'cn_alpha_per_rad': round(cn_alpha, 3), 'cn_cap': cn_cap,
                'rho_kg_m3': RHO, 'hold_speed_m_s': v_hold, 'r_stop': round(r_stop, 4),
                'r_worst_hold': round(r_worst, 4),
            },
            'model_structure_notes': [
                'fin equation of motion integrated in the crank coordinate with the chain-rule inertia term',
                'aero hinge moment follows effective angle of attack during deployment (peak while folding, not constant)',
                'link tolerances enter through a numerically derived toggle-position gradient',
                'fold-back judged statically at the stop: reflected gust moment vs spring preload',
            ],
            'success_fraction': success_rate,
            'basis': 'numerical simulation; no physical deployment was observed',
        }
        (out / "C7_run_record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    return success_rate, failures


# Legacy single-deployment helper retained for compatibility; the militarized
# design point does not use it (D-013 documented its defects).
def simulate_deployment(k_spring, theta_toggle, v_egress, I_fin, Cm_alpha, timer_latency_ms):
    theta_deg = math.degrees(theta_toggle)
    return theta_deg, 0.0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--emit', required=True)
    args = parser.parse_args()

    print("Running militarized Monte Carlo (10,000 trials)...")
    t0 = time.time()
    sr, fails = run_monte_carlo(num_trials=10000, output_dir=Path(args.emit).parent)
    print(f"Finished in {time.time() - t0:.1f}s. Success rate: {sr * 100:.3f}% "
          f"({len(fails)} failures)")
