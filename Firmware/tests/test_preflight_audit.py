import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

FIRMWARE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FIRMWARE_DIR))

import preflight_audit as pa

ENV = "ENV,0.000000,0.000000,212.3,1"
RUN_THROUGH = [
    (0, "T,1000,0.1,0.2,0"), (0, "STATUS:IDLE,0.50,0.20,1.30"), (0, ENV),
    (10, "T,11000,0.1,0.2,0"), (10, "STATUS:IDLE,0.50,0.20,1.42"),  # The calibrate at 8 s moved skew.
    (20, "T,21000,0.1,0.2,0"), (20, "STATUS:ARMED,0.50,0.20,1.37"),
    (30, "ABORT:Arming switch flipped OFF."),
    (31, "T,31000,0.1,0.2,0"), (31, "STATUS:ARMED,0.50,0.20,1.37"),
    (41, "CMD_REJECT:dashboard_launch_disabled"),
]
COMMANDS = [(8, "calibrate", "sent"), (40, "launch", "sent")]
CLEAN = {"session_id": "bench_x", "closed_cleanly": True, "dashboard": {"worktree_dirty": False}}


def make_session(root, rows, commands=(), metadata=CLEAN, declaration=None):
    directory = Path(root) / "session"
    directory.mkdir()
    with (directory / "telemetry.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["received_at_iso", "raw", "origin"], lineterminator="\n")
        writer.writeheader()
        for second, raw in rows:
            writer.writerow({"received_at_iso": f"2000-01-01T00:{second // 60:02d}:{second % 60:02d}.000+00:00",
                             "raw": raw, "origin": "synthetic"})
    with (directory / "commands.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sent_utc", "command", "outcome"], lineterminator="\n")
        writer.writeheader()
        for second, command, outcome in commands:
            writer.writerow({"sent_utc": f"2000-01-01T00:{second // 60:02d}:{second % 60:02d}.000+00:00",
                             "command": command, "outcome": outcome})
    if metadata is not None:
        (directory / "session.json").write_text(json.dumps(metadata), encoding="utf-8")
    if declaration is not None:
        (directory / "declaration.json").write_text(json.dumps(declaration), encoding="utf-8")
    return directory


def audit(rows, commands=(), **kwargs):
    with tempfile.TemporaryDirectory() as tmp:
        return pa.build_report(make_session(tmp, rows, commands, **kwargs))


def statuses(report):
    return {step["step"]: step["status"] for step in report["steps"]}


