"""Read-only status board window for the bench dashboard.

The panel draws GroundStatus snapshots and nothing else: it has no command path,
no socket, and no buttons that act on hardware. Attitude stays on screen with no
way to hide it, and goes visibly invalid rather than holding an old value.

    python Firmware/status_panel.py --demo    # invented packets, no hardware
"""

import argparse
import math
import tkinter as tk

from ground_status import (ADVISORY, AT_RISK, CAUTION, GroundStatus, LOST, NOT_SEEN, SEEN, SUPPORTED, SUSPECT,
                           WARNING, diagnosis_text, gains_line, synthetic_demo_events)

BG, PANEL, INK, DIM = "#10151a", "#1a2128", "#e6edf3", "#8b98a5"
GREEN, AMBER, RED, CYAN = "#3fb950", "#d29922", "#f85149", "#58a6ff"
UNIT_COLOURS = {SEEN: GREEN, SUSPECT: RED, NOT_SEEN: DIM}
CAPABILITY_COLOURS = {SUPPORTED: GREEN, AT_RISK: AMBER, LOST: RED}
LEVEL_COLOURS = {WARNING: RED, CAUTION: AMBER, ADVISORY: CYAN}
STATE_COLOURS = {"IDLE": DIM, "ARMED": AMBER, "IGNITING": RED, "FLIGHT": RED}
FONT, MONO = "Segoe UI", "Consolas"
DIAL = 240


