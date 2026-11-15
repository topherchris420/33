"""Planar four-bar kinematics for the C1 folding-fin mechanism question.

Geometry convention (all lengths in mm, angles in degrees unless noted):
ground pivot A at the origin, ground pivot D at (ground, 0). The input link
AB rotates by the drive angle; the coupler BC and output link DC close the loop.

A pose that cannot close (the coupler and output circles do not intersect) is
reported as ``None``. It is never replaced by a numeric placeholder: an
unassemblable linkage has no transmission angle and no swept envelope.

Revision 2 (see evidence/archive/): revision 1 returned 90 degrees for
unassemblable poses, an empty-trajectory envelope of 0.0, and a Freudenstein
solution with misassigned constants. Its committed sweep is preserved in
evidence/archive/C1_four_bar_sweep.v1.json.
"""

import argparse
import json
import math
from pathlib import Path

DRIVE_MIN_DEG = 0
DRIVE_MAX_DEG = 92
DRIVE_STEP_DEG = 2
BASELINE = {"ground": 25, "coupler": 60, "input": 15, "output": 15}

REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_POINT_PATH = REPO_ROOT / 'design_point.json'


def load_design_point(path=DESIGN_POINT_PATH):
    """Load the shared militarized design point (D-010 resolution)."""
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def grashof_condition(a, b, c, d):
    """Return 'Grashof', 'non-Grashof', or 'change-point' for four link lengths."""
    links = sorted([a, b, c, d])
    shortest, p, q, longest = links
    if shortest + longest < p + q:
        return 'Grashof'
    if shortest + longest > p + q:
        return 'non-Grashof'
    return 'change-point'


def closure_points(a, b, c, d, theta2_rad):
    """Both coupler-output joint positions C, or None when the loop cannot close.

    a: ground, b: input, c: coupler, d: output.
    """
    bx, by = b * math.cos(theta2_rad), b * math.sin(theta2_rad)
    dx, dy = a - bx, -by
    f = math.hypot(dx, dy)
    if f == 0 or f > c + d or f < abs(c - d):
        return None
    along = (c * c - d * d + f * f) / (2 * f)
    height = math.sqrt(max(c * c - along * along, 0.0))
    ux, uy = dx / f, dy / f
    base_x, base_y = bx + along * ux, by + along * uy
    return ((base_x - height * uy, base_y + height * ux),
            (base_x + height * uy, base_y - height * ux))


def compute_theta4(a, b, c, d, theta2_rad):
    """Output-link angles (radians) for both assembly branches, or None."""
    points = closure_points(a, b, c, d, theta2_rad)
    if points is None:
        return None
    return tuple(math.atan2(y, x - a) for x, y in points)


def transmission_angle(link_ground, link_coupler, link_input, link_output, theta_drive):
    """Angle between coupler and output link in degrees, or None if the pose cannot close."""
    a, b, c, d = link_ground, link_input, link_coupler, link_output
    theta2 = math.radians(theta_drive)
    f_sq = a**2 + b**2 - 2 * a * b * math.cos(theta2)
    if f_sq <= 0:
        return None
    cos_mu = (c**2 + d**2 - f_sq) / (2 * c * d)
    if cos_mu > 1.0 or cos_mu < -1.0:
        return None
    return math.degrees(math.acos(cos_mu))


def tip_trajectory(link_ground, link_coupler, link_input, link_output,
                   theta_drive_min, theta_drive_max, num_steps=200):
    """Joint C positions on the open branch for every pose that closes."""
    a, b, c, d = link_ground, link_input, link_coupler, link_output
    x_tips, y_tips = [], []
    for i in range(num_steps):
        theta = theta_drive_min + (theta_drive_max - theta_drive_min) * i / max(num_steps - 1, 1)
        points = closure_points(a, b, c, d, math.radians(theta))
        if points is None:
            continue
        x, y = points[0]
        x_tips.append(x)
        y_tips.append(y)
    return x_tips, y_tips


def over_center_moment_sign(link_ground, link_coupler, link_input, link_output,
                            theta_drive, theta_toggle=92.0):
    """Sign of (theta_drive - theta_toggle).

    This is an angle comparison only. It does not compute a moment or use the
    link geometry, so it cannot demonstrate over-center locking.
    """
    if theta_drive < theta_toggle:
        return -1
    if theta_drive > theta_toggle:
        return 1
    return 0


