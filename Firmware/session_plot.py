"""Session graph intended to be readable months later without the operator present.

Units and clock domain on every axis, gaps drawn as gaps, state changes marked,
gains annotated, and display scaling labeled as scaling rather than data.
"""

import math


def break_at_gaps(times, values, gap_ms):
    """Insert a NaN between samples separated by more than gap_ms or by a clock regression.

    Matplotlib does not draw a line through NaN, so missing time stays visibly missing.
    """
    out_t, out_v = [], []
    for index, (t, v) in enumerate(zip(times, values)):
        if index:
            delta = t - times[index - 1]
            if delta > gap_ms or delta < 0:
                out_t.append(math.nan)
                out_v.append(math.nan)
        out_t.append(t)
        out_v.append(v)
    return out_t, out_v


def gap_spans(times, gap_ms):
    return [(a, b) for a, b in zip(times, times[1:]) if b - a > gap_ms]


def render_session_graph(path, times, roll, rate, servo, *, session_id, events=(), gains_text="",
                         rate_scale=0.25, gap_ms=500):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    width = max(12, min(200, len(times) / 50))
    fig, ax = plt.subplots(figsize=(width, 4.6), dpi=100)
    t_roll, v_roll = break_at_gaps(times, roll, gap_ms)
    t_rate, v_rate = break_at_gaps(times, [r * rate_scale for r in rate], gap_ms)
    t_servo, v_servo = break_at_gaps(times, servo, gap_ms)
    ax.plot(t_roll, v_roll, label="Roll (deg), raw", color="tab:blue", linewidth=1.8)
    ax.plot(t_rate, v_rate, label=f"Roll rate (deg/s) x {rate_scale} (display scaling)", color="tab:orange", linewidth=1.2)
    ax.step(t_servo, v_servo, where="post", label="Servo offset command (deg), raw", color="tab:purple", linewidth=1.0)
    for start, end in gap_spans(times, gap_ms):
        ax.axvspan(start, end, color="tab:red", alpha=0.10, lw=0)
    if gap_spans(times, gap_ms):
        ax.plot([], [], color="tab:red", alpha=0.3, linewidth=8, label=f"Gap > {gap_ms} ms (no samples)")
    for event in events:
        ax.axvline(event["time"], color="black", linestyle="--", alpha=0.5)
        ax.annotate(event["state"], (event["time"], 1.0), xycoords=("data", "axes fraction"),
                    rotation=90, va="top", ha="right", fontsize=8)
    ax.set_xlabel("time_ms: launcher relay clock (ms), not rocket sample time")
    ax.set_ylabel("deg | scaled deg/s | deg")
    ax.set_title(f"Session {session_id} · RAW SESSION, not evidence · {len(times)} live T samples · origin undeclared",
                 fontsize=10)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper left", fontsize=8)
    footer = gains_text + " · Invalid samples are excluded, not plotted as zero."
    fig.subplots_adjust(bottom=0.22)
    fig.text(0.01, 0.005, footer, fontsize=8, color="0.3", va="bottom")
    fig.savefig(path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    return path