class StatusPanel:
    def __init__(self, master, status, banner="RAW SESSION · not evidence", refresh_ms=200):
        self.status = status
        self.refresh_ms = refresh_ms
        self.window = tk.Toplevel(master)
        self.window.title("Project 33 Status Board")
        self.window.configure(bg=BG)
        self._build(banner)
        # Size to the content so fonts fit at any display scaling, within the screen.
        self.window.update_idletasks()
        self.window.minsize(min(self.window.winfo_reqwidth(), self.window.winfo_screenwidth() - 40),
                            min(self.window.winfo_reqheight(), self.window.winfo_screenheight() - 80))
        self.refresh()

    def exists(self):
        try:
            return bool(self.window.winfo_exists())
        except tk.TclError:
            return False

    def lift(self):
        self.window.deiconify()
        self.window.lift()

    # ---- layout -------------------------------------------------------------------------

    def _frame(self, parent, title):
        outer = tk.Frame(parent, bg=PANEL, padx=12, pady=8)
        tk.Label(outer, text=title, bg=PANEL, fg=DIM, font=(FONT, 9, "bold"), anchor="w").pack(fill=tk.X)
        return outer

    def _build(self, banner):
        tk.Label(self.window, text=banner, bg=BG, fg=AMBER, font=(FONT, 9, "bold"), anchor="w", padx=12).pack(fill=tk.X, pady=(6, 0))
        top = tk.Frame(self.window, bg=BG, padx=12, pady=6)
        top.pack(fill=tk.X)
        tk.Label(top, text="ROCKET", bg=BG, fg=DIM, font=(FONT, 10, "bold")).pack(side=tk.LEFT)
        self.rocket_label = tk.Label(top, text="", bg=BG, fg=INK, font=(MONO, 18, "bold"))
        self.rocket_label.pack(side=tk.LEFT, padx=(8, 24))
        tk.Label(top, text="LAUNCHER", bg=BG, fg=DIM, font=(FONT, 10, "bold")).pack(side=tk.LEFT)
        self.launcher_label = tk.Label(top, text="", bg=BG, fg=INK, font=(FONT, 10))
        self.launcher_label.pack(side=tk.LEFT, padx=8)

        # Packed before the middle row so advisories keep their space when the window is short.
        bottom = tk.Frame(self.window, bg=BG, padx=12, pady=8)
        bottom.pack(side=tk.BOTTOM, fill=tk.X)
        middle = tk.Frame(self.window, bg=BG, padx=12)
        middle.pack(fill=tk.BOTH, expand=True)
        middle.columnconfigure(1, weight=1)
        middle.columnconfigure(2, weight=2)
        middle.rowconfigure(0, weight=1)

        attitude = self._frame(middle, "ATTITUDE (ROLL ONLY)")
        attitude.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.dial = tk.Canvas(attitude, width=DIAL, height=DIAL, bg=PANEL, highlightthickness=0)
        self.dial.pack(pady=6)
        self.roll_label = tk.Label(attitude, text="", bg=PANEL, fg=INK, font=(MONO, 16, "bold"))
        self.roll_label.pack()
        self.rate_label = tk.Label(attitude, text="", bg=PANEL, fg=INK, font=(MONO, 11))
        self.rate_label.pack()
        self.servo = tk.Canvas(attitude, width=DIAL, height=38, bg=PANEL, highlightthickness=0)
        self.servo.pack(pady=(6, 0))
        self.attitude_note = tk.Label(attitude, text="", bg=PANEL, fg=DIM, font=(FONT, 8), justify=tk.LEFT,
                                      wraplength=DIAL, anchor="w")
        self.attitude_note.pack(fill=tk.X, pady=(4, 0))

        units = self._frame(middle, "UNITS")
        units.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
        self.unit_rows = {}
        for unit in self.status.model["units"]:
            row = tk.Frame(units, bg=PANEL)
            row.pack(fill=tk.X, pady=2)
            dot = tk.Canvas(row, width=12, height=12, bg=PANEL, highlightthickness=0)
            dot.create_oval(1, 1, 11, 11, fill=DIM, outline="", tags="dot")
            dot.pack(side=tk.LEFT)
            tk.Label(row, text=unit["id"], bg=PANEL, fg=INK, font=(MONO, 10, "bold"), width=9, anchor="w").pack(side=tk.LEFT, padx=4)
            state = tk.Label(row, text="", bg=PANEL, fg=DIM, font=(MONO, 9), anchor="w")
            state.pack(side=tk.LEFT)
            self.unit_rows[unit["id"]] = (dot, state)
        tk.Label(units, text="SEEN means packets that need this unit are arriving now. It is not a health check.",
                 bg=PANEL, fg=DIM, font=(FONT, 8), wraplength=210, justify=tk.LEFT, anchor="w").pack(fill=tk.X, pady=(8, 8))
        tk.Label(units, text="ISOLATION", bg=PANEL, fg=DIM, font=(FONT, 9, "bold"), anchor="w").pack(fill=tk.X)
        self.diagnosis_label = tk.Label(units, text="", bg=PANEL, fg=INK, font=(FONT, 10), wraplength=210,
                                        justify=tk.LEFT, anchor="w")
        self.diagnosis_label.pack(fill=tk.X, pady=(2, 4))
        self.isolation_label = tk.Label(units, text="", bg=PANEL, fg=CYAN, font=(FONT, 10), wraplength=210,
                                        justify=tk.LEFT, anchor="w")
        self.isolation_label.pack(fill=tk.X)

        capabilities = self._frame(middle, "CAPABILITIES (SOURCE-PINNED MODEL, BENCH NOT MEASURED)")
        capabilities.grid(row=0, column=2, sticky="nsew")
        self.capability_rows = {}
        for capability in self.status.model["capabilities"]:
            row = tk.Frame(capabilities, bg=PANEL)
            row.pack(fill=tk.X, pady=1)
            state = tk.Label(row, text="", bg=PANEL, fg=DIM, font=(MONO, 9, "bold"), width=13, anchor="w")
            state.pack(side=tk.LEFT)
            tk.Label(row, text=capability["name"], bg=PANEL, fg=INK, font=(FONT, 9), anchor="w").pack(side=tk.LEFT)
            self.capability_rows[capability["id"]] = state

        gains = self._frame(bottom, "GAINS")
        gains.pack(fill=tk.X, pady=(0, 8))
        self.gains_label = tk.Label(gains, text="", bg=PANEL, fg=INK, font=(MONO, 10), anchor="w")
        self.gains_label.pack(fill=tk.X)
        alerts = self._frame(bottom, "ADVISORIES")
        alerts.pack(fill=tk.X)
        self.advisory_text = tk.Text(alerts, height=9, bg=PANEL, fg=INK, font=(MONO, 10), bd=0, wrap=tk.WORD,
                                     state=tk.DISABLED, highlightthickness=0)
        self.advisory_text.pack(fill=tk.X)
        for level, colour in LEVEL_COLOURS.items():
            self.advisory_text.tag_configure(level, foreground=colour, font=(MONO, 10, "bold"))
        self.advisory_text.tag_configure("detail", foreground=DIM, font=(FONT, 9), lmargin1=12, lmargin2=12)

    # ---- drawing ------------------------------------------------------------------------

    def refresh(self):
        if not self.exists():
            return
        self.render(self.status.snapshot())
        self.window.after(self.refresh_ms, self.refresh)

    def render(self, snapshot):
        rocket = snapshot["rocket"]
        colour = RED if rocket["stale"] and rocket["state"] in ("ARMED", "IGNITING", "FLIGHT") else STATE_COLOURS.get(rocket["state"], DIM)
        self.rocket_label.config(text=rocket["display"], fg=colour)
        self.launcher_label.config(text=snapshot["launcher"])
        self._draw_attitude(snapshot["attitude"])
        for unit, state in snapshot["units"].items():
            dot, label = self.unit_rows[unit]
            dot.itemconfig("dot", fill=UNIT_COLOURS[state])
            label.config(text=state, fg=UNIT_COLOURS[state])
        self.diagnosis_label.config(text=diagnosis_text(snapshot))
        self.isolation_label.config(text=snapshot["isolation"] or "")
        for capability, state in snapshot["capabilities"].items():
            self.capability_rows[capability].config(text=state, fg=CAPABILITY_COLOURS.get(state, DIM))
        self.gains_label.config(text=gains_line(snapshot["gains"]))
        self._draw_advisories(snapshot["advisories"])

    def _draw_attitude(self, attitude):
        dial, size = self.dial, DIAL
        centre, radius = size / 2, size / 2 - 10
        dial.delete("all")
        dial.create_oval(centre - radius, centre - radius, centre + radius, centre + radius, outline=DIM, width=2)
        for mark in range(0, 360, 30):
            angle = math.radians(mark)
            inner = radius - (12 if mark % 90 == 0 else 6)
            dial.create_line(centre + inner * math.sin(angle), centre - inner * math.cos(angle),
                             centre + radius * math.sin(angle), centre - radius * math.cos(angle), fill=DIM)
        dial.create_line(centre - 34, centre, centre - 10, centre, fill=AMBER, width=3)
        dial.create_line(centre + 10, centre, centre + 34, centre, fill=AMBER, width=3)
        dial.create_oval(centre - 3, centre - 3, centre + 3, centre + 3, fill=AMBER, outline="")
        if attitude["valid"]:
            angle = math.radians(attitude["roll_deg"])
            dx, dy = (radius - 16) * math.cos(angle), (radius - 16) * math.sin(angle)
            dial.create_line(centre - dx, centre - dy, centre + dx, centre + dy, fill=GREEN, width=3)
            self.roll_label.config(text=f"{attitude['roll_deg']:+8.2f} deg", fg=INK)
            self.rate_label.config(text=f"{attitude['rate_deg_s']:+8.2f} deg/s", fg=INK)
            note = f"Basis: {attitude['basis']}. {attitude['drift']}. {attitude['not_observed'].capitalize()}."
        else:
            span = radius * 0.7
            dial.create_line(centre - span, centre - span, centre + span, centre + span, fill=RED, width=4)
            dial.create_line(centre - span, centre + span, centre + span, centre - span, fill=RED, width=4)
            self.roll_label.config(text="ATTITUDE INVALID", fg=RED)
            self.rate_label.config(text=attitude["reason"], fg=RED)
            note = f"No old value is held on screen. {attitude['not_observed'].capitalize()}."
        self.attitude_note.config(text=note)
        self._draw_servo(attitude)

    def _draw_servo(self, attitude):
        servo, width = self.servo, DIAL
        servo.delete("all")
        servo.create_rectangle(1, 2, width - 1, 16, outline=DIM)
        servo.create_line(width / 2, 0, width / 2, 18, fill=DIM)
        limit = attitude["limit_deg"]
        output = attitude["output_deg"]
        if output is None:
            servo.create_text(width / 2, 29, text="SERVO --", fill=DIM, font=(MONO, 9))
            return
        fraction = max(-1.0, min(1.0, output / limit))
        end = width / 2 + fraction * (width / 2 - 2)
        servo.create_rectangle(min(width / 2, end), 4, max(width / 2, end), 14,
                               fill=AMBER if abs(fraction) >= 1 else GREEN, outline="")
        servo.create_text(width / 2, 29, text=f"SERVO {output:+.0f} of ±{limit} deg", fill=INK, font=(MONO, 9))

    def _draw_advisories(self, advisories):
        text = self.advisory_text
        first_visible = text.yview()[0]
        text.config(state=tk.NORMAL)
        text.delete("1.0", tk.END)
        if not advisories:
            text.insert(tk.END, "None active.\n", "detail")
        for advisory in advisories:
            text.insert(tk.END, f"{advisory['level']:<9}{advisory['text']}\n", advisory["level"])
            text.insert(tk.END, f"{advisory['detail']}\n", "detail")
        text.config(state=tk.DISABLED)
        text.yview_moveto(first_visible)


