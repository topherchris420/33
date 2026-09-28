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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--emit', required=True)
    args = parser.parse_args()
    parameter_study(args.emit)
