"""Phase 3 CEP Monte Carlo (all MODELED).

Six-degree-free (3-DOF point mass + attitude channel) engagement simulation
of the guided round against a static target point, including:

- the SAME proportional-navigation law implemented in the rocket firmware
  (Firmware/Rocket/src/guidance.h), re-implemented independently here so the
  firmware law is cross-checked rather than trusted,
- canard authority limits with first-order servo lag,
- GPS position error and latency (the GPS-aided IMU model),
- gyro-drift attitude error growing over the flight,
- steady wind plus gusts,
- target-coordinate designation error (operator grid precision).

Motors: two configurations are reported.
- G64W (the committed Phase 1/6 inert-flight motor; ~0.5 km envelope), and
- PHASE4-MOTOR: a preliminary military-class solid motor (800 N*s, 2.0 s
  burn, 0.75 kg wet) required to reach the 1-3 km tactical envelope. Its final
  sizing happens in Phase 4; it is an assumption here and is labeled as such.

CEP is the median radial miss distance over seeded trials.
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]

G = 9.80665
RHO0 = 1.225


def atmosphere(h):
    rho = RHO0 * math.exp(-h / 8500.0)
    return rho


def drag_accel(v_vec, rho, cd_a, m):
    v = math.sqrt(v_vec[0] ** 2 + v_vec[1] ** 2 + v_vec[2] ** 2)
    if v < 1e-6:
        return (0.0, 0.0, 0.0)
    f = 0.5 * rho * cd_a * v * v / m
    return (-f * v_vec[0] / v, -f * v_vec[1] / v, -f * v_vec[2] / v)


def pn_command(pos, vel, tgt, max_lat):
    """Same PN law as Guidance::pnCommand (ENU)."""
    l = (tgt[0] - pos[0], tgt[1] - pos[1], tgt[2] - pos[2])
    l2 = l[0] * l[0] + l[1] * l[1] + l[2] * l[2]
    if l2 < 25.0:
        return (0.0, 0.0, 0.0)
    ld = (-vel[0], -vel[1], -vel[2])
    w = ((l[1] * ld[2] - l[2] * ld[1]) / l2,
         (l[2] * ld[0] - l[0] * ld[2]) / l2,
         (l[0] * ld[1] - l[1] * ld[0]) / l2)
    n = 3.0
    # a = N * (omega x V): proportional navigation (the cross order matters;
    # V x omega steers AWAY from the target -- caught by the clean-trial check)
    a = (n * (w[1] * vel[2] - w[2] * vel[1]),
         n * (w[2] * vel[0] - w[0] * vel[2]),
         n * (w[0] * vel[1] - w[1] * vel[0]))
    mag = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2)
    if mag > max_lat and mag > 0:
        s = max_lat / mag
        a = (a[0] * s, a[1] * s, a[2] * s)
    return a


def ballistic_impact(elev_deg, motor, cd_a, m0, m_bo, dt=0.02):
    """Ballistic (unguided) ground impact distance for a launch elevation."""
    v0 = 12.0
    vel = [v0 * math.cos(math.radians(elev_deg)), 0.0, v0 * math.sin(math.radians(elev_deg))]
    pos = [0.0, 0.0, 0.0]
    t = 0.0
    burn = motor['burn_s']
    thrust_avg = motor['total_impulse_ns'] / burn
    m_prop = motor['wet_kg'] - motor['dry_kg']
    while t < 300.0 and (pos[2] > 0.0 or t < 1.0):
        m = m0 if t < burn else m_bo
        thrust = thrust_avg / m if t < burn else 0.0
        sp = max(math.sqrt(vel[0] ** 2 + vel[1] ** 2 + vel[2] ** 2), 1e-6)
        rho = atmosphere(pos[2])
        d = drag_accel(vel, rho, cd_a, m)
        a = (thrust * vel[0] / sp + d[0], thrust * vel[1] / sp + d[1],
             thrust * vel[2] / sp + d[2] - G)
        vel = [vel[0] + a[0] * dt, vel[1] + a[1] * dt, vel[2] + a[2] * dt]
        pos = [pos[0] + vel[0] * dt, pos[1] + vel[1] * dt, pos[2] + vel[2] * dt]
        t += dt
        if pos[2] <= 0.0 and t > 1.0:
            break
    return pos[0]


def solve_elevation(rng, motor, tgt_range_m, cd_a, m0, m_bo):
    """Launcher fire-control solution: elevation whose ballistic impact best
    matches the target range (the standard range-card aim). Bisection over
    elevation; drag makes low-arc solutions non-monotonic near the top, so
    search the ascending branch only."""
    lo, hi = 5.0, 65.0
    best_elev, best_err = 45.0, 1e9
    for elev in range(5, 66, 5):
        impact = ballistic_impact(float(elev), motor, cd_a, m0, m_bo)
        err = abs(impact - tgt_range_m)
        # track the best elevation on the ascending branch (before max range)
        if err < best_err:
            best_elev, best_err = float(elev), err
        if impact > tgt_range_m:
            hi = float(elev)
            lo = float(elev - 5)
            break
    lo, hi = max(5.0, lo - 2.5), min(65.0, hi + 2.5)
    for _ in range(12):
        mid = 0.5 * (lo + hi)
        impact = ballistic_impact(mid, motor, cd_a, m0, m_bo)
        if abs(impact - tgt_range_m) < best_err:
            best_elev, best_err = mid, abs(impact - tgt_range_m)
        if impact > tgt_range_m:
            hi = mid
        else:
            lo = mid
    return best_elev, best_err


def run_trial(rng, motor, tgt_range_m, tgt_err_m, wind_max, cd_a, m0, m_bo,
             guidance_on=True, dt=0.02, launch_elev=50.0):
    """One engagement. Returns miss distance (m) or None if the round cannot fly."""
    v0 = 12.0
    # per-round aim scatter, applied to BOTH guided and ballistic
    aim_error_deg = rng.normal(0.0, 0.3)
    launch_elev_actual = launch_elev + aim_error_deg
    # ENU: east, north, up. Elevation is in the east-up plane.
    vel = [v0 * math.cos(math.radians(launch_elev_actual)), 0.0, v0 * math.sin(math.radians(launch_elev_actual))]

    # truth state: position (ENU), velocity
    pos = [0.0, 0.0, 0.0]
    # target at the given slant range along the launch bearing, on the ground
    tgt = [tgt_range_m, 0.0, 0.0]
    tgt_err = rng.normal(0.0, tgt_err_m / 1.1774, 3)  # CEP -> sigma
    tgt = [tgt[0] + tgt_err[0], tgt[1] + tgt_err[1], tgt[2] + tgt_err[2]]
    # wind (steady + gust, horizontal)
    wind_dir = rng.uniform(0, 2 * math.pi)
    wind_v = rng.uniform(0, wind_max)
    wind = (wind_v * math.cos(wind_dir), wind_v * math.sin(wind_dir), 0.0)

    # sensor models
    gps_sigma = 2.5          # m, position noise
    gps_period = 0.2         # s (5 Hz, u-blox configurable default class)
    gps_latency = rng.uniform(0.3, 1.0)
    gps_vel_sigma = 0.3      # m/s, velocity noise (carrier-smoothed)
    attitude_bias = rng.normal(0.0, math.radians(2.0))   # rad, attitude error
    gyro_drift_rate = rng.uniform(0.5, 4.0) / 60.0       # rad/s
    servo_tau = 0.12         # s
    max_lat = 9.6            # m/s^2, canard authority (Phase 3 derivation)
    # gravity bias: canards carry part of the weight in the vertical channel
    # so PN does not spend its authority fighting droop
    grav_bias = 0.75 * G
    # LOS-rate deadband: do not steer on sensor noise
    omega_deadband = 0.002  # rad/s
    # per-round motor scatter (thrust), applied to BOTH guided and ballistic
    thrust_scale = rng.uniform(0.96, 1.04)

    # perceived state (what the guidance law sees)
    nav_pos = list(pos)
    nav_vel = list(vel)
    canard_accel = [0.0, 0.0, 0.0]

    t = 0.0
    burn = motor['burn_s']
    thrust_avg = thrust_scale * motor['total_impulse_ns'] / burn
    m_prop = motor['wet_kg'] - motor['dry_kg']
    last_gps = -10.0

    while t < 120.0:
        m = m0 if t < burn else (m0 - m_prop if t < burn + 1e-9 else m_bo)
        if t < burn:
            thrust = thrust_avg / m
        else:
            thrust = 0.0
        rho = atmosphere(pos[2])

        # dynamics: thrust along velocity direction (zero-effort after burnout,
        # gravity, drag, wind-relative airspeed, commanded lateral accel)
        ax_body = thrust * vel[0] / max(math.sqrt(vel[0] ** 2 + vel[1] ** 2 + vel[2] ** 2), 1e-6)
        ay_body = thrust * vel[1] / max(math.sqrt(vel[0] ** 2 + vel[1] ** 2 + vel[2] ** 2), 1e-6)
        az_body = thrust * vel[2] / max(math.sqrt(vel[0] ** 2 + vel[1] ** 2 + vel[2] ** 2), 1e-6)

        v_air = (vel[0] - wind[0], vel[1] - wind[1], vel[2] - wind[2])
        d = drag_accel(v_air, rho, cd_a, m)
        a = (ax_body + d[0] + canard_accel[0],
             ay_body + d[1] + canard_accel[1],
             az_body + d[2] + canard_accel[2] - G)

        vel = [vel[0] + a[0] * dt, vel[1] + a[1] * dt, vel[2] + a[2] * dt]
        pos = [pos[0] + vel[0] * dt, pos[1] + vel[1] * dt, pos[2] + vel[2] * dt]
        t += dt

        if pos[2] <= 0.0 and t > burn:
            miss = math.sqrt((pos[0] - tgt[0]) ** 2 + (pos[1] - tgt[1]) ** 2)
            return miss

        # navigation update: GPS at its period with latency and noise
        if t - last_gps >= gps_period:
            last_gps = t
            nav_pos = [pos[0] + rng.normal(0, gps_sigma),
                       pos[1] + rng.normal(0, gps_sigma),
                       pos[2] + rng.normal(0, gps_sigma)]
            nav_vel = [vel[0] + rng.normal(0, gps_vel_sigma),
                       vel[1] + rng.normal(0, gps_vel_sigma),
                       vel[2] + rng.normal(0, gps_vel_sigma)]

        # guidance after burnout plus a short settling gate
        if guidance_on and t > burn + 0.2 and math.sqrt(nav_vel[0] ** 2 + nav_vel[1] **  2 + nav_vel[2] ** 2) > 15.0:
            l = (tgt[0] - nav_pos[0], tgt[1] - nav_pos[1], tgt[2] - nav_pos[2])
            l2 = l[0] * l[0] + l[1] * l[1] + l[2] * l[2]
            ld = (-nav_vel[0], -nav_vel[1], -nav_vel[2])
            w = ((l[1] * ld[2] - l[2] * ld[1]) / l2,
                 (l[2] * ld[0] - l[0] * ld[2]) / l2,
                 (l[0] * ld[1] - l[1] * ld[0]) / l2)
            w_mag = math.sqrt(w[0] ** 2 + w[1] ** 2 + w[2] ** 2)
            if w_mag > omega_deadband or l2 < 400.0:
                a_cmd = pn_command(nav_pos, nav_vel, tgt, max_lat)
            else:
                a_cmd = (0.0, 0.0, 0.0)
            # first-order canard/servo response with attitude-error leakage:
            # a fraction of the command leaks through as a cross-axis error.
            leak = attitude_bias + gyro_drift_rate * t
            ax = a_cmd[0] * math.cos(leak) - a_cmd[1] * math.sin(leak)
            ay = a_cmd[0] * math.sin(leak) + a_cmd[1] * math.cos(leak)
            az = a_cmd[2] + (grav_bias if l2 > 400.0 else 0.0)
            az = min(az, max_lat)
            alpha = dt / servo_tau
            canard_accel[0] += alpha * (ax - canard_accel[0])
            canard_accel[1] += alpha * (ay - canard_accel[1])
            canard_accel[2] += alpha * (az - canard_accel[2])
    return None


def run_motor_set(rng, motor, m0, m_bo, cd_a, ranges=(1000, 2000, 3000), trials=400):
    out = {}
    for r in ranges:
        # launcher fire-control solution for this range (range-card aim)
        elev, aim_err = solve_elevation(rng, motor, r, cd_a, m0, m_bo)
        misses_g = [run_trial(rng, motor, r, 10.0, 8.0, cd_a, m0, m_bo, True, launch_elev=elev)
                   for _ in range(trials)]
        misses_g = [m_ for m_ in misses_g if m_ is not None]
        misses_b = [run_trial(rng, motor, r, 10.0, 8.0, cd_a, m0, m_bo, False, launch_elev=elev)
                    for _ in range(trials)]
        misses_b = [m_ for m_ in misses_b if m_ is not None]
        if misses_g:
            cep_g = float(np.median(misses_g))
        else:
            cep_g = None
        cep_b = float(np.median(misses_b)) if misses_b else None
        out[f'{r}_m'] = {
            'launch_elevation_deg': round(elev, 1),
            'aim_solution_error_m': round(aim_err, 1),
            'guided_trials': len(misses_g),
            'cep_guided_m': round(cep_g, 1) if cep_g is not None else None,
            'cep_ballistic_m': round(cep_b, 1) if cep_b is not None else None,
            'guided_over_ballistic': (round(cep_b / cep_g, 2)
                                      if cep_g and cep_b and cep_g > 0 else None),
        }
    return out


def build_record(trials=400, seed=33):
    rng = np.random.default_rng(seed)
    # airframe drag: Cd ~ 0.55 (canards + fins + body), A = pi*0.0381^2
    cd_a = 0.55 * math.pi * 0.0381 ** 2

    g64w = {'total_impulse_ns': 118.8, 'burn_s': 2.1, 'wet_kg': 0.151, 'dry_kg': 0.088}
    phase4 = {'total_impulse_ns': 800.0, 'burn_s': 2.0, 'wet_kg': 0.75, 'dry_kg': 0.35}

    # mass models: G64W on the 1.90 kg Phase 2 round; Phase 4 motor adds mass
    m0_g = 1.903
    m_bo_g = 1.840
    m0_p4 = 1.903 - 0.151 + 0.75
    m_bo_p4 = m0_p4 - 0.40

    record = {
        'schema': 'project33.mil.cep/1',
        'generator': 'Simulation/cep_model.py',
        'evidence_class': 'MODELED',
        'trials': trials,
        'seed': seed,
        'guidance_law': 'proportional navigation, N=3, identical to Firmware/Rocket/src/guidance.h (independent re-implementation)',
        'error_budget': {
            'gps_position_sigma_m': 2.5,
            'gps_period_s': 0.2,
            'gps_velocity_sigma_m_s': 0.3,
            'gps_latency_s': [0.3, 1.0],
            'target_designation_cep_m': 10.0,
            'attitude_bias_sigma_rad': 0.035,
            'gyro_drift_deg_per_min': [0.5, 4.0],
            'wind_m_s': [0, 8],
            'servo_tau_s': 0.12,
            'canard_authority_m_s2': 9.6,
            'gravity_bias_fraction': 0.75,
            'los_rate_deadband_rad_s': 0.002,
            'motor_thrust_scatter': [0.96, 1.04],
            'launcher_aim_error_sigma_deg': 0.3,
        },
        'G64W_inert_motor': {
            'note': 'committed Phase 6 inert-flight motor; the 1-3 km tactical envelope is beyond its reach',
            'motor': g64w,
            'masses_kg': [m0_g, m_bo_g],
            'results': run_motor_set(rng, g64w, m0_g, m_bo_g, cd_a, ranges=(300,), trials=trials),
        },
        'PHASE4_MOTOR': {
            'note': 'PRELIMINARY military-class motor assumption for the 1-3 km envelope (800 N*s, 2.0 s, 0.75 kg wet); final sizing is the Phase 4 deliverable',
            'motor': phase4,
            'masses_kg': [round(m0_p4, 3), round(m_bo_p4, 3)],
            'results': run_motor_set(rng, phase4, m0_p4, m_bo_p4, cd_a, trials=trials),
        },
        'basis': 'numerical Monte Carlo; no round has flown; every error term is an assumed budget, not a measurement',
    }
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--emit', required=True)
    parser.add_argument('--trials', type=int, default=400)
    args = parser.parse_args()
    rec = build_record(trials=args.trials)
    out = Path(args.emit)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=2) + '\n', encoding='utf-8')
    print('wrote', out)
    print(json.dumps({k: v['results'] for k, v in rec.items() if isinstance(v, dict) and 'results' in v}, indent=1))