class PreflightAuditTests(unittest.TestCase):
    def test_a_full_run_through_reports_what_each_step_left_behind(self):
        self.assertEqual(statuses(audit(RUN_THROUGH, COMMANDS)), {
            1: pa.OPERATOR_ONLY, 2: pa.OPERATOR_ONLY, 3: pa.OBSERVED, 4: pa.OBSERVED, 5: pa.OBSERVED,
            6: pa.INFERRED, 7: pa.OBSERVED, 8: pa.OBSERVED, 9: pa.OBSERVED, 10: pa.OBSERVED})

    def test_every_checklist_step_gets_exactly_one_result(self):
        report = audit(RUN_THROUGH, COMMANDS)
        self.assertEqual([step["step"] for step in report["steps"]], list(range(1, 11)))
        self.assertEqual(sum(report["tally"].values()), 10)

    def test_an_empty_capture_claims_nothing(self):
        report = audit([], metadata=None)
        for number, status in statuses(report).items():
            self.assertIn(status, (pa.NOT_OBSERVED, pa.OPERATOR_ONLY), number)
        self.assertEqual(report["raised"], [])

    def test_the_stage_line_says_this_is_not_evidence(self):
        self.assertIn("Not evidence", audit(RUN_THROUGH, COMMANDS)["stage"])

    def test_rocket_left_armed_after_the_abort_is_called_out(self):
        warnings = audit(RUN_THROUGH, COMMANDS)["warnings"]
        self.assertTrue(any("D-025" in warning and "ARMED" in warning for warning in warnings), warnings)

    def test_restarted_rocket_does_not_raise_the_armed_warning(self):
        rows = RUN_THROUGH + [(50, "T,1000,0.0,0.0,0"), (50, "STATUS:IDLE,0.50,0.20,1.28")]
        report = audit(rows, COMMANDS)
        self.assertEqual(report["warnings"], [])
        self.assertTrue(any(entry["id"] == "C-ROCKET-RESTART" for entry in report["raised"]))

    def test_armed_from_the_first_row_does_not_show_ready_was_reached(self):
        report = audit([(0, "STATUS:ARMED,0.50,0.20,1.30")])
        self.assertEqual(statuses(report)[6], pa.NOT_OBSERVED)
        self.assertIn("already ARMED", report["steps"][5]["note"])

    def test_abort_for_another_reason_is_not_the_switch_reset(self):
        report = audit([(0, "T,1,0,0,0"), (1, "ABORT:Rocket Timeout.")])
        self.assertEqual(statuses(report)[7], pa.NOT_OBSERVED)
        self.assertIn("Rocket Timeout", report["steps"][6]["note"])

    def test_calibration_without_a_skew_change_is_sent_only(self):
        rows = [(0, "STATUS:IDLE,0.50,0.20,1.30"), (10, "STATUS:IDLE,0.50,0.20,1.30")]
        report = audit(rows, [(5, "calibrate", "sent")])
        self.assertEqual(statuses(report)[8], pa.SENT_ONLY)
        self.assertIn("does not show the command was lost", report["steps"][7]["note"])

    def test_a_skew_change_long_after_the_command_does_not_count(self):
        rows = [(0, "STATUS:IDLE,0.50,0.20,1.30"), (30, "STATUS:IDLE,0.50,0.20,1.42")]
        self.assertEqual(statuses(audit(rows, [(5, "calibrate", "sent")]))[8], pa.SENT_ONLY)

    def test_a_failed_send_is_not_a_sent_command(self):
        self.assertEqual(statuses(audit([(0, "T,1,0,0,0")], [(0, "calibrate", "send_failed: x")]))[8], pa.NOT_OBSERVED)

    def test_launch_accepted_contradicts_the_step(self):
        report = audit([(0, "T,1,0,0,0"), (2, "CMD_ACK:launch_ready")], [(1, "launch", "sent")])
        self.assertEqual(statuses(report)[9], pa.CONTRADICTED)

    def test_not_ready_refusal_still_shows_launch_was_enabled(self):
        report = audit([(0, "T,1,0,0,0"), (2, "CMD_REJECT:launch_not_ready")], [(1, "launch", "sent")])
        self.assertEqual(statuses(report)[9], pa.CONTRADICTED)

    def test_refusal_before_the_request_does_not_answer_it(self):
        report = audit([(0, "CMD_REJECT:dashboard_launch_disabled"), (9, "T,1,0,0,0")], [(5, "launch", "sent")])
        self.assertEqual(statuses(report)[9], pa.NOT_OBSERVED)

    def test_unclean_close_is_not_observed(self):
        report = audit(RUN_THROUGH, COMMANDS, metadata=dict(CLEAN, closed_cleanly=False))
        self.assertEqual(statuses(report)[10], pa.NOT_OBSERVED)

    def test_declared_commit_is_labeled_as_a_statement(self):
        report = audit(RUN_THROUGH, COMMANDS, declaration={"firmware_commit": "abc123"})
        self.assertEqual(statuses(report)[2], pa.DECLARED)
        self.assertIn("abc123", report["steps"][1]["note"])

    def test_cli_refuses_to_write_inside_the_session_and_never_changes_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = make_session(tmp, RUN_THROUGH, COMMANDS)
            before = {path.name: path.read_bytes() for path in session.iterdir()}
            script = str(FIRMWARE_DIR / "preflight_audit.py")
            refused = subprocess.run([sys.executable, script, str(session), "--output", str(session / "audit.txt")],
                                     capture_output=True, text=True)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("raw capture", refused.stderr)
            printed = subprocess.run([sys.executable, script, str(session)], capture_output=True, text=True, check=True)
            self.assertIn("Preflight steps:", printed.stdout)
            as_json = subprocess.run([sys.executable, script, str(session), "--json"], capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(as_json.stdout)["session"], "session")
            self.assertEqual({path.name: path.read_bytes() for path in session.iterdir()}, before)


if __name__ == "__main__":
    unittest.main()
