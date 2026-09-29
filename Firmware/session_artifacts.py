"""Files produced by one dashboard bench session.

A session folder is a RAW SESSION: raw capture plus what the dashboard itself
knows (times, its own revision, commands it sent). It is not evidence until it
is audited, declared by the operator, and accepted by a named human. Facts the
dashboard cannot know are written as NOT RECORDED rather than guessed.
"""

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import threading

REPO_ROOT = Path(__file__).resolve().parents[1]
NOT_RECORDED = [
    "firmware revision (not reported by the device)",
    "hardware revision (declare with python -m evidence session declare)",
    "calibration result (CALIBRATE is not acknowledged by firmware)",
    "device boot identifier and packet sequence numbers (not in the protocol)",
    "evidence origin (undeclared until the operator declares it)",
]


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _file_sha256(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def _git_commit():
    try:
        commit = subprocess.check_output(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
                                         stderr=subprocess.DEVNULL, timeout=5).decode().strip()
        dirty = bool(subprocess.check_output(["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
                                             stderr=subprocess.DEVNULL, timeout=5).strip())
        return commit, dirty
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return None, None


class TestSessionArtifacts:
    __test__ = False
    """Owns the files produced by one bench-test session."""

    def __init__(self, root=None, session_id=None, *, record_metadata=True, now=None):
        self.root = Path(root) if root is not None else Path(__file__).resolve().parent / "TestSessions"
        self.session_id = session_id or datetime.now().strftime("bench_%Y%m%d_%H%M%S")
        self.session_dir = self.root / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.telemetry_csv = self.session_dir / "telemetry.csv"
        self.graph_png = self.session_dir / "graph.png"
        self.summary_md = self.session_dir / "session-summary.md"
        self.pid_markdown = self.session_dir / "pid-comparison.md"
        self.session_json = self.session_dir / "session.json"
        self.commands_csv = self.session_dir / "commands.csv"
        self._lock = threading.Lock()
        self.commands_sent = 0
        self.metadata = None
        if record_metadata:
            commit, dirty = _git_commit()
            self.metadata = {
                "schema": "project33.session/1",
                "session_id": self.session_id,
                "evidence_stage": "RAW SESSION — not evidence until audited, declared, and accepted by a named human",
                "capture_started_utc": now or _utc_now(),
                "capture_ended_utc": None,
                "closed_cleanly": False,
                "packets_logged": None,
                "dashboard": {"path": "Firmware/dashboard.py", "sha256": _file_sha256(REPO_ROOT / "Firmware/dashboard.py"),
                              "git_commit": commit, "worktree_dirty": dirty},
                "protocol": {"path": "protocol/project33_protocol.json",
                             "sha256": _file_sha256(REPO_ROOT / "protocol/project33_protocol.json")},
                "not_recorded": NOT_RECORDED,
            }
            self._write_metadata()
            with self.commands_csv.open("w", newline="", encoding="utf-8") as handle:
                csv.writer(handle, lineterminator="\n").writerow(["sent_utc", "command", "outcome"])

    def _write_metadata(self):
        self.session_json.write_text(json.dumps(self.metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def log_command(self, command, outcome="sent", now=None):
        """Record a command the dashboard sent. Delivery is not confirmed by UDP."""
        with self._lock:
            with self.commands_csv.open("a", newline="", encoding="utf-8") as handle:
                csv.writer(handle, lineterminator="\n").writerow([now or _utc_now(), command, outcome])
            self.commands_sent += 1

    def close(self, packet_count, now=None):
        if self.metadata is None:
            return
        self.metadata.update(capture_ended_utc=now or _utc_now(), closed_cleanly=True, packets_logged=packet_count)
        self._write_metadata()

    def write_summary(self, packet_count=0, notes="", quality=None):
        lines = [
            f"# Bench Session {self.session_id}",
            "",
            "**Stage: RAW SESSION.** Not evidence until audited, declared by the operator, and accepted by a named human.",
            "",
            "## Artifacts",
            "",
            f"- Telemetry CSV: `{self.telemetry_csv.name}`",
            f"- Saved graph: `{self.graph_png.name}`",
            f"- PID comparison: `{self.pid_markdown.name}`",
            f"- Session metadata: `{self.session_json.name}`",
            f"- Commands sent: `{self.commands_csv.name}`",
            "",
            "## Run Summary",
            "",
            f"- Packets captured: {packet_count}",
            f"- Commands sent from the dashboard: {self.commands_sent}",
        ]
        if quality:
            lines += [f"- {label}: {value}" for label, value in quality.items()]
        if self.metadata:
            lines += [f"- Capture started (UTC): {self.metadata['capture_started_utc']}",
                      f"- Capture ended (UTC): {self.metadata['capture_ended_utc'] or 'NOT RECORDED'}"]
        lines += ["", "## Not Recorded by the Dashboard", ""] + [f"- {item}" for item in NOT_RECORDED]
        lines += [
            "", "## Next Steps", "",
            "```bash",
            f"python -m evidence session declare {self.session_dir} --operator NAME --origin bench \\",
            "  --purpose \"ONE QUESTION\" --inert-configuration \"...\" --firmware-commit SHA --tests TAG",
            f"python -m evidence session passport {self.session_dir} --output build/{self.session_id}-passport",
            "```",
            "",
            "A clean audit is necessary, not sufficient: it cannot establish physical performance.",
        ]
        if notes:
            lines.extend(["", "## Notes", "", notes])
        self.summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return self.summary_md
