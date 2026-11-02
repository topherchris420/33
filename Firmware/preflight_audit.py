"""Compare a recorded bench session with the inert preflight checklist in docs/SAFETY.md.

Offline and read-only: it opens no connection, sends nothing, and never changes the
session folder. For each step it reports what the record holds:

    OBSERVED       The record holds what this step leaves behind.
    INFERRED       The record implies it through firmware logic; nothing reports it directly.
    DECLARED       A person stated it in the session declaration. Nothing here checks it.
    SENT ONLY      The command was sent and left no visible result.
    NOT OBSERVED   The record could show this and does not.
    CONTRADICTED   The record shows something this step rules out.
    OPERATOR ONLY  Packets cannot show this. Only a person can confirm it.

OBSERVED never means the step was done correctly, safely, or in order. This is a derived
view of a raw session: it is not evidence, and it cannot accept a session.

    python Firmware/preflight_audit.py Firmware/TestSessions/bench_EXAMPLE
"""

import argparse
import json
from pathlib import Path
import sys

import ground_status as gs

OBSERVED, INFERRED, DECLARED, SENT_ONLY = "OBSERVED", "INFERRED", "DECLARED", "SENT ONLY"
NOT_OBSERVED, CONTRADICTED, OPERATOR_ONLY = "NOT OBSERVED", "CONTRADICTED", "OPERATOR ONLY"

STAGE = ("DERIVED VIEW of a raw session. Not evidence; it cannot accept a session or establish hardware "
         "behavior. OBSERVED means the record holds what a step leaves behind, not that the step was done "
         "correctly, safely, or in order.")

SWITCH_ABORT = "Arming switch flipped OFF."
LAUNCH_REFUSED = "CMD_REJECT:dashboard_launch_disabled"
LAUNCH_ENABLED_REPLIES = ("CMD_ACK:launch_ready", "CMD_REJECT:launch_not_ready")  # Sent only with the opt-in built.
ACTIVE_STATES = ("ARMED", "IGNITING", "FLIGHT")

# Word for word from docs/SAFETY.md; tests/test_ground_status_model.py fails if they drift apart.
STEPS = (
    "Verify wiring against [WIRING.md](WIRING.md).",
    "Build both PlatformIO projects from a recorded commit.",
    "Connect to the launcher access point.",
    'Start the dashboard and confirm the session ID, "RAW SESSION", and the data-quality line appear.',
    'Confirm GPS status, altitude (or "not reported"), and heartbeat telemetry update.',
    "Flip the arming switch and verify the launcher reaches `READY`.",
    "Confirm switch reset returns the launcher to `SAFE` and an `ABORT:` row is logged.",
    "Run calibration with the rocket held still; the dashboard records that it was sent (the firmware does not acknowledge it).",
    "Confirm digital launch is rejected by default and `CMD_REJECT:dashboard_launch_disabled` is logged; enable it only for a separately reviewed inert test.",
    "Close the dashboard so `session.json` records a clean close, then run `python -m evidence session declare` and `session passport`.",
)


def _read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


class Record:
    """What one session folder holds, in received order."""

    def __init__(self, session_dir):
        session_dir = Path(session_dir)
        self.metadata = _read_json(session_dir / "session.json")
        self.declaration = _read_json(session_dir / "declaration.json")
        self.events, self.origins = gs.session_events(session_dir)
        self.start = self.events[0][0] if self.events else 0.0
        self.counts = {"T": 0, "ENV": 0}
        self.gps_states, self.altitudes = [], 0
        self.statuses = []  # (seconds, state, skew text)
        self.aborts = []  # (seconds, reason)
        self.replies = []  # (seconds, CMD_REJECT or CMD_ACK text)
        self.commands = []  # (seconds, command)
        for at, _, kind, payload in self.events:
            seconds, text = at - self.start, payload.strip()
            if kind == "command":
                self.commands.append((seconds, text))
            else:
                self._read_packet(seconds, text)

    def _read_packet(self, seconds, text):
        if text.startswith("T,"):
            self.counts["T"] += 1
        elif text.startswith("ENV,"):
            self.counts["ENV"] += 1
            parts = text.split(",")
            if len(parts) >= 5:
                self.gps_states.append(parts[4].strip())
                self.altitudes += gs._finite(parts[3]) is not None
        elif text.startswith("STATUS:"):
            parts = text.split(":", 1)[1].split(",")
            self.statuses.append((seconds, parts[0].strip(), parts[3].strip() if len(parts) >= 4 else None))
        elif text.startswith("ABORT:"):
            self.aborts.append((seconds, text.split(":", 1)[1].strip()))
        elif text.startswith(("CMD_REJECT:", "CMD_ACK:")):
            self.replies.append((seconds, text))

    @property
    def packets(self):
        return sum(1 for event in self.events if event[2] == "packet")

    def sent(self, command):
        return [seconds for seconds, text in self.commands if text == command]

    def first_armed(self):
        """When the rocket went IDLE to ARMED; None if this capture never saw it happen."""
        previous = None
        for seconds, state, _ in self.statuses:
            if previous == "IDLE" and state == "ARMED":
                return seconds
            previous = state
        return None

    def skew_changed_within(self, start, window):
        before = None
        for seconds, _, skew in self.statuses:
            if seconds <= start:
                before = skew
            elif seconds <= start + window and before is not None and skew != before:
                return True
        return False


