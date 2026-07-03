import csv
from pathlib import Path
import sys
import tempfile
import unittest


FIRMWARE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FIRMWARE_DIR))

from analyze_pid import summarize_pid_csv
from session_artifacts import TestSessionArtifacts


class TestSessionArtifactsTests(unittest.TestCase):
    def test_creates_session_paths_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = TestSessionArtifacts(root=tmp, session_id="bench_001")

            self.assertEqual(session.session_dir, Path(tmp) / "bench_001")
            self.assertEqual(session.telemetry_csv.name, "telemetry.csv")
            self.assertEqual(session.graph_png.name, "graph.png")

            session.write_summary(packet_count=42, notes="servo centering run")
            summary = session.summary_md.read_text(encoding="utf-8")

        self.assertIn("# Bench Session bench_001", summary)
        self.assertIn("telemetry.csv", summary)
        self.assertIn("graph.png", summary)
        self.assertIn("servo centering run", summary)

    def test_pid_summary_groups_by_active_pid_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "telemetry.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "message_type",
                        "time_ms",
                        "roll_deg",
                        "rate_deg_s",
                        "servo_output",
                        "kp",
                        "kd",
                    ],
                )
                writer.writeheader()
                writer.writerow({"message_type": "STATUS", "kp": "0.50", "kd": "0.20"})
                writer.writerow(
                    {
                        "message_type": "T",
                        "time_ms": "100",
                        "roll_deg": "4.0",
                        "rate_deg_s": "-2.0",
                        "servo_output": "3",
                    }
                )
                writer.writerow(
                    {
                        "message_type": "T",
                        "time_ms": "150",
                        "roll_deg": "-2.0",
                        "rate_deg_s": "1.0",
                        "servo_output": "-1",
                    }
                )
                writer.writerow({"message_type": "STATUS", "kp": "0.80", "kd": "0.30"})
                writer.writerow(
                    {
                        "message_type": "T",
                        "time_ms": "200",
                        "roll_deg": "1.0",
                        "rate_deg_s": "5.0",
                        "servo_output": "6",
                    }
                )

            summaries = summarize_pid_csv(csv_path)

        self.assertEqual(len(summaries), 2)
        first = summaries[0]
        self.assertEqual(first.kp, "0.50")
        self.assertEqual(first.kd, "0.20")
        self.assertEqual(first.samples, 2)
        self.assertEqual(first.mean_abs_roll, 3.0)
        self.assertEqual(first.peak_abs_roll, 4.0)
        self.assertEqual(first.peak_abs_servo_output, 3.0)


if __name__ == "__main__":
    unittest.main()