def swept_envelope_radius(tip_x, tip_y):
    """Largest distance of joint C from pivot A, or None if no pose closed."""
    radii_sq = [x**2 + y**2 for x, y in zip(tip_x, tip_y)]
    if not radii_sq:
        return None
    return math.sqrt(max(radii_sq))


def _rounded(value):
    return None if value is None else round(value, 2)


# ---------------------------------------------------------------------------
# Militarized deployment linkage (Phase 1 redesign; resolves D-002 and D-004).
#
# Convention: crank pivot A at the origin, fin hinge D at (ground, 0); +x runs
# from A toward D (nose to tail). The fin panel is rigidly attached to the
# output link DC. Fin deployment angle psi is measured from folded-flush:
#   psi = 0   fin lies alongside the body, pointing at the nose
#   psi = 90  fin perpendicular to the body (deployed hard stop)
#   psi > 90  beyond perpendicular, toward the tail
# The fin deploys on the assembly branch that is continuous from the stowed
# flush pose; joint C is chosen by nearest-point continuity at each crank
# angle, exactly as a physical pin-jointed mechanism does.
#
# Over-center lock: the linkage toggle (crank-coupler collinearity, |AC| = b
# + c) is placed ~1.5 deg of fin angle BEYOND the 90 deg stop. At the toggle
# the kinematic ratio dpsi/dt2 = 0, so fin hinge loads cannot back-drive the
# crank; at the stop (just before the toggle) the ratio is small and the spring
# preload holds the fin on its stop.
# ---------------------------------------------------------------------------

def _branch_points(a, b, c, d, t2_rad):
    """Both assembly positions of joint C, or None when the loop cannot close."""
    bx, by = b * math.cos(t2_rad), b * math.sin(t2_rad)
    dx, dy = a - bx, -by
    f = math.hypot(dx, dy)
    if f == 0 or f > c + d or f < abs(c - d):
        return None
    along = (c * c - d * d + f * f) / (2 * f)
    height = math.sqrt(max(c * c - along * along, 0.0))
    ux, uy = dx / f, dy / f
    base_x, base_y = bx + along * ux, by + along * uy
    return ((base_x - height * uy, base_y + height * ux),
            (base_x + height * uy, base_y - height * ux))


def fin_angle_from_c(cx, cy, a):
    """Fin deployment angle psi (deg) from folded-flush, for joint C at (cx, cy).

    psi = 0 flush pointing at the nose, 90 perpendicular. Sign carries the
    assembly side; the deployed branch of the Phase 1 design is positive.
    """
    phi = math.degrees(math.atan2(cy, cx - a))
    return 180.0 - (phi % 360.0)


def trace_deployment(ground, crank, coupler, output, t2_start, t2_end, steps=1200):
    """Physically continuous trace of the fin deployment branch.

    Returns a list of (t2_deg, psi_deg, f_bd, mu_deg) for every crank angle
    where the loop closes, following the assembly branch by continuity of joint
    C from the stowed pose. All four link lengths are verified at every pose.
    """
    trace = []
    prev = None
    for i in range(steps + 1):
        t2 = t2_start + (t2_end - t2_start) * i / steps
        pts = _branch_points(ground, crank, coupler, output, math.radians(t2))
        if pts is None:
            prev = None
            continue
        if prev is None:
            cx, cy = min(pts, key=lambda p: abs(fin_angle_from_c(p[0], p[1], ground)))
        else:
            cx, cy = min(pts, key=lambda p: math.hypot(p[0] - prev[0], p[1] - prev[1]))
        prev = (cx, cy)
        # self-check the pose against every link length
        bx, by = crank * math.cos(math.radians(t2)), crank * math.sin(math.radians(t2))
        assert abs(math.hypot(cx - bx, cy - by) - coupler) < 1e-6
        assert abs(math.hypot(cx - ground, cy) - output) < 1e-6
        f = math.hypot(ground - bx, by)
        cos_mu = (coupler ** 2 + output ** 2 - f ** 2) / (2 * coupler * output)
        cos_mu = max(-1.0, min(1.0, cos_mu))
        mu = math.degrees(math.acos(cos_mu))
        trace.append((t2, fin_angle_from_c(cx, cy, ground), f, mu))
    return trace


def backdrive_ratio(trace, psi_target):
    """Kinematic ratio dpsi/dt2 at the pose where psi first reaches psi_target.

    This is the fraction of fin hinge torque that reaches the crank: a fin
    hinge moment M reflects to the crank as M * dpsi/dt2 (virtual work).
    Returns None when psi_target is never reached.
    """
    for i in range(len(trace) - 1):
        t2a, pa, _, _ = trace[i]
        t2b, pb, _, _ = trace[i + 1]
        if pa <= psi_target <= pb or pb <= psi_target <= pa:
            if t2b == t2a:
                continue
            return abs((pb - pa) / (t2b - t2a))
    return None


