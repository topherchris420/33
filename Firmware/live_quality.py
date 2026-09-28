"""Live data-quality counters for the dashboard.

Pure logic with no GUI dependency, so it is tested in CI. It answers "is the
data trustworthy right now?" with counts, never with interpolation: a malformed
packet is counted, a gap is counted, and nothing missing is shown as zero.
"""

import math
import time

GAP_MS = 500


def _finite(text):
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


class LiveQuality:
    def __init__(self, gap_ms=GAP_MS, clock=time.monotonic):
        self.gap_ms = gap_ms
        self.clock = clock
        self.packets = 0
        self.samples = {"T": 0, "LOG": 0}
        self.invalid = 0
        self.gaps = 0
        self.clock_regressions = 0
        self.rejections = []
        self.last_packet_at = None
        self._last_device = {}
        self.gains_observed = None
        self.gains_commanded = None
        self.calibrations_sent = []

    def observe(self, message):
        """Classify one received packet and update counters. Returns the category."""
        self.packets += 1
        self.last_packet_at = self.clock()
        message = str(message).strip()
        if message.startswith(("CMD_REJECT:", "ABORT:")):
            self.rejections.append(message)
            return "rejection"
        if message.startswith("STATUS:"):
            parts = message.split(":", 1)[1].split(",")
            if len(parts) >= 3 and _finite(parts[1]) is not None and _finite(parts[2]) is not None:
                self.gains_observed = (parts[1], parts[2])
            return "status"
        kind = "T" if message.startswith("T,") else "LOG" if message.startswith("LOG,") else None
        if kind is None:
            return "other"
        parts = message.split(",")
        values = [_finite(p) for p in parts[2:5]] if len(parts) >= 5 else [None]
        device = parts[1] if len(parts) > 1 else ""
        if not device.isdecimal() or any(value is None for value in values):
            self.invalid += 1
            return "invalid"
        self.samples[kind] += 1
        device = int(device)
        previous = self._last_device.get(kind)
        if previous is not None:
            if device < previous:
                self.clock_regressions += 1
            elif device - previous > self.gap_ms:
                self.gaps += 1
        self._last_device[kind] = device
        return kind

    def commanded(self, kp, kd):
        self.gains_commanded = (f"{kp:.2f}", f"{kd:.2f}")

    def calibration_sent(self, stamp):
        self.calibrations_sent.append(stamp)

    def seconds_since_last_packet(self):
        return None if self.last_packet_at is None else self.clock() - self.last_packet_at

    def gains_text(self):
        observed = "not received" if self.gains_observed is None else f"Kp {self.gains_observed[0]} / Kd {self.gains_observed[1]}"
        if self.gains_commanded is None:
            return f"Gains observed: {observed}"
        confirmed = self.gains_observed is not None and all(
            abs(float(a) - float(b)) < 0.005 for a, b in zip(self.gains_observed, self.gains_commanded))
        state = "confirmed by STATUS" if confirmed else "not yet confirmed by STATUS"
        return (f"Gains observed: {observed} · commanded Kp {self.gains_commanded[0]} / "
                f"Kd {self.gains_commanded[1]} ({state})")

    def calibration_text(self):
        if not self.calibrations_sent:
            return "Calibration: none sent this session"
        return f"Calibration: sent {self.calibrations_sent[-1]} (firmware sends no acknowledgement)"

    def summary(self):
        age = self.seconds_since_last_packet()
        return {
            "Packets received": self.packets,
            "Live T samples": self.samples["T"],
            "Recovered LOG samples": self.samples["LOG"],
            "Invalid samples (excluded)": self.invalid,
            f"Gaps over {self.gap_ms} ms": self.gaps,
            "Clock regressions": self.clock_regressions,
            "Command rejections/aborts": len(self.rejections),
            "Seconds since last packet": "no packet received" if age is None else f"{age:.1f}",
        }

    def status_line(self):
        age = self.seconds_since_last_packet()
        age_text = "no packets yet" if age is None else f"last packet {age:.1f}s ago" + (" (STALE)" if age > 2 else "")
        return (f"{self.packets} packets · T {self.samples['T']} · LOG {self.samples['LOG']} · invalid {self.invalid} · "
                f"gaps>{self.gap_ms}ms {self.gaps} · clock regressions {self.clock_regressions} · "
                f"rejections {len(self.rejections)} · {age_text}")