def _result(status, note):
    return {"status": status, "note": note}


def _wiring(_record):
    return _result(OPERATOR_ONLY, "Packets cannot show how the boards are wired.")


def _build(record):
    declared = (record.declaration or {}).get("firmware_commit")
    if declared:
        return _result(DECLARED, f"Declared firmware commit {declared}. Nothing here links that commit to what the boards are running.")
    return _result(OPERATOR_ONLY, "No firmware commit is declared yet. The dashboard records its own commit, not the boards'.")


def _connect(record):
    if record.packets:
        return _result(OBSERVED, f"{record.packets} packets arrived from the launcher.")
    return _result(NOT_OBSERVED, "No packets are in the capture.")


def _dashboard(record):
    if record.metadata and record.metadata.get("session_id"):
        return _result(OBSERVED, f"session.json identifies {record.metadata['session_id']}. What the screen showed is not recorded.")
    return _result(NOT_OBSERVED, "No readable session.json with a session ID.")


def _environment(record):
    missing = [name for name, count in (("T", record.counts["T"]), ("ENV", record.counts["ENV"])) if not count]
    if missing:
        return _result(NOT_OBSERVED, f"No {' or '.join(missing)} rows in the capture.")
    named = {"0": "no NMEA", "1": "no fix", "2": "fix"}
    seen = sorted({named.get(state, f"unknown {state}") for state in record.gps_states})
    return _result(OBSERVED, f"{record.counts['T']} T rows and {record.counts['ENV']} ENV rows. GPS seen as: {', '.join(seen) or 'not reported'}. "
                             f"Altitude reported in {record.altitudes} of {record.counts['ENV']} ENV rows.")


def _ready(record):
    armed = record.first_armed()
    if armed is not None:
        return _result(INFERRED, f"The launcher reports no state. The rocket went IDLE to ARMED at {armed:.1f} s, and the launcher sends ARM only on entering READY.")
    if record.statuses and record.statuses[0][1] in ACTIVE_STATES:
        return _result(NOT_OBSERVED, f"The rocket was already {record.statuses[0][1]} when the capture began, so this session does not show the launcher reaching READY.")
    return _result(NOT_OBSERVED, "The rocket never went IDLE to ARMED. The launcher reports no state, and a READY shown only on its LED is not in this record.")


def _switch_reset(record):
    for seconds, reason in record.aborts:
        if reason == SWITCH_ABORT:
            return _result(OBSERVED, f"ABORT row at {seconds:.1f} s. The launcher does not report SAFE itself.")
    if record.aborts:
        reasons = "; ".join(reason for _, reason in record.aborts)
        return _result(NOT_OBSERVED, f"The only aborts have other reasons: {reasons}")
    return _result(NOT_OBSERVED, "No ABORT row in the capture.")


def _calibration(record):
    sent = record.sent("calibrate")
    if not sent:
        return _result(NOT_OBSERVED, "No calibrate command was sent.")
    held_still = "Whether the rocket was held still is not recorded."
    if any(record.skew_changed_within(seconds, gs.CALIBRATION_WINDOW_S) for seconds in sent):
        return _result(OBSERVED, f"Skew changed after a calibrate command, which is the only sign firmware gives. {held_still}")
    return _result(SENT_ONLY, f"Sent {len(sent)} time(s) with no skew change. Skew is reported to 0.01 deg, so this does not show the command was lost. {held_still}")