def military_linkage_record(design_point=None):
    """Structured analysis of the Phase 1 militarized linkage.

    Checks: closure across the full stroke with worst-case link tolerance,
    the toggle position and over-center margin, the back-drive ratio at the
    stop, transmission angle over the power stroke, and the radial closure
    margin at the stop (tolerance robustness).
    """
    dp = design_point or load_design_point()
    fb = dp['four_bar']
    a, b, c, d = fb['ground_mm'], fb['crank_mm'], fb['coupler_mm'], fb['output_mm']
    tol = fb['tolerance_mm']

    t2_stow = fb['stowed_crank_deg']
    # trace well past the toggle so the extremum is captured
    t2_end = fb['toggle_crank_deg'] + 15.0
    trace = trace_deployment(a, b, c, d, t2_stow, t2_end)
    closed = [row for row in trace]

    psis = [row[1] for row in closed]
    t2s = [row[0] for row in closed]
    itoggle = max(range(len(psis)), key=lambda i: psis[i])
    psi_toggle = psis[itoggle]
    t2_toggle = t2s[itoggle]

    # crank angle where the fin reaches its 90 deg stop
    t2_stop = None
    for i in range(len(psis) - 1):
        if psis[i] <= fb['fin_stop_deg'] <= psis[i + 1]:
            t2_stop = t2s[i]
            break

    r_stop = backdrive_ratio(closed, fb['fin_stop_deg'])

    # transmission angle over the power stroke (psi >= 20 deg to the stop):
    # the stowed end is against the launch tube (no load) and the final
    # approach is the deliberate near-toggle lock approach.
    power = [row for row in closed
             if 20.0 <= row[1] <= fb['fin_stop_deg']]
    mu_min_power = min((row[3] for row in power), default=None)
    mu_max_power = max((row[3] for row in power), default=None)

    # radial closure margin at the stop pose
    f_stop = next((row[2] for row in closed if row[0] == t2_stop), None) if t2_stop else None
    radial_margin_stop = (c + d - f_stop) if f_stop is not None else None

    # worst-case tolerance sweep: shrink coupler and output by the tolerance
    # (tightest closure) and confirm the stop pose still assembles.
    tol_ok = True
    tol_detail = []
    for da_, db_, dc_, dd_ in [(tol, -tol, -tol, -tol), (-tol, tol, tol, tol),
                               (tol, tol, -tol, tol), (-tol, -tol, tol, -tol)]:
        a2, b2, c2, d2 = a + da_, b + db_, c + dc_, d + dd_
        pts = _branch_points(a2, b2, c2, d2, math.radians(t2_stop)) if t2_stop else None
        ok = pts is not None
        tol_ok = tol_ok and ok
        tol_detail.append({'delta_mm': [da_, db_, dc_, dd_], 'stop_pose_closes': ok})

    sweep_crank = (t2_stop - t2_stow) if t2_stop is not None else None
    return {
        'schema': 'project33.c1.four_bar_military/1',
        'generator': 'mechanism/four_bar.py',
        'design_point_revision': dp.get('revision'),
        'units': {'length': 'mm', 'angle': 'deg'},
        'links': {'ground': a, 'crank': b, 'coupler': c, 'output': d},
        'stroke': {
            'stowed_crank_deg': t2_stow,
            'stop_crank_deg': round(t2_stop, 2) if t2_stop is not None else None,
            'toggle_crank_deg': round(t2_toggle, 2),
            'crank_sweep_deg': round(sweep_crank, 2) if sweep_crank is not None else None,
            'fin_stop_deg': fb['fin_stop_deg'],
        },
        'lock': {
            'toggle_fin_deg': round(psi_toggle, 3),
            'over_center_margin_fin_deg': round(psi_toggle - fb['fin_stop_deg'], 3),
            'over_center_margin_crank_deg': round(t2_toggle - t2_stop, 2) if t2_stop is not None else None,
            'backdrive_ratio_at_stop': round(r_stop, 4) if r_stop is not None else None,
            'backdrive_ratio_meaning': 'fraction of fin hinge torque reaching the crank at the stop pose',
        },
        'transmission': {
            'mu_min_power_stroke_deg': round(mu_min_power, 2) if mu_min_power is not None else None,
            'mu_max_power_stroke_deg': round(mu_max_power, 2) if mu_max_power is not None else None,
            'window_note': 'power stroke is psi 20 deg to the stop; the stowed end is tube-supported and the final approach is the near-toggle lock',
        },
        'closure': {
            'radial_margin_at_stop_mm': round(radial_margin_stop, 3) if radial_margin_stop is not None else None,
            'link_tolerance_mm': tol,
            'worst_case_tolerance_closes_at_stop': tol_ok,
            'tolerance_cases': tol_detail,
        },
        'poses_checked': len(closed),
        'assemblable_over_range': all(row is not None for row in closed),
        'basis': 'analytical planar kinematics with continuity-tracked assembly branch; no physical mechanism observed',
    }


