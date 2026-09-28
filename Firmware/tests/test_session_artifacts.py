import csv
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

FIRMWARE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FIRMWARE_DIR))

from analyze_pid import render_pid_markdown, summarize_pid_csv
from live_quality import LiveQuality
from session_artifacts import TestSessionArtifacts
from session_plot import break_at_gaps, gap_spans, render_session_graph

FIELDS = ["message_type", "time_ms", "roll_deg", "rate_deg_s", "servo_output", "kp", "kd"]


def write_rows(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


class TestSessionArtifactsTests(unittest.TestCase):
    def test_creates_session_paths_summary_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = TestSessionArtifacts(root=tmp, session_id="bench_001", now="2026-01-01T00:00:00+00:00")
            self.assertEqual(session.session_dir, Path(tmp) / "bench_001")
            metadata = json.loads(session.session_json.read_text())
            self.assertFalse(metadata["closed_cleanly"])
            self.assertIsNone(metadata["capture_ended_utc"])
            self.assertTrue(metadata["evidence_stage"].startswith("RAW SESSION"))
            self.assertIn("firmware revision (not reported by the device)", metadata["not_recorded"])

            session.log_command("PID,0.8,0.3", "sent", now="2026-01-01T00:00:01+00:00")
            session.log_command("launch", "send_failed: unreachable", now="2026-01-01T00:00:02+00:00")
            session.close(42, now="2026-01-01T00:01:00+00:00")
            metadata = json.loads(session.session_json.read_text())
            self.assertTrue(metadata["closed_cleanly"])
            self.assertEqual(metadata["packets_logged"], 42)
            commands = list(csv.DictReader(session.commands_csv.open(encoding="utf-8")))
            self.assertEqual([c["outcome"] for c in commands], ["sent", "send_failed: unreachable"])

            session.write_summary(packet_count=42, notes="servo centering run", quality={"Gaps over 500 ms": 1})
            summary = session.summary_md.read_text(encoding="utf-8")
        self.assertIn("# Bench Session bench_001", summary)
        self.assertIn("RAW SESSION", summary)
        self.assertIn("Commands sent from the dashboard: 2", summary)
        self.assertIn("Gaps over 500 ms: 1", summary)
        self.assertIn("python -m evidence session declare", summary)
        self.assertIn("servo centering run", summary)


class PidSummaryTests(unittest.TestCase):
    def test_windows_follow_gain_changes_not_status_packets(self):
        # The launcher sends a STATUS after every T packet; windows must not fragment.
        rows = []
        for index in range(6):
            gains = ("0.50", "0.20") if index < 4 else ("0.80", "0.30")
            rows.append({"message_type": "T", "time_ms": str(100 + 50 * index), "roll_deg": "4.0" if index % 2 else "-2.0",
                         "rate_deg_s": "1.0", "servo_output": "3"})
            rows.append({"message_type": "STATUS", "kp": gains[0], "kd": gains[1]})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "telemetry.csv"
            write_rows(path, rows)
            summaries, unattributed = summarize_pid_csv(path)
        self.assertEqual(unattributed, 1)  # the first T precedes any STATUS
        self.assertEqual([(s.kp, s.kd, s.samples) for s in summaries], [("0.50", "0.20", 4), ("0.80", "0.30", 1)])

    def test_invalid_values_are_counted_not_zero_filled(self):
        rows = [{"message_type": "STATUS", "kp": "0.5", "kd": "0.2"},
                {"message_type": "T", "time_ms": "0", "roll_deg": "10", "rate_deg_s": "1", "servo_output": "1"},
                {"message_type": "T", "time_ms": "50", "roll_deg": "nan", "rate_deg_s": "1", "servo_output": "1"},
                {"message_type": "T", "time_ms": "100", "roll_deg": "garbage", "rate_deg_s": "1", "servo_output": "1"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "telemetry.csv"
            write_rows(path, rows)
            (summary,), _ = summarize_pid_csv(path)
        self.assertEqual((summary.samples, summary.invalid_samples), (1, 2))
        self.assertEqual(summary.mean_abs_roll, 10.0)  # a zero-filled sample would have halved this

    def test_recovered_log_rows_use_their_own_gains_and_stream(self):
        rows = [{"message_type": "STATUS", "kp": "0.5", "kd": "0.2"},
                {"message_type": "T", "time_ms": "0", "roll_deg": "1", "rate_deg_s": "1", "servo_output": "1"},
                {"message_type": "LOG", "time_ms": "0", "roll_deg": "5", "rate_deg_s": "1", "servo_output": "1", "kp": "0.9", "kd": "0.1"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "telemetry.csv"
            write_rows(path, rows)
            summaries, _ = summarize_pid_csv(path)
        self.assertEqual([(s.stream, s.kp, s.samples) for s in summaries], [("T", "0.5", 1), ("LOG", "0.9", 1)])

    def test_window_without_valid_samples_reports_not_measured(self):
        rows = [{"message_type": "STATUS", "kp": "0.5", "kd": "0.2"},
                {"message_type": "T", "time_ms": "0", "roll_deg": "nan", "rate_deg_s": "1", "servo_output": "1"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "telemetry.csv"
            write_rows(path, rows)
            summaries, _ = summarize_pid_csv(path)
        self.assertTrue(math.isnan(summaries[0].mean_abs_roll))
        self.assertIn("not measured", render_pid_markdown(summaries))


class LiveQualityTests(unittest.TestCase):
    def test_counts_invalid_gaps_regressions_and_rejections(self):
        now = [0.0]
        quality = LiveQuality(gap_ms=500, clock=lambda: now[0])
        self.assertIn("no packets yet", quality.status_line())
        for message in ["T,1000,1,1,1", "T,1050,nan,1,1", "T,2000,1,1,1", "T,10,1,1,1",
                        "LOG,5,1,1,1,IDLE,0.5,0.2,0", "CMD_REJECT:launch_not_ready", "STATUS:IDLE,0.50,0.20,1.0"]:
            quality.observe(message)
        now[0] = 3.0
        self.assertEqual((quality.samples["T"], quality.samples["LOG"], quality.invalid), (3, 1, 1))
        self.assertEqual((quality.gaps, quality.clock_regressions, len(quality.rejections)), (1, 1, 1))
        self.assertIn("STALE", quality.status_line())

    def test_commanded_gains_are_unconfirmed_until_status_matches(self):
        quality = LiveQuality()
        self.assertEqual(quality.gains_text(), "Gains observed: not received")
        quality.commanded(0.8, 0.3)
        self.assertIn("not yet confirmed", quality.gains_text())
        quality.observe("STATUS:ARMED,0.80,0.30,0.0")
        self.assertIn("confirmed by STATUS", quality.gains_text())
        self.assertIn("none sent", quality.calibration_text())
        quality.calibration_sent("12:00:00Z")
        self.assertIn("no acknowledgement", quality.calibration_text())


class SessionPlotTests(unittest.TestCase):
    def test_gaps_and_regressions_break_lines(self):
        t, v = break_at_gaps([0, 50, 700, 750, 10], [1, 2, 3, 4, 5], 500)
        self.assertEqual(len(t), 7)
        self.assertTrue(math.isnan(t[2]) and math.isnan(v[5]))
        self.assertEqual(gap_spans([0, 50, 700], 500), [(50, 700)])

    def test_graph_renders_with_units(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "graph.png"
            render_session_graph(path, [0, 50, 900], [1, 2, 3], [0, 1, 0], [0, 1, 2], session_id="bench_x",
                                 events=[{"time": 50, "state": "ARMED"}], gains_text="Gains observed: not received")
            self.assertGreater(path.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