def _launch_refused(record):
    enabled = [text for _, text in record.replies if text in LAUNCH_ENABLED_REPLIES]
    if enabled:
        return _result(CONTRADICTED, f"{enabled[0]} is only sent by a launcher built with dashboard launch enabled.")
    sent = record.sent("launch")
    if not sent:
        return _result(NOT_OBSERVED, "No launch request was sent, so its refusal was not exercised.")
    if any(seconds >= sent[0] and text == LAUNCH_REFUSED for seconds, text in record.replies):
        return _result(OBSERVED, f"{LAUNCH_REFUSED} logged after the request.")
    return _result(NOT_OBSERVED, "A launch request was sent and no refusal is logged. UDP does not guarantee delivery.")


def _close(record):
    if not record.metadata or record.metadata.get("closed_cleanly") is not True:
        return _result(NOT_OBSERVED, "session.json does not record a clean close.")
    declared = "declaration.json is present" if record.declaration else "no declaration.json yet"
    return _result(OBSERVED, f"Clean close recorded; {declared}. Passports are built outside this folder and are not checked here.")


CHECKS = (_wiring, _build, _connect, _dashboard, _environment, _ready, _switch_reset, _calibration, _launch_refused, _close)


def _warnings(record):
    """Conditions a person should act on, whichever steps were recorded."""
    warnings = []
    last_abort = record.aborts[-1][0] if record.aborts else None
    after = [state for seconds, state, _ in record.statuses if last_abort is not None and seconds > last_abort]
    if after and after[-1] in ACTIVE_STATES:
        warnings.append(f"The rocket still reported {after[-1]} after the last launcher abort. Its deploy trigger stays live and the "
                        "launcher cannot re-arm it until the rocket is restarted (D-025).")
    if record.metadata and (record.metadata.get("dashboard") or {}).get("worktree_dirty"):
        warnings.append("The dashboard ran from a modified worktree.")
    return warnings


def build_report(session_dir, model=None):
    record = Record(session_dir)
    steps = []
    for number, (text, check) in enumerate(zip(STEPS, CHECKS), start=1):
        steps.append(dict(check(record), step=number, text=text))
    raised = []
    if record.events:
        timeline = gs.replay(record.events, model=model)["timeline"]
        raised = [entry for entry in timeline if entry["level"] in (gs.WARNING, gs.CAUTION)]
    tally = {}
    for step in steps:
        tally[step["status"]] = tally.get(step["status"], 0) + 1
    return {"session": Path(session_dir).name, "stage": STAGE, "origins": record.origins, "steps": steps,
            "tally": tally, "warnings": _warnings(record), "raised": raised}


def format_report(report):
    lines = [f"Session: {report['session']}", report["stage"]]
    if report["origins"]:
        lines.append("In-band origin column: " + ", ".join(report["origins"]))
    lines += ["", "Preflight steps:"]
    for step in report["steps"]:
        lines.append(f"  {step['step']:>2}. {step['status']:<14} {step['note']}")
    lines += ["", "Tally: " + ", ".join(f"{count} {status}" for status, count in sorted(report["tally"].items()))]
    if report["warnings"]:
        lines += ["", "Act on these:"] + [f"  - {warning}" for warning in report["warnings"]]
    lines += ["", "Warnings and cautions the status board would have raised:"]
    if not report["raised"]:
        lines.append("  none")
    for entry in report["raised"]:
        lines.append(f"  {entry['start']:8.1f} s  {entry['level']:<8} {entry['text']}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare a raw dashboard session with the inert preflight checklist. Sends nothing.")
    parser.add_argument("session", help="Session folder containing telemetry.csv")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON")
    parser.add_argument("--output", help="Write the report here; refused inside the session folder")
    args = parser.parse_args(argv)
    session = Path(args.session).resolve()
    if not (session / "telemetry.csv").is_file():
        parser.error(f"no telemetry.csv in {session}")
    if args.output and session in Path(args.output).resolve().parents:
        parser.error("refusing to write inside the session folder: it holds raw capture files that a passport hashes")
    report = build_report(session)
    text = json.dumps(report, indent=2, sort_keys=True) if args.json else format_report(report)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8", newline="\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
