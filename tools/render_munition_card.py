"""Render the Project 33 guided-munition configuration card (SVG).

Everything in the figure is drawn from committed, MODELED sources:
- geometry and mass model: design_point.json
- static margin: docs/EVIDENCE/C5_static_margin_inputs.json
- reliability: docs/EVIDENCE/C7_run_record.json
- CEP: docs/EVIDENCE/CEP_estimates.json
- motor: docs/EVIDENCE/MOTOR_sizing.json

The figure is deterministic (no embedded dates) so `--check` can compare
bytes exactly, like every other generated view in this repository.
"""

import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrow, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'docs' / 'assets' / 'munition_overview.svg'

MM = 1.0  # draw in mm; convert to m for text


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def build_figure():
    dp = load(ROOT / 'design_point.json')
    sm = load(ROOT / 'docs/EVIDENCE/C5_static_margin_inputs.json')
    c7 = load(ROOT / 'docs/EVIDENCE/C7_run_record.json')
    cep = load(ROOT / 'docs/EVIDENCE/CEP_estimates.json')
    motor = load(ROOT / 'docs/EVIDENCE/MOTOR_sizing.json')

    fig, ax = plt.subplots(figsize=(11.0, 4.6))
    ax.set_xlim(-260, 900)
    ax.set_ylim(-320, 320)
    ax.set_aspect('equal')
    ax.axis('off')

    body_r = 38.1
    length = 601.0
    nose_l = 38.1

    # ---- body ----
    ax.add_patch(Rectangle((nose_l, -body_r), length - nose_l, 2 * body_r,
                           facecolor='#d8dee9', edgecolor='#343c47', lw=1.4))
    # nose (ellipsoid)
    from matplotlib.patches import Ellipse
    ax.add_patch(Ellipse((nose_l, 0), 2 * nose_l, 2 * body_r,
                          facecolor='#eceff4', edgecolor='#343c47', lw=1.4))

    # ---- warhead bay (nose + first 60 mm) ----
    bay = dp['warhead_bay']
    ax.add_patch(Rectangle((6, -body_r + 4), 79, 2 * (body_r - 4),
                           facecolor='#8d1d1d', edgecolor='#4a0f0f', lw=1.0, alpha=0.85))
    ax.annotate(f"warhead bay\n{bay['bay_total_mass_kg']*1000:.0f} g constant-mass\nGP / HEAT / EFP",
                xy=(45, body_r), xytext=(-150, 250), fontsize=8.5,
                arrowprops=dict(arrowstyle='->', lw=0.8, color='#4a0f0f'),
                ha='left', color='#4a0f0f', fontweight='bold')

    # ---- canards ----
    ca = dp['canards']
    for y in (-1, 1):
        ax.add_patch(Rectangle((ca['leading_edge_x_mm'], y * (body_r - 2) - (1.5 if y > 0 else 1.5)),
                               ca['root_chord_mm'], 3,
                               facecolor='#5e81ac', edgecolor='#2e3440', lw=0.8))
    ax.annotate(f"canards (4)\n{ca['root_chord_mm']:.0f} x {ca['span_mm']:.0f} mm\nPN guidance, ±12°",
                xy=(ca['leading_edge_x_mm'] + 10, body_r), xytext=(80, 255), fontsize=8.5,
                arrowprops=dict(arrowstyle='->', lw=0.8, color='#2e3440'),
                ha='left', color='#2e3440')

    # ---- main fins (deployed, indexed 45 deg -> profile view) ----
    mf = dp['main_fins']
    fin_h = mf['span_mm'] * math.cos(math.radians(45)) * 0.55  # projected profile
    for y in (-1, 1):
        ax.add_patch(Rectangle((mf['leading_edge_x_mm'], y * body_r), mf['root_chord_mm'], y * fin_h,
                               facecolor='#a3be8c', edgecolor='#2e3440', lw=0.9))
    ax.annotate(f"main fins (4), folding\n{mf['root_chord_mm']:.0f} x {mf['span_mm']:.0f} mm\nfour-bar, over-center lock",
                xy=(mf['leading_edge_x_mm'] + 60, body_r + fin_h), xytext=(470, 250), fontsize=8.5,
                arrowprops=dict(arrowstyle='->', lw=0.8, color='#2e3440'),
                ha='left', color='#2e3440')

    # ---- motor ----
    m = motor['motor']
    ax.add_patch(Rectangle((length - 320, -body_r + 3), 320, 2 * (body_r - 3),
                           facecolor='#7a5c3e', edgecolor='#3b2c1f', lw=1.0))
    ax.annotate(f"MIL-33 motor\n{m['impulse_ns']:.0f} N s\n{m['initial_accel_g']:.0f} g launch",
                xy=(length - 160, -body_r), xytext=(620, -270), fontsize=8.5,
                arrowprops=dict(arrowstyle='->', lw=0.8, color='#3b2c1f'),
                ha='left', color='#3b2c1f')

    # ---- CG / CP ----
    cg = sm['cg_ignition_m'] * 1000
    cp = sm['cp_m'] * 1000
    d = sm['geometry']['d_ref'] if 'geometry' in sm else 76.2
    sm_cal = sm['sm_min_calibers']
    ax.plot([cg], [0], marker='o', markersize=9, color='#b48ead', zorder=5)
    ax.plot([cp], [0], marker='^', markersize=10, color='#d08770', zorder=5)
    ax.plot([cg, cp], [-body_r - 26] * 2, lw=2.0, color='#b48ead')
    ax.annotate(f"CG (ignition) {cg:.0f} mm", xy=(cg, 0), xytext=(cg - 60, -120), fontsize=8.5, color='#b48ead')
    ax.annotate(f"CP {cp:.0f} mm", xy=(cp, 0), xytext=(cp - 20, 100), fontsize=8.5, color='#d08770')
    ax.annotate(f"static margin {sm['sm_min_calibers']:.2f}–{sm['sm_max_calibers']:.2f} cal",
                xy=((cg + cp) / 2, -body_r - 26), xytext=((cg + cp) / 2 - 70, -160), fontsize=8.5,
                color='#b48ead', fontweight='bold')

    # ---- fuze callout ----
    ax.annotate("S&A fuze: launch-g ∧ canard-deploy ∧ burn-time\nPD 0/5/10/20 ms · RF proximity option",
                xy=(nose_l + 6, -body_r + 6), xytext=(-250, -230), fontsize=8.5,
                arrowprops=dict(arrowstyle='->', lw=0.8, color='#4a0f0f'),
                ha='left', color='#4a0f0f')

    # ---- stats panel ----
    cep2 = cep['PHASE4_MOTOR']['results']['2000_m']
    stats = (
        "PROJECT 33 · GUIDED MUNITION · PHASE 6 CONFIGURATION\n"
        f"envelope {m['ballistic_envelope_m']/1000:.1f} km · round {m['round_wet_kg']:.1f} kg wet\n"
        f"deployment reliability {c7['success_fraction']*100:.2f}% (MODELED Monte Carlo)\n"
        f"CEP {cep['PHASE4_MOTOR']['results']['1000_m']['cep_guided_m']:.0f} / "
        f"{cep2['cep_guided_m']:.0f} / "
        f"{cep['PHASE4_MOTOR']['results']['3000_m']['cep_guided_m']:.0f} m at 1/2/3 km (guided)\n"
        "MITL default · AUTO behind arm toggle · two-key OVERRIDE\n"
        "HMAC+seq commands · AES-CCM telemetry · DISARM after abort"
    )
    ax.text(900, 300, stats, fontsize=9, family='DejaVu Sans',
            ha='right', va='top', color='#2e3440',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#eceff4', edgecolor='#343c47'))

    ax.text(900, -300, "All values MODELED from committed sources; nothing measured or fielded. "
                       "Evidence: docs/MILITARY/ · generator: tools/render_munition_card.py",
            fontsize=7.5, ha='right', va='bottom', color='#4c566a', style='italic')

    return fig


def render(path=OUTPUT):
    import re
    fig = build_figure()
    path.parent.mkdir(parents=True, exist_ok=True)
    # metadata Date=None keeps the SVG free of timestamps; matplotlib also
    # randomizes clip-path and marker ids per render, so canonicalize them
    # for byte-deterministic output.
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
        tmp_out = Path(tmp) / 'card.svg'
        render(tmp_out)
        return tmp_out.read_bytes() == path.read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        if not OUTPUT.exists() or not check():
            print('Munition configuration card is stale: run python tools/render_munition_card.py')
            return 1
        print('Munition configuration card is current.')
        return 0
    render()
    print(f'Wrote {OUTPUT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
