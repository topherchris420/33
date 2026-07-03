import csv
import sys
import tempfile
from pathlib import Path
import unittest


FIRMWARE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FIRMWARE_DIR))

from telemetry_log import TelemetryCsvLogger


class TelemetryCsvLoggerTests(unittest.TestCase):
    def test_writes_t_status_and_env_packets_to_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "flight.csv"
            logger = TelemetryCsvLogger(path)

            logger.log_packet("T,1234,5.2,-3.1,4")
            logger.log_packet("STATUS:FLIGHT,0.50,0.20,1.30")
            logger.log_packet("ENV,34.146700,-118.388500,200.5,2")
            logger.close()

            rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["message_type"], "T")
        self.assertEqual(rows[0]["time_ms"], "1234")
        self.assertEqual(rows[0]["roll_deg"], "5.2")
        self.assertEqual(rows[0]["rate_deg_s"], "-3.1")
        self.assertEqual(rows[0]["servo_output"], "4")

        self.assertEqual(rows[1]["message_type"], "STATUS")
        self.assertEqual(rows[1]["state"], "FLIGHT")
        self.assertEqual(rows[1]["kp"], "0.50")
        self.assertEqual(rows[1]["kd"], "0.20")
        self.assertEqual(rows[1]["skew_deg"], "1.30")

        self.assertEqual(rows[2]["message_type"], "ENV")
        self.assertEqual(rows[2]["latitude"], "34.146700")
        self.assertEqual(rows[2]["longitude"], "-118.388500")
        self.assertEqual(rows[2]["altitude_m"], "200.5")
        self.assertEqual(rows[2]["gps_state"], "2")

    def test_preserves_unknown_packets_as_raw_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "flight.csv"
            logger = TelemetryCsvLogger(path)

            logger.log_packet("[FUSION] Hdg: 123.4 | Pitch: +01.2")
            logger.close()

            rows = list(csv.DictReader(path.open(newline="", encoding="utf-8")))

        self.assertEqual(rows[0]["message_type"], "RAW")
        self.assertEqual(rows[0]["raw"], "[FUSION] Hdg: 123.4 | Pitch: +01.2")


if __name__ == "__main__":
    unittest.main()
