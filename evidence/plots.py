"""Standard-library SVG plots for review packets.

Plots follow three rules: every axis has units, a gap is drawn as a gap (never
bridged by a line), and excluded samples are counted in the caption rather than
drawn at zero.
"""

from html import escape

WIDTH, HEIGHT, PAD_L, PAD_R, PAD_T, PAD_B = 980, 190, 64, 16, 22, 34
SIGNALS = [("roll_deg", "roll (deg)", "#1f6f5a"), ("rate_deg_s", "roll rate (deg/s)", "#b36b00"),
           ("servo_output", "servo offset (deg)", "#6b5bd6")]
MAX_PANELS = 6


def _ticks(low, high, count=4):
    if high == low:
        return [low]
    step = (high - low) / count
    return [low + step * index for index in range(count + 1)]


def _panel(points, title, caption, gap_ms):
    xs = [p["t"] for p in points]
    x0, x1 = min(xs), max(xs)
    values = [p[key] for p in points for key, _, _ in SIGNALS]
    y0, y1 = min(values + [0.0]), max(values + [0.0])
    if y1 == y0:
        y0, y1 = y0 - 1, y1 + 1
    span_x = (x1 - x0) or 1

    def sx(value):
        return PAD_L + (value - x0) / span_x * (WIDTH - PAD_L - PAD_R)

    def sy(value):
        return PAD_T + (y1 - value) / (y1 - y0) * (HEIGHT - PAD_T - PAD_B)

    parts = [f'<svg viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{escape(title)}" '
             f'style="width:100%;height:auto;background:var(--panel);border:1px solid var(--line);border-radius:6px;margin:6px 0">',
             f'<text x="{PAD_L}" y="15" font-size="12" fill="currentColor">{escape(title)}</text>']
    for tick in _ticks(y0, y1):
        y = sy(tick)
        parts.append(f'<line x1="{PAD_L}" x2="{WIDTH - PAD_R}" y1="{y:.1f}" y2="{y:.1f}" stroke="currentColor" stroke-opacity=".12"/>'
                     f'<text x="{PAD_L - 6}" y="{y + 4:.1f}" font-size="10" text-anchor="end" fill="currentColor" fill-opacity=".7">{tick:.3g}</text>')
    for tick in _ticks(x0, x1):
        x = sx(tick)
        parts.append(f'<text x="{x:.1f}" y="{HEIGHT - 18}" font-size="10" text-anchor="middle" fill="currentColor" fill-opacity=".7">{tick:.0f}</text>')
    parts.append(f'<text x="{(WIDTH + PAD_L) / 2:.0f}" y="{HEIGHT - 4}" font-size="10.5" text-anchor="middle" fill="currentColor">{escape(caption)}</text>')
    # Shade every gap above the threshold so missing time is visible as missing.
    for previous, current in zip(points, points[1:]):
        if current["t"] - previous["t"] > gap_ms:
            parts.append(f'<rect x="{sx(previous["t"]):.1f}" y="{PAD_T}" width="{sx(current["t"]) - sx(previous["t"]):.1f}" '
                         f'height="{HEIGHT - PAD_T - PAD_B}" fill="#9b2c2c" fill-opacity=".10"><title>gap {current["t"] - previous["t"]} ms: no samples</title></rect>')
    for key, label, colour in SIGNALS:
        runs, run = [], []
        for index, point in enumerate(points):
            if index and (point["t"] - points[index - 1]["t"] > gap_ms):
                runs.append(run)
                run = []
            run.append(f"{sx(point['t']):.1f},{sy(point[key]):.1f}")
        runs.append(run)
        for run in runs:
            if len(run) == 1:
                x, y = run[0].split(",")
                parts.append(f'<circle cx="{x}" cy="{y}" r="1.8" fill="{colour}"/>')
            elif run:
                parts.append(f'<polyline fill="none" stroke="{colour}" stroke-width="1.4" points="{" ".join(run)}"/>')
    legend_x = WIDTH - PAD_R - 3 * 150
    for index, (_, label, colour) in enumerate(SIGNALS):
        x = legend_x + index * 150
        parts.append(f'<rect x="{x}" y="6" width="12" height="3" fill="{colour}"/><text x="{x + 16}" y="12" font-size="10.5" fill="currentColor">{escape(label)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def telemetry_svg(series, gap_ms):
    if not series:
        return '<p class="muted">No plottable T or LOG samples.</p>'
    out = []
    for stream in series:
        segments = {}
        for point in stream["points"]:
            segments.setdefault(point["segment"], []).append(point)
        name = f'{stream["source"]} / {stream["message_type"]}'
        clock = "launcher relay clock" if stream["clock_domain"] == "launcher_relay_millis" else "rocket clock"
        excluded = stream["invalid_samples"]
        ordered = sorted(segments.items())
        for number, points in ordered[:MAX_PANELS]:
            title = f"{name} · segment {number} of {len(segments)}"
            caption = (f"time_ms on the {clock} (ms). Raw recorded values. Shaded bands: gaps over {gap_ms} ms. "
                       f"{excluded} invalid sample(s) in this stream excluded, not drawn.")
            out.append(_panel(points, title, caption, gap_ms))
        if len(ordered) > MAX_PANELS:
            out.append(f'<p class="muted">{len(ordered) - MAX_PANELS} further segment(s) of {escape(name)} not drawn; see the CSV.</p>')
    return "".join(out)
