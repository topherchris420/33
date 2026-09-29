"""Deterministic review figures rendered from tested geometry code (standard library only).

A reviewer should be able to understand the key geometry without Fusion 360.
These figures show geometry only: none of them establishes that a part can be
built, will survive loads, or performs aerodynamically.

    python tools/review_figures.py          # write docs/assets/review/*.svg
    python tools/review_figures.py --check  # fail if a committed figure is stale
"""

import argparse
import importlib.util
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "review"
INK, MUTED, ACCENT, WARN = "#1b2622", "#5b6b64", "#1f6f5a", "#9b2c2c"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _svg(width, height, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
            f'font-family="system-ui, sans-serif" role="img" aria-label="{title}">\n'
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>\n{body}</svg>\n')


def _text(x, y, text, size=13, fill=INK, anchor="start", weight="normal"):
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{text}</text>\n'


def naca_profile():
    generator = _load("naca_fin_generator", "CAD Files/naca_fin_generator.py")
    upper, lower = generator.naca_4digit_coordinates(0.0, 0.0, 0.12, 0.060, num_points=80)
    chord = upper[-1][0]
    thickness, at = max(((u[1] - l[1]), u[0]) for u, l in zip(upper, lower))
    scale, x0, y0 = 12.0, 70.0, 190.0
    points = [(x0 + x * scale, y0 - y * scale) for x, y, _ in upper] + \
             [(x0 + x * scale, y0 - y * scale) for x, y, _ in reversed(lower)]
    path = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    right = x0 + chord * scale
    top, bottom = y0 - thickness / 2 * scale, y0 + thickness / 2 * scale
    tx = x0 + at * scale
    body = [
        _text(30, 36, "C3 · NACA 0012 fin profile, 60 mm chord (generated, not measured)", 17, weight="600"),
        _text(30, 58, "Source: CAD Files/naca_fin_generator.py, naca_4digit_coordinates(m=0, p=0, t=0.12, c=0.060).", 12, MUTED),
        f'<line x1="{x0 - 20}" y1="{y0}" x2="{right + 20}" y2="{y0}" stroke="{MUTED}" stroke-dasharray="5 4"/>\n',
        f'<polygon points="{path}" fill="#e1f1ea" stroke="{ACCENT}" stroke-width="1.6"/>\n',
        f'<line x1="{x0}" y1="{y0 + 70}" x2="{right}" y2="{y0 + 70}" stroke="{INK}" marker-start="url(#a)" marker-end="url(#a)"/>\n',
        f'<line x1="{x0}" y1="{bottom + 6}" x2="{x0}" y2="{y0 + 76}" stroke="{MUTED}"/><line x1="{right}" y1="{y0 + 6}" x2="{right}" y2="{y0 + 76}" stroke="{MUTED}"/>\n',
        _text((x0 + right) / 2, y0 + 92, f"chord {chord:.1f} mm", 13, anchor="middle"),
        f'<line x1="{tx}" y1="{top - 40}" x2="{tx}" y2="{bottom + 40}" stroke="{WARN}" stroke-dasharray="3 3"/>\n',
        _text(tx + 8, top - 44, f"max thickness {thickness:.2f} mm at {at:.1f} mm ({at / chord * 100:.0f}% chord)", 13, WARN),
        _text(30, 330, "Geometry only. Says nothing about aerodynamic performance, fin loads, or the 120 mm chord used by C6.", 12, MUTED),
        _text(30, 348, "Chord line dashed; scale 12 px per mm.", 12, MUTED),
    ]
    marker = f'<defs><marker id="a" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="{INK}"/></marker></defs>\n'
    return _svg(900, 370, marker + "".join(body), "NACA 0012 fin profile")


def loop_closure():
    four_bar = _load("four_bar", "mechanism/four_bar.py")
    base = four_bar.BASELINE
    a, c, b, d = base["ground"], base["coupler"], base["input"], base["output"]
    assemblable = four_bar.evaluate_linkage(a, c, b, d)["assemblable_over_range"]
    scale, ox, oy = 3.2, 250.0, 330.0

    def P(x, y):
        return ox + x * scale, oy - y * scale

    body = [_text(30, 36, f"C1 · Can the baseline four-bar close? (ground {a}, coupler {c}, input {b}, output {d} mm)", 17, weight="600"),
            _text(30, 58, "Source: mechanism/four_bar.py revision 2. The output joint C must lie on both circles at once.", 12, MUTED)]
    ax, ay = P(0, 0)
    dx, dy = P(a, 0)
    body.append(f'<line x1="{ax}" y1="{ay}" x2="{dx}" y2="{dy}" stroke="{INK}" stroke-width="4"/>\n')
    for theta, colour, label in ((0, ACCENT, "drive 0°"), (92, "#6b5bd6", "drive 92°")):
        bx, by = b * math.cos(math.radians(theta)), b * math.sin(math.radians(theta))
        px, py = P(bx, by)
        body.append(f'<line x1="{ax}" y1="{ay}" x2="{px:.1f}" y2="{py:.1f}" stroke="{colour}" stroke-width="3"/>\n')
        body.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{c * scale:.1f}" fill="none" stroke="{colour}" stroke-dasharray="6 4"/>\n')
        if theta == 0:
            body.append(_text(px, py + 40, f"B at {label}", 12, colour, anchor="middle"))
        else:
            body.append(_text(px + 6, py - 6, f"B at {label}", 12, colour))
    body.append(f'<circle cx="{dx}" cy="{dy}" r="{d * scale:.1f}" fill="none" stroke="{WARN}" stroke-width="1.6"/>\n')
    body.append(_text(ax - 8, ay + 18, "A", 13, anchor="end", weight="600"))
    body.append(_text(dx + 6, dy + 18, "D", 13, weight="600"))
    reach = max(math.sqrt(a * a + b * b - 2 * a * b * math.cos(math.radians(t))) for t in range(0, 93))
    verdict = "closes at every drive angle" if assemblable else "cannot close at any drive angle from 0 to 92°"
    notes = [f"Dashed circles: where the {c} mm coupler can put C from B.  Red circle: where the {d} mm output link allows C.",
             f"The B-D distance never exceeds {reach:.1f} mm, but the circles only meet when it is at least |{c}-{d}| = {abs(c - d)} mm.",
             f"Result: the linkage {verdict} (requirement R-C1-CLOSURE, discrepancy D-002).",
             "Geometry only: a closed loop would still say nothing about loads, clearance, or locking."]
    wrapped = []
    for note in notes:
        line = ""
        for word in note.split():
            if line and len(line) + len(word) > 58:
                wrapped.append(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        wrapped += [line, ""]
    for index, line in enumerate(wrapped):
        body.append(_text(560, 110 + index * 19, line, 12, WARN if "Result" in line or "cannot" in line else INK))
    return _svg(1000, 600, "".join(body), "Four-bar loop closure check")


FIGURES = {"c3_naca0012_profile.svg": naca_profile, "c1_loop_closure.svg": loop_closure}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    stale = []
    for name, render in FIGURES.items():
        content = render()
        target = OUT / name
        if args.check:
            if not target.is_file() or target.read_text(encoding="utf-8") != content:
                stale.append(str(target.relative_to(ROOT)))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="\n")
    if stale:
        print("Stale review figures (run python tools/review_figures.py):", *stale, sep="\n  ")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