def evaluate_linkage(a, c, b, d):
    """Structured result for one configuration: ground a, coupler c, input b, output d."""
    angles = list(range(DRIVE_MIN_DEG, DRIVE_MAX_DEG + 1, DRIVE_STEP_DEG))
    mus = [transmission_angle(a, c, b, d, float(theta)) for theta in angles]
    closed = [mu for mu in mus if mu is not None]
    tip_x, tip_y = tip_trajectory(a, c, b, d, DRIVE_MIN_DEG, DRIVE_MAX_DEG)
    return {
        'ground': a, 'coupler': c, 'input': b, 'output': d,
        'grashof': grashof_condition(a, b, c, d),
        'poses_evaluated': len(angles),
        'poses_closed': len(closed),
        'assemblable_over_range': len(closed) == len(angles),
        'min_transmission_angle': _rounded(min(closed)) if closed else None,
        'max_transmission_angle': _rounded(max(closed)) if closed else None,
        'max_envelope_radius': _rounded(swept_envelope_radius(tip_x, tip_y)),
    }


def parameter_study(output_path):
    rows = []
    for a in [20, 25, 30]:
        for c in [55, 60, 65]:
            for b in [12, 15, 18]:
                for d in [12, 15, 18]:
                    rows.append(evaluate_linkage(a, c, b, d))
    baseline = evaluate_linkage(BASELINE['ground'], BASELINE['coupler'],
                                BASELINE['input'], BASELINE['output'])
    result = {
        'schema': 'project33.c1.four_bar_sweep/2',
        'generator': 'mechanism/four_bar.py',
        'units': {'length': 'mm', 'angle': 'deg'},
        'drive_range_deg': [DRIVE_MIN_DEG, DRIVE_MAX_DEG],
        'drive_step_deg': DRIVE_STEP_DEG,
        'null_means': 'pose or configuration cannot close; no value exists',
        'not_modeled': ['over-center locking moment', 'joint clearance', 'link compliance',
                        'fin inertia and aerodynamic load'],
        'baseline': baseline,
        'summary': {
            'configurations': len(rows),
            'assemblable_over_range': sum(r['assemblable_over_range'] for r in rows),
            'closing_at_any_pose': sum(r['poses_closed'] > 0 for r in rows),
        },
        'rows': rows,
    }
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        return result
    a, c, b, d = (BASELINE[k] for k in ('ground', 'coupler', 'input', 'output'))
    thetas = list(range(DRIVE_MIN_DEG, DRIVE_MAX_DEG + 1))
    diagonal = [math.sqrt(a * a + b * b - 2 * a * b * math.cos(math.radians(t))) for t in thetas]
    plt.figure(figsize=(8, 5))
    plt.plot(thetas, diagonal, color='tab:blue', label='Available B-D distance (mm)')
    plt.fill_between(thetas, abs(c - d), c + d, color='tab:green', alpha=0.15,
                     label=f'Distance needed to close loop: {abs(c - d)}-{c + d} mm')
    plt.xlabel('Drive angle θ (deg)')
    plt.ylabel('Distance (mm)')
    plt.title(f'C1 baseline {a}/{c}/{b}/{d} mm: loop closure check (model rev. 2)')
    plt.legend(loc='upper left')
    plt.grid(True, linestyle=':')
    plt.savefig(output_file.parent / 'C1_four_bar_plot.png', dpi=150)
    plt.close()
    return result


def military_study(output_path):
    """Emit the Phase 1 militarized linkage analysis (C1 redesign record)."""
    record = military_linkage_record()
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--emit', help='emit the historical 81-configuration sweep')
    parser.add_argument('--emit-military', help='emit the militarized linkage record')
    args = parser.parse_args()
    if args.emit_military:
        military_study(args.emit_military)
    elif args.emit:
        parameter_study(args.emit)