class DemoFeed:
    """Plays invented packets into a GroundStatus once, then holds the final moment on screen."""

    def __init__(self, root, status, clock):
        self.root, self.status, self.clock = root, status, clock
        self.events = synthetic_demo_events()
        self.index = 0

    def tick(self):
        if self.index >= len(self.events):
            return  # The clock stops too, so the ending stays readable instead of aging into silence.
        self.clock.advance(0.05)
        while self.index < len(self.events) and self.events[self.index][0] <= self.clock.scenario:
            _, _, kind, payload = self.events[self.index]
            if kind == "packet":
                self.status.observe(payload)
            else:
                self.status.command_sent(payload)
            self.index += 1
        self.root.after(50, self.tick)


class DemoClock:
    def __init__(self):
        self.scenario = 0.0

    def __call__(self):
        return self.scenario

    def advance(self, seconds):
        self.scenario += seconds


def main():
    parser = argparse.ArgumentParser(description="Status board demonstration with invented packets.")
    parser.add_argument("--demo", action="store_true", required=True,
                        help="Play the synthetic scenario. Live use is through Firmware/dashboard.py.")
    parser.parse_args()
    root = tk.Tk()
    root.withdraw()
    clock = DemoClock()
    status = GroundStatus(clock=clock)
    panel = StatusPanel(root, status, banner="SYNTHETIC DEMO · invented packets · no hardware")
    panel.window.protocol("WM_DELETE_WINDOW", root.destroy)
    DemoFeed(root, status, clock).tick()
    root.mainloop()


if __name__ == "__main__":
    main()
