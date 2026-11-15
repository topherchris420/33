"""Render the Project 33 guided-munition exploded blueprint (SVG).

A schematic-style exploded assembly drawn entirely from committed sources:
stations and masses from design_point.json, the verified four-bar linkage
poses from mechanism/four_bar.py, and the motor record from
docs/EVIDENCE/MOTOR_sizing.json. Deterministic (canonicalized ids, no
date metadata) with a --check mode, like every generated view here.
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Ellipse, FancyArrow, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'mechanism'))
import four_bar  # noqa: E402

OUTPUT = ROOT / 'docs' / 'assets' / 'munition_blueprint.svg'
BLUE = '#2e3440'
PAPER = '#fbfbf8'


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def part_box(ax, x, y, w, h, label, sub, color, edge=BLUE):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=color, edgecolor=edge, lw=1.2))
    ax.text(x + w / 2, y + h / 2, label, ha='center', va='center', fontsize=8.6,
            color=BLUE, fontweight='bold')
    if sub:
        ax.text(x + w / 2, y + h / 2 - 11, sub, ha='center', va='center', fontsize=7.2, color='#4c566a')


def build_figure():
    dp = load(ROOT / 'design_point.json')
    motor = load(ROOT / 'docs/EVIDENCE/MOTOR_sizing.json')['motor']

    fig, ax = plt.subplots(figsize=(12.0, 6.4))
    fig.patch.set_facecolor(PAPER)
    ax.set_xlim(0, 1200)
    ax.set_ylim(0, 640)
    ax.axis('off')

    # title block (blueprint style)
    ax.add_patch(Rectangle((820, 560), 370, 70, facecolor='none', edgecolor=BLUE, lw=1.6))
    ax.text(840, 618, 'PROJECT 33 — GUIDED MUNITION', fontsize=12, fontweight='bold', color=BLUE)
    ax.text(840, 596, 'EXPLODED ASSEMBLY · PHASE 6 · SCALE: NONE', fontsize=7.6, color='#4c566a')
    ax.text(840, 578, 'ALL VALUES MODELED · SOURCE: design_point.json', fontsize=7.6, color='#4c566a')

    R = 36.0  # body radius on the sheet

    # ---- axial spine with station dimensions ----
    y_axis = 330
    ax.annotate('', xy=(1160, y_axis), xytext=(40, y_axis),
                arrowprops=dict(arrowstyle='<->', lw=0.9, color=BLUE))
    stations = [
        (0, '0'), (85, '85'), (180, '180 canards'),
        (440, '440 fin LE'), (520, '520 fin TE'), (601, '601 tail'),
    ]
    for x, t in stations:
        ax.plot([x, x], [y_axis - 8, y_axis + 8], color=BLUE, lw=0.9)
        ax.text(x, y_axis - 22, t, ha='center', fontsize=7.2, color=BLUE)

    # ---- exploded parts along the spine ----
    # 1. nose cone + fuze (x ~ 100, top)
    part_box(ax, 60, 430, 120, 56, 'NOSE CONE', 'ellipsoid · PLA/7075', '#eceff4')
    ax.add_patch(Ellipse((120, 418), 26, 40, facecolor='#eceff4', edgecolor=BLUE, lw=1.2))
    ax.text(150, 510, 'crush switch + accel impact sensing', fontsize=6.8, color='#4a0f0f')
    ax.text(120, 528, 'S&A FUZE (in bay aft ring)', fontsize=8.2, color='#4a0f0f',
            fontweight='bold', ha='center')

    # 2. warhead bay (x ~ 260)
    bay = dp['warhead_bay']
    part_box(ax, 210, 430, 150, 56, 'WARHEAD BAY', f"{bay['bay_total_mass_kg']*1000:.0f} g constant-mass", '#8d1d1d', edge='#4a0f0f')
    ax.text(285, 510, 'GP 110 g A5 · HEAT 120 g B · EFP 95 g', fontsize=6.8,
            color='#4a0f0f', ha='center')
    ax.text(285, 524, 'loadouts interchangeable', fontsize=6.8, color='#4a0f0f', ha='center')

    # 3. avionics + GPS (x ~ 430)
    part_box(ax, 420, 430, 140, 56, 'AVIONICS', 'ESP32 · MPU6050 · GPS', '#e5e9f0')
    ax.text(490, 510, 'GPS-aided IMU · PN guidance (N=3)', fontsize=6.8, ha='center', color='#4c566a')
    ax.text(490, 524, 'RAM ring-buffer flight log', fontsize=6.8, ha='center', color='#4c566a')

    # 4. canard ring (drawn on the spine)
    ca = dp['canards']
    ax.add_patch(Rectangle((590, y_axis - R), 40, 2 * R, facecolor='#d8dee9', edgecolor=BLUE, lw=1.2))
    for yy in (-1, 1):
        ax.add_patch(Rectangle((575, y_axis + yy * (R - 2) - 1.5), ca['root_chord_mm'] * 0.7, 3,
                               facecolor='#5e81ac', edgecolor='#2e3440', lw=0.7))
    ax.text(610, 510, 'CANARD RING (4 servos, 30 kg·cm)', fontsize=8.2, ha='center',
            color='#2e3440', fontweight='bold')
    ax.text(610, 494, f"canards {ca['root_chord_mm']:.0f} x {ca['span_mm']:.0f} mm · ±12°", fontsize=6.8,
            ha='center', color='#4c566a')

    # 5. body tube + fin section (x ~ 760)
    part_box(ax, 690, 430, 180, 56, 'AFT BODY (G-10)', 'folding-fin section', '#d8dee9')
    # fin planform
    mf = dp['main_fins']
    ax.add_patch(Rectangle((720, 380), 100, 44, facecolor='#a3be8c', edgecolor='#2e3440', lw=1.0))
    ax.text(770, 402, 'FIN 160 x 220', fontsize=7.4, ha='center', color='#2e3440', fontweight='bold')
    ax.text(780, 510, 'molded CFRP · four-bar linkage', fontsize=6.8, ha='center', color='#4c566a')

    # 6. motor (x ~ 1000)
    part_box(ax, 940, 430, 160, 56, 'MIL-33 MOTOR', f"{motor['impulse_ns']:.0f} N s · e-initiator", '#c8b6a6', edge='#3b2c1f')
    ax.text(1020, 510, f"propellant {motor['propellant_kg']:.2f} kg · {motor['burn_s']:.0f} s burn",
            fontsize=6.8, ha='center', color='#3b2c1f')
    ax.text(1020, 524, 'ignition servo backup path', fontsize=6.8, ha='center', color='#3b2c1f')

    # ---- four-bar linkage detail (from the verified kinematics) ----
    ax.add_patch(Rectangle((660, 80), 300, 210, facecolor='none', edgecolor=BLUE, lw=1.2))
    ax.text(670, 272, 'FOUR-BAR DETAIL — verified kinematics (mechanism/four_bar.py)',
            fontsize=8.0, color=BLUE, fontweight='bold')
    fb = dp['four_bar']
    trace = four_bar.trace_deployment(fb['ground_mm'], fb['crank_mm'], fb['coupler_mm'],
                                       fb['output_mm'], fb['stowed_crank_deg'],
                                       fb['toggle_crank_deg'] + 15.0, steps=200)
    # draw the linkage at the deployed-stop pose, scaled into the detail box
    stop_idx = None
    for i, row in enumerate(trace):
        if row[1] >= 89.0:
            stop_idx = i
            break
    pose = trace[stop_idx if stop_idx is not None else len(trace) // 2]
    # recompute joint positions for the pose
    a, b, c, d = fb['ground_mm'], fb['crank_mm'], fb['coupler_mm'], fb['output_mm']
    t2 = math.radians(pose[0])
    bx, by = b * math.cos(t2), b * math.sin(t2)
    pts = four_bar.closure_points(a, b, c, d, t2)
    cx, cy = pts[0]
    ox, oy = 690 + a * 8.0, 200
    sx = lambda v: ox + v * 8.0
    sy = lambda v: oy - v * 8.0
    ax.plot([sx(0), sx(a)], [sy(0), sy(0)], color='#4c566a', lw=1.6)
    ax.plot([sx(0), sx(bx)], [sy(0), sy(by)], color=BLUE, lw=2.2)
    ax.plot([sx(bx), sx(cx)], [sy(by), sy(cy)], color=BLUE, lw=2.2)
    ax.plot([sx(a), sx(cx)], [sy(0), sy(cy)], color=BLUE, lw=2.2)
    for (px, py), lbl in (((0, 0), 'A'), ((a, 0), 'D'), ((bx, by), 'B'), ((cx, cy), 'C')):
        ax.plot(sx(px), sy(py), 'o', color='#8d1d1d', markersize=4)
        ax.text(sx(px) + 5, sy(py) + 5, lbl, fontsize=7.5, color='#8d1d1d', fontweight='bold')
    ax.text(700, 100, f"ground {a} · crank {b} · coupler {c} · output {d} mm\n"
                     f"stop at fin {fb['fin_stop_deg']:.0f}° · toggle {fb['toggle_fin_deg']:.2f}° (over-center)\n"
                     f"back-drive ratio at stop 0.363 · ±0.15 mm tolerances assemble",
            fontsize=7.0, color='#4c566a', va='bottom')

    # leader lines from spine parts to detail
    ax.annotate('', xy=(810, 290), xytext=(770, 380),
                arrowprops=dict(arrowstyle='->', lw=0.8, color=BLUE))

    # CG/CP ruler at the bottom
    cg = 323
    cp = 450
    ax.plot([cg, cp], [46, 46], color='#b48ead', lw=2.0)
    ax.plot([cg], [46], 'o', color='#b48ead', markersize=6)
    ax.plot([cp], [46], '^', color='#d08770', markersize=7)
    ax.text(cg, 30, 'CG 323', fontsize=7.2, color='#b48ead', ha='center')
    ax.text(cp, 30, 'CP 450', fontsize=7.2, color='#d08770', ha='center')
    ax.text((cg + cp) / 2, 14, 'static margin 1.66–1.76 cal · deployment reliability 99.93% · CEP 19–81 m guided',
            fontsize=7.4, color='#4c566a', ha='center')

    ax.text(1160, 8, 'MODELED from committed sources · docs/MILITARY/ · generator: tools/render_munition_blueprint.py',
            fontsize=6.6, ha='right', color='#4c566a', style='italic')

    return fig


def render(path=OUTPUT):
    fig = build_figure()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp.svg')
    fig.savefig(tmp, format='svg', metadata={'Date': None}, bbox_inches='tight')
    plt.close(fig)
    text = tmp.read_text(encoding='utf-8')
    counter = {}

    def canon(match):
        key = match.group(0)
        if key not in counter:
            counter[key] = f'c{len(counter)}'
        return counter[key]

    text = re.sub(r'(?:id="|url\(#|xlink:href="#)(?:p|m)[0-9a-f]{6,}"?', canon, text)
    path.write_text(text, encoding='utf-8', newline='\n')
    tmp.unlink()


def check(path=OUTPUT):
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_out = Path(tmp) / 'bp.svg'
        render(tmp_out)
        return tmp_out.read_bytes() == path.read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        if not OUTPUT.exists() or not check():
            print('Munition blueprint is stale: run python tools/render_munition_blueprint.py')
            return 1
        print('Munition blueprint is current.')
        return 0
    render()
    print(f'Wrote {OUTPUT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
