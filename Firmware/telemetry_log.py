import csv
from datetime import datetime, timezone
from pathlib import Path
import threading


FIELDNAMES = [
    "received_at_iso",
    "source",
    "message_type",
    "time_ms",
    "roll_deg",
    "rate_deg_s",
    "servo_output",
    "state",
    "kp",
    "kd",
    "skew_deg",
    "latitude",
    "longitude",
    "altitude_m",
    "gps_state",
    "raw",
]


class TelemetryCsvLogger:
    """Thread-safe CSV logger for launcher dashboard UDP packets."""

    def __init__(self, path=None):
        self.path = Path(path) if path is not None else self.default_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._file = self.path.open("w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=FIELDNAMES)
        self._writer.writeheader()
        self._file.flush()

    @staticmethod
    def default_path():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return Path(__file__).resolve().parent / "TelemetryLogs" / f"flight_{stamp}.csv"

    def log_packet(self, message, source="udp"):
        row = self._parse_packet(message, source)
        with self._lock:
            self._writer.writerow(row)
            self._file.flush()

    def close(self):
        with self._lock:
            if not self._file.closed:
                self._file.flush()
                self._file.close()

    def _base_row(self, message, source):
        return {
            "received_at_iso": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "source": source,
            "raw": message,
        }

    def _parse_packet(self, message, source):
        message = str(message).strip()
        row = self._base_row(message, source)

        if message.startswith("T,"):
            parts = message.split(",")
            if len(parts) >= 5:
                row.update(
                    {
                        "message_type": "T",
                        "time_ms": parts[1],
                        "roll_deg": parts[2],
                        "rate_deg_s": parts[3],
                        "servo_output": parts[4],
                    }
                )
                return row

        if message.startswith("STATUS:"):
            parts = message.split(":", 1)[1].split(",")
            row["message_type"] = "STATUS"
            if len(parts) >= 1:
                row["state"] = parts[0]
            if len(parts) >= 4:
                row.update({"kp": parts[1], "kd": parts[2], "skew_deg": parts[3]})
            return row

        if message.startswith("ENV,"):
            parts = message.split(",")
            row["message_type"] = "ENV"
            if len(parts) >= 5:
                row.update(
                    {
                        "latitude": parts[1],
                        "longitude": parts[2],
                        "altitude_m": parts[3],
                        "gps_state": parts[4],
                    }
                )
            return row

        row["message_type"] = "RAW"
        return row
