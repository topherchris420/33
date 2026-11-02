"""Model-based ground status for the inert bench dashboard.

Pure logic with no GUI, socket, or command path, so it runs in CI and offline
against a recorded session. It reads packets and reports what they support:

- which units have been seen working, and which are suspect (model-based
  diagnosis over protocol/ground_status_model.json);
- which capabilities those units support;
- the one attitude quantity the rocket reports, or an explicit invalid flag;
- gain entries as preselected, sent, confirmed, rejected, or not matching;
- whether a sent calibration left a visible change, since firmware sends no reply;
- what the rocket's pose implies for the accelerometer's roll correction;
- prioritized advisories, each with the reason it fired.

Everything here is an interpretation of telemetry. It cannot show that hardware
behaved correctly, and it is never evidence on its own. It never sends anything.
"""

import argparse
import csv
from datetime import datetime
from itertools import combinations
import json
import math
from pathlib import Path
import sys
import threading
import time

MODEL_PATH = Path(__file__).resolve().parents[1] / "protocol" / "ground_status_model.json"

PRESENT, ABSENT, PENDING, UNTESTED = "PRESENT", "ABSENT", "PENDING", "UNTESTED"
SEEN, SUSPECT, NOT_SEEN = "SEEN", "SUSPECT", "NOT SEEN"
SUPPORTED, AT_RISK, LOST, NOT_OBSERVED = "SUPPORTED", "AT RISK", "LOST", "NOT OBSERVED"
WARNING, CAUTION, ADVISORY = "WARNING", "CAUTION", "ADVISORY"
LEVEL_ORDER = {WARNING: 0, CAUTION: 1, ADVISORY: 2}

ATTITUDE_VALID_S = 0.5  # Same limit as live_quality.GAP_MS: older roll is not shown.
CONFIRM_WINDOW_S = 1.0  # STATUS arrives about 20 times a second when the rocket is reporting.
EVENT_HOLD_S = 30.0  # How long a one-shot event stays on the board.
FROZEN_SAMPLES = 40  # Heuristic, about 2 s at 20 Hz. Real sensor noise is NOT MEASURED.
GAIN_MATCH_TOLERANCE = 0.00501  # Firmware reports gains to two decimals.
CALIBRATION_WINDOW_S = 5.0  # Calibrating blocks the rocket about 1 s; this allows for relay and the next sample.
LOG_CLOCK_MARGIN_S = 5.0  # A dump can take about 2 s to arrive, so both of its ends can lag. Not measured.
WEAK_REFERENCE_PITCH_DEG = 85.0  # Heuristic. Error on the roll axes is magnified over 11 times here; noise is NOT MEASURED.

GEOMETRY_OK, WEAK_GEOMETRY, GYRO_ONLY = "GEOMETRY OK", "WEAK GEOMETRY", "GYRO ONLY"

# Every advisory the board can raise. docs/DEGRADED_MODES.md is generated from this.
ADVISORIES = {
    "W-ARMED-AFTER-ABORT": (WARNING, "The launcher aborted and the rocket still reports an active state. A launcher abort does not disarm the rocket, the launcher cannot re-arm it, and only a rocket restart returns it to IDLE (D-025)."),
    "W-ACTIVE-STATE-STALE": (WARNING, "The rocket last reported an active state and telemetry has stopped. Its state is unknown; loss of telemetry is not a safe indication."),
    "W-IGNITION-ACTUATION": (WARNING, "The rocket reports IGNITING or FLIGHT, so the ignition servo was commanded. FLIGHT does not confirm ignition. On the bench the servo must be mechanically disconnected."),
    "C-NO-PACKETS": (CAUTION, "Nothing is arriving from the launcher."),
    "C-ROCKET-TELEMETRY-LOST": (CAUTION, "The launcher is reporting but rocket telemetry has stopped."),
    "C-LAUNCHER-ABORT": (CAUTION, "The launcher reported an abort. Shown for 30 s."),
    "C-GAINS-NO-MATCH": (CAUTION, "Telemetry is flowing and still shows different gains from the ones sent."),
    "C-GAINS-REJECTED": (CAUTION, "A board rejected the gains that were sent."),
    "C-ROCKET-RESTART": (CAUTION, "Rocket state moved backwards, skew changed while IDLE with no calibration to explain it, or the rocket clock fell behind ground time between log dumps. Firmware has no other path to these, so a restart or brownout is inferred. A restart also returns gains to their defaults, zeroes roll, and loses the onboard log. Shown for 30 s."),
    "C-LAUNCHER-RESTART": (CAUTION, "The launcher clock went backwards, so a restart or brownout is inferred. Shown for 30 s."),
    "C-OUTPUT-OUTSIDE-FLIGHT": (CAUTION, "A non-zero servo output arrived outside FLIGHT, which firmware should not produce. Check the firmware and protocol revision."),
    "C-STATE-UNKNOWN": (CAUTION, "STATUS carried a state this model does not know. Check the firmware and protocol revision."),
    "C-UNKNOWN-COMMAND": (CAUTION, "The launcher did not recognize a dashboard command. Check the firmware and protocol revision. Shown for 30 s."),
    "A-LAUNCHER-HELD": (ADVISORY, "Rocket telemetry is flowing but ENV has paused, so the launcher is inside a wait: arming window, ignition wait, or abort latch."),
    "A-GPS-NO-NMEA": (ADVISORY, "ENV reports no characters from the GPS module."),
    "A-GPS-NO-FIX": (ADVISORY, "GPS is sending sentences without a fix. Position is unavailable, not zero."),
    "A-BARO-MISSING": (ADVISORY, "ENV reports no barometer. Altitude is unavailable, not zero."),
    "A-COMPASS-SILENT": (ADVISORY, "ENV is flowing without [FUSION], which is what a compass reading all zeros produces."),
    "A-IMU-FROZEN": (ADVISORY, "Roll and rate have been identical for about 2 s. The firmware does not detect a sensor failure after boot; this threshold is a heuristic because sensor noise is not measured."),
    "A-CANARD-LIMIT": (ADVISORY, "The servo output is at the firmware deflection limit."),
    "A-COMMAND-REFUSED": (ADVISORY, "A board refused a command. The default refusal of dashboard launch is expected. Shown for 30 s."),
    "A-GAINS-UNCONFIRMED": (ADVISORY, "Gains were sent and no telemetry arrived to confirm them."),
    "A-ROLL-REFERENCE-WEAK": (ADVISORY, "The rocket's body axis is within 5 degrees of vertical, so little gravity falls on the two axes firmware uses to correct roll, and error on them is magnified by 1/cos(pitch) (D-026). The threshold is a heuristic because sensor noise is not measured."),
    "A-CALIBRATION-NO-CHANGE": (ADVISORY, "Calibration was sent and telemetry is flowing, but skew did not change. This is not a refusal: firmware sends no reply, and skew is reported to 0.01 deg, so a recalibration can land on the same value. Shown for 30 s."),
    "A-LOG-PARTIAL": (ADVISORY, "A log dump ended with a different row count from the one it announced. Shown for 30 s."),
    "A-PROBE-UNANSWERED": (ADVISORY, "A log dump got no reply while telemetry shows the path working, so the command or reply was probably lost; UDP does not guarantee delivery."),
}


def load_model(path=MODEL_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _finite(text):
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _fusion_pitch(message):
    """Pitch from a launcher [FUSION] line, computed there from the rocket's relayed IMU values."""
    _, found, text = message.partition("Pitch:")
    return _finite(text) if found else None


def parse_gain_entry(kp_text, kd_text, limits=None):
    """Return (kp, kd) or raise ValueError, applying the limits both boards enforce."""
    limits = limits or load_model()["firmware_limits"]
    low, high = limits["gain_min"], limits["gain_max"]
    values = []
    for text in (kp_text, kd_text):
        value = _finite(text)
        if value is None:
            raise ValueError("PID values must be finite numbers")
        if value < low:
            raise ValueError("PID values must be non-negative")
        if value > high:
            raise ValueError(f"PID values must not exceed {high}")
        values.append(value)
    return tuple(values)


def minimal_diagnoses(conflicts, unit_order):
    """Smallest sets of units that explain every conflict (minimal hitting sets)."""
    conflicts = [set(conflict) for conflict in conflicts if conflict]
    if not conflicts:
        return []
    universe = [unit for unit in unit_order if any(unit in conflict for conflict in conflicts)]
    found = []
    for size in range(1, len(universe) + 1):
        for combo in combinations(universe, size):
            candidate = set(combo)
            if any(set(known) <= candidate for known in found):
                continue
            if all(candidate & conflict for conflict in conflicts):
                found.append(combo)
    return [list(item) for item in found]


def diagnose(states, model):
    """Turn channel states into unit status, diagnoses, and the next useful probe."""
    units = [unit["id"] for unit in model["units"]]
    channels = {channel["id"]: channel for channel in model["channels"]}
    seen = set()
    for channel_id, state in states.items():
        if state == PRESENT:
            seen.update(channels[channel_id]["requires"])
    conflicts, unexplained = [], []
    for channel_id, state in states.items():
        if state == ABSENT:
            remaining = set(channels[channel_id]["requires"]) - seen
            if remaining:
                conflicts.append(remaining)
            else:
                unexplained.append(channel_id)
    diagnoses = minimal_diagnoses(conflicts, units)
    suspects = {unit for diagnosis in diagnoses for unit in diagnosis}
    unit_status = {unit: SEEN if unit in seen else SUSPECT if unit in suspects else NOT_SEEN for unit in units}
    return {"unit_status": unit_status, "diagnoses": diagnoses, "unexplained": unexplained,
            "next_test": _next_test(states, diagnoses, seen, channels)}


def _next_test(states, diagnoses, seen, channels):
    if len(diagnoses) < 2:
        return None
    for channel_id, channel in channels.items():
        if channel["kind"] != "probe" or states.get(channel_id) != UNTESTED:
            continue
        tested = set(channel["requires"]) - seen
        cleared = [diagnosis for diagnosis in diagnoses if not set(diagnosis) & tested]
        blamed = [diagnosis for diagnosis in diagnoses if set(diagnosis) & tested]
        if cleared and blamed:
            return {"command": channel["command"], "channel": channel_id,
                    "if_reply": cleared, "if_silent": blamed}
    return None


def capability_status(capability, unit_status, diagnoses):
    required = capability["requires"]
    if diagnoses and any(all(unit in diagnosis for diagnosis in diagnoses) for unit in required):
        return LOST
    if any(unit_status[unit] == SUSPECT for unit in required):
        return AT_RISK
    if all(unit_status[unit] == SEEN for unit in required):
        return SUPPORTED
    return NOT_OBSERVED


def capabilities_after(failed, model):
    """Capabilities a given set of failed units leaves, from the dependency model alone."""
    failed = set(failed)
    return [capability["id"] for capability in model["capabilities"] if not failed & set(capability["requires"])]


def signature(failed, model, probe=False):
    """What the dashboard would observe with these units failed, assuming steady state."""
    failed = set(failed)
    states = {}
    channels = {channel["id"]: channel for channel in model["channels"]}
    for channel_id, channel in channels.items():
        state = ABSENT if failed & set(channel["requires"]) else PRESENT
        gate = channel.get("gated_by")
        if gate and failed & set(channels[gate]["requires"]):
            state = UNTESTED
        if channel["kind"] == "probe" and not probe:
            state = UNTESTED
        states[channel_id] = state
    return states


class GroundStatus:
    """Accumulates packets and answers "what do they support right now?"."""

    def __init__(self, model=None, clock=time.monotonic):
        self.model = model or load_model()
        self.clock = clock
        self._lock = threading.Lock()
        self._channels = {channel["id"]: channel for channel in self.model["channels"]}
        self._limits = self.model["firmware_limits"]
        self._states_order = {state: i for i, state in enumerate(self._limits["rocket_states"])}
        self._started_at = clock()
        self._any_packet_at = None
        self._last_seen = {}
        self._env = None  # (gps_state, altitude or None)
        self._env_resumed_at = None
        self._probe_sent_at = None
        self._probe_reply_at = None
        self._rocket_state = None
        self._rocket_state_at = None
        self._unknown_state = None
        self._output = None
        self._output_outside_flight = False
        self._sample = None  # (roll, rate, output, at)
        self._repeat = 0
        self._last_pair = None
        self._last_device_ms = None
        self._abort_active = False  # Cleared when the rocket is next seen IDLE.
        self._abort_latch = False  # Cleared when ENV resumes.
        self._events = {}  # advisory id -> (text, at)
        self._observed_gains = None
        self._observed_gains_at = None
        self._commanded = None
        self._preselect = None
        self._calibration_at = None
        self._calibration_seen = False
        self._skew = None
        self._pitch = None
        self._log_announced = None
        self._log_rows = 0
        self._log_last_ms = None
        self._log_mark = None  # (rocket ms, ground time) at the end of the last complete dump.
        self._active_since = {}
        self.timeline = []
        self.packets = 0

    # ---- inputs -------------------------------------------------------------------------

    def observe(self, message, at=None):
        """Read one packet exactly as the launcher sent it."""
        with self._lock:
            now = self.clock() if at is None else at
            message = str(message).strip()
            self.packets += 1
            self._any_packet_at = now
            if message.startswith("T,"):
                self._observe_sample(message, now)
            elif message.startswith("STATUS:"):
                self._observe_status(message, now)
            elif message.startswith("ENV,"):
                self._observe_env(message, now)
            elif message.startswith("[FUSION]"):
                self._last_seen["heading"] = now
                self._pitch = _fusion_pitch(message)
            elif message.startswith("ABORT:"):
                self._abort_active = True
                self._abort_latch = True
                self._events["C-LAUNCHER-ABORT"] = (f"LAUNCHER ABORT: {message.split(':', 1)[1].strip()}", now)
            elif message.startswith("CMD_REJECT:"):
                self._observe_rejection(message, now)
            elif message.startswith("LOG"):
                self._observe_log(message, now)

    def command_sent(self, command, at=None):
        """Note a command the dashboard already sent. This module sends nothing itself."""
        with self._lock:
            now = self.clock() if at is None else at
            command = str(command).strip()
            if command == "dumplog":
                self._probe_sent_at = now
                self._probe_reply_at = None
            elif command == "calibrate":
                self._calibration_at = now
                self._calibration_seen = False
            elif command.startswith("PID,"):
                parts = command.split(",")
                if len(parts) == 3 and _finite(parts[1]) is not None and _finite(parts[2]) is not None:
                    self._commanded = {"kp": float(parts[1]), "kd": float(parts[2]), "at": now, "rejected": False}
                    self._events.pop("C-GAINS-REJECTED", None)

    def preselect(self, kp_text, kd_text):
        """Note what is typed in the entry boxes; nothing is sent."""
        with self._lock:
            try:
                kp, kd = parse_gain_entry(kp_text, kd_text, self._limits)
                self._preselect = {"kp": kp, "kd": kd, "error": None}
            except ValueError as error:
                self._preselect = {"kp": None, "kd": None, "error": str(error)}

    def _observe_sample(self, message, now):
        parts = message.split(",")
        values = [_finite(part) for part in parts[1:5]] if len(parts) >= 5 else [None]
        if any(value is None for value in values):
            return
        device_ms, roll, rate, output = values
        if self._last_device_ms is not None and device_ms < self._last_device_ms:
            self._events["C-LAUNCHER-RESTART"] = ("LAUNCHER CLOCK WENT BACKWARDS: RESTART INFERRED", now)
        self._last_device_ms = device_ms
        self._last_seen["rocket_telemetry"] = now
        self._sample = (roll, rate, output, now)
        self._output = output
        pair = (parts[2].strip(), parts[3].strip())
        self._repeat = self._repeat + 1 if pair == self._last_pair else 0
        self._last_pair = pair

    def _observe_status(self, message, now):
        parts = message.split(":", 1)[1].strip().split(",")
        state = parts[0].strip()
        self._last_seen["rocket_telemetry"] = now
        if state not in self._states_order:
            self._unknown_state = state
            return
        self._unknown_state = None
        previous = self._rocket_state
        if previous is not None and self._states_order[state] < self._states_order[previous]:
            self._events["C-ROCKET-RESTART"] = (f"ROCKET WENT {previous} TO {state}: RESTART INFERRED", now)
        if state == "IDLE":
            self._abort_active = False
        if len(parts) >= 4:
            self._observe_skew(parts[3], previous, state, now)
        self._rocket_state, self._rocket_state_at = state, now
        # T comes first from the same DATA line, so this pairing is sample-accurate.
        self._output_outside_flight = bool(self._output) and state != "FLIGHT"
        if len(parts) >= 3:
            kp, kd = _finite(parts[1]), _finite(parts[2])
            if kp is not None and kd is not None:
                self._observed_gains = (kp, kd)
                self._observed_gains_at = now

    def _observe_skew(self, text, previous, state, now):
        """Firmware sets skew only while calibrating: at boot, on ARM, and on CALIBRATE."""
        skew = _finite(text)
        if skew is None:
            return
        last, self._skew = self._skew, skew
        if last is None or skew == last:
            return
        sent = self._calibration_at
        # One calibration moves skew once, so a second change inside the window has another cause.
        if sent is not None and now - sent <= CALIBRATION_WINDOW_S and not self._calibration_seen:
            self._calibration_seen = True
        elif previous == state == "IDLE":
            # Outside IDLE, ARM and the launcher's own pre-ignition CALIBRATE also move skew.
            self._events["C-ROCKET-RESTART"] = (f"ROCKET SKEW WENT {last:g} TO {skew:g} WITH NO CALIBRATION TO EXPLAIN IT: RESTART INFERRED", now)

    def _observe_env(self, message, now):
        parts = message.split(",")
        if len(parts) < 5:
            return
        try:
            gps_state = int(parts[4])
        except ValueError:
            return
        previous = self._last_seen.get("environment")
        if previous is None or now - previous > self._channels["environment"]["timeout_s"]:
            self._env_resumed_at = now
        self._last_seen["environment"] = now
        self._abort_latch = False
        self._env = (gps_state, _finite(parts[3]))

    def _observe_rejection(self, message, now):
        reason = message.split(":", 1)[1].strip()
        if reason == "pid_invalid":
            if self._commanded:
                self._commanded["rejected"] = True
            self._events["C-GAINS-REJECTED"] = ("GAINS REJECTED BY FIRMWARE", now)
        elif reason == "unknown_command":
            self._events["C-UNKNOWN-COMMAND"] = ("LAUNCHER DID NOT RECOGNIZE A COMMAND", now)
        else:
            self._events["A-COMMAND-REFUSED"] = (f"COMMAND REFUSED: {reason}", now)

    def _observe_log(self, message, now):
        if message.startswith("LOG_START"):
            parts = message.split(",")
            self._log_announced = int(parts[1]) if len(parts) > 1 and parts[1].strip().isdecimal() else None
            self._log_rows = 0
            self._log_last_ms = None
        elif message.startswith("LOG_END"):
            if self._log_announced is not None and self._log_rows != self._log_announced:
                self._events["A-LOG-PARTIAL"] = (f"LOG DUMP PARTIAL: {self._log_rows} OF {self._log_announced} ROWS", now)
            elif self._log_announced is not None:
                self._check_rocket_clock(now)
            self._log_announced = None
        elif message.startswith("LOG,"):
            self._log_rows += 1
            parts = message.split(",")
            self._log_last_ms = _finite(parts[1]) if len(parts) > 1 else None
        else:
            return
        self._probe_reply_at = now

    def _check_rocket_clock(self, now):
        """LOG rows carry the rocket clock. Across a restart it restarts, and ground time does not."""
        rocket_ms = self._log_last_ms
        if rocket_ms is None:
            return
        if self._log_mark is not None:
            behind = (now - self._log_mark[1]) - (rocket_ms - self._log_mark[0]) / 1000.0
            if behind > LOG_CLOCK_MARGIN_S:
                self._events["C-ROCKET-RESTART"] = (f"ROCKET CLOCK {behind:.0f} s BEHIND GROUND TIME SINCE THE LAST LOG DUMP: RESTART INFERRED", now)
        self._log_mark = (rocket_ms, now)

    # ---- derived state ------------------------------------------------------------------

    def _channel_states(self, now):
        states = {}
        for channel_id, channel in self._channels.items():
            if channel["kind"] == "stream":
                states[channel_id] = self._stream_state(channel_id, channel, now)
        # A launcher waiting in a loop stops the loop tail, not the relay; see the model.
        env_present = states["environment"] == PRESENT
        for channel_id, channel in self._channels.items():
            if channel.get("gated_by") and not env_present:
                states[channel_id] = UNTESTED
            elif channel["kind"] == "probe":
                states[channel_id] = self._probe_state(channel, now)
        if env_present:
            states["heading"] = self._heading_state(self._channels["heading"], now)
        if env_present and self._env is not None:
            gps_state, altitude = self._env
            states["gps_stream"] = PRESENT if gps_state >= 1 else ABSENT
            states["altitude"] = PRESENT if altitude is not None else ABSENT
        return states

    def _stream_state(self, channel_id, channel, now):
        last = self._last_seen.get(channel_id)
        if last is not None and now - last <= channel["timeout_s"]:
            return PRESENT
        if last is None and now - self._started_at <= channel["timeout_s"]:
            return PENDING
        return ABSENT

    def _heading_state(self, channel, now):
        """Silence only counts once ENV has kept flowing past the timeout without [FUSION].

        Both come from the launcher loop tail, and [FUSION] times out first, so a launcher
        entering a wait must not read as a compass fault.
        """
        last = self._last_seen.get("heading")
        if last is not None and now - last <= channel["timeout_s"]:
            return PRESENT
        reference = max(self._env_resumed_at, last if last is not None else self._env_resumed_at)
        return ABSENT if self._last_seen["environment"] - reference > channel["timeout_s"] else UNTESTED

    def _probe_state(self, channel, now):
        if self._probe_sent_at is None:
            return UNTESTED
        age = now - self._probe_sent_at
        if age > channel["hold_s"]:
            return UNTESTED
        if self._probe_reply_at is not None:
            return PRESENT
        return PENDING if age <= channel["timeout_s"] else ABSENT

    def _roll_reference(self, states):
        """What the pose implies for the accelerometer's roll correction. Geometry only, not a health check."""
        view = {"state": NOT_OBSERVED, "pitch_deg": None, "magnification": None}
        if self._rocket_state == "FLIGHT":
            return dict(view, state=GYRO_ONLY)
        # [FUSION] is computed from the last relayed rocket IMU values, so both streams must be live.
        if states["rocket_telemetry"] != PRESENT or states.get("heading") != PRESENT or self._pitch is None:
            return view
        cosine = math.cos(math.radians(abs(self._pitch)))
        return {"state": WEAK_GEOMETRY if abs(self._pitch) >= WEAK_REFERENCE_PITCH_DEG else GEOMETRY_OK,
                "pitch_deg": self._pitch, "magnification": 1.0 / cosine if cosine > 1e-6 else None}

    def _calibration(self, now, telemetry_present):
        """Firmware sends no reply to CALIBRATE; a change in skew is the only sign it ran."""
        view = {"state": "NOT SENT", "skew_deg": self._skew}
        sent = self._calibration_at
        if sent is None:
            return view
        if self._calibration_seen:
            state = "CHANGE SEEN"
        elif now - sent <= CALIBRATION_WINDOW_S:
            state = "SENT"
        else:
            state = "NO CHANGE SEEN" if telemetry_present else "UNCONFIRMED"
        return dict(view, state=state, age_s=now - sent)

    def _attitude(self, now, reference):
        sample = self._sample
        basis = "gyro only" if self._rocket_state == "FLIGHT" else "gyro, corrected from the accelerometer when it totals near 1 g"
        view = {"valid": False, "roll_deg": None, "rate_deg_s": None, "output_deg": None,
                "reason": "no telemetry received", "age_s": None, "basis": basis, "reference": reference,
                "not_observed": "pitch and yaw are not in the protocol",
                "limit_deg": self._limits["max_deflection_deg"],
                "drift": "Gyro drift NOT MEASURED (P-003)",
                "calibration_age_s": None if self._calibration_at is None else now - self._calibration_at}
        if sample is None:
            return view
        roll, rate, output, at = sample
        view["age_s"] = now - at
        if now - at > ATTITUDE_VALID_S:
            view["reason"] = f"last sample {now - at:.1f} s old"
            return view
        view.update(valid=True, roll_deg=roll, rate_deg_s=rate, output_deg=output, reason=None)
        return view

    def _gains(self, now, telemetry_present):
        observed, commanded = self._observed_gains, self._commanded
        view = {"observed": observed, "state": "NOT RECEIVED" if observed is None else "ACTIVE",
                "commanded": None if commanded is None else (commanded["kp"], commanded["kd"]),
                "preselect": None, "preselect_error": None}
        if commanded is not None:
            after = self._observed_gains_at is not None and self._observed_gains_at >= commanded["at"]
            matched = after and all(abs(a - b) <= GAIN_MATCH_TOLERANCE
                                    for a, b in zip(observed, (commanded["kp"], commanded["kd"])))
            if commanded["rejected"]:
                view["state"] = "REJECTED"
            elif matched:
                view["state"] = "CONFIRMED"
            elif now - commanded["at"] <= CONFIRM_WINDOW_S:
                view["state"] = "SENT"
            elif after and telemetry_present:
                view["state"] = "NO MATCH"
            else:
                view["state"] = "UNCONFIRMED"
        preselect = self._preselect
        if preselect is not None:
            if preselect["error"]:
                view["preselect_error"] = preselect["error"]
            else:
                pair = (preselect["kp"], preselect["kd"])
                reference = [observed]
                if commanded is not None and view["state"] in ("SENT", "UNCONFIRMED", "NO MATCH", "REJECTED"):
                    reference.append((commanded["kp"], commanded["kd"]))
                if not any(ref is not None and all(abs(a - b) <= GAIN_MATCH_TOLERANCE for a, b in zip(ref, pair))
                           for ref in reference):
                    view["preselect"] = pair
        return view

    def _launcher_inference(self, states):
        env, telemetry = states["environment"], states["rocket_telemetry"]
        if self._any_packet_at is None:
            return "NOT REPORTED; no packets"
        if env == ABSENT and telemetry == ABSENT:
            return "NOT REPORTED; no packets now"
        if env == ABSENT:
            if self._abort_latch:
                return "NOT REPORTED; abort latch inferred (ABORT seen, ENV paused)"
            return "NOT REPORTED; wait inferred (ENV paused while relaying)"
        if self._abort_active:
            return "NOT REPORTED; left abort latch inferred (ENV resumed)"
        if self._rocket_state in ("ARMED", "IGNITING", "FLIGHT"):
            return "NOT REPORTED; reached READY earlier, inferred from the rocket state"
        return "NOT REPORTED"

    def _rocket_view(self, states, now):
        state = self._rocket_state
        if state is None:
            return {"state": None, "age_s": None, "stale": False, "display": "NOT RECEIVED"}
        age = now - self._rocket_state_at
        stale = states["rocket_telemetry"] != PRESENT
        return {"state": state, "age_s": age, "stale": stale,
                "display": f"{state} (STALE {age:.1f} s)" if stale else state}

    def _conditions(self, states, analysis, rocket, gains, reference, calibration, now):
        active = []

        def add(advisory_id, text):
            active.append((advisory_id, text))

        state, stale = rocket["state"], rocket["stale"]
        is_active = state in ("ARMED", "IGNITING", "FLIGHT")
        if self._abort_active and is_active and not stale:
            add("W-ARMED-AFTER-ABORT", f"ROCKET STILL {state} AFTER LAUNCHER ABORT")
        if is_active and stale:
            add("W-ACTIVE-STATE-STALE", f"ROCKET LAST REPORTED {state}; NO TELEMETRY FOR {rocket['age_s']:.1f} s")
        if state in ("IGNITING", "FLIGHT") and not stale:
            add("W-IGNITION-ACTUATION", f"IGNITION ACTUATION COMMANDED ({state})")

        telemetry, env = states["rocket_telemetry"], states["environment"]
        if telemetry == ABSENT and env == ABSENT:
            add("C-NO-PACKETS", "NO PACKETS FROM THE LAUNCHER")
        elif telemetry == ABSENT:
            add("C-ROCKET-TELEMETRY-LOST", "NO ROCKET TELEMETRY; LAUNCHER STILL REPORTING")
        if gains["state"] == "NO MATCH":
            add("C-GAINS-NO-MATCH", "GAINS NO MATCH: TELEMETRY DIFFERS FROM THE VALUES SENT")
        if gains["state"] == "UNCONFIRMED":
            add("A-GAINS-UNCONFIRMED", "GAINS SENT, NOT CONFIRMED: NO TELEMETRY SINCE")
        if self._output_outside_flight and not stale:
            add("C-OUTPUT-OUTSIDE-FLIGHT", f"SERVO OUTPUT {self._output:g} WHILE {state}")
        if self._unknown_state:
            add("C-STATE-UNKNOWN", f"UNKNOWN ROCKET STATE: {self._unknown_state}")

        if "environment" in analysis["unexplained"]:
            add("A-LAUNCHER-HELD", "LAUNCHER WAITING: ENV PAUSED WHILE RELAYING")
        if "log_reply" in analysis["unexplained"]:
            add("A-PROBE-UNANSWERED", "LOG DUMP UNANSWERED WHILE TELEMETRY IS FLOWING")
        if states.get("gps_stream") == ABSENT:
            add("A-GPS-NO-NMEA", "GPS: NO NMEA")
        elif states.get("gps_stream") == PRESENT and self._env and self._env[0] == 1:
            add("A-GPS-NO-FIX", "GPS: NO FIX")
        if states.get("altitude") == ABSENT:
            add("A-BARO-MISSING", "BAROMETER NOT REPORTED")
        if states.get("heading") == ABSENT:
            add("A-COMPASS-SILENT", "NO COMPASS OUTPUT")
        if telemetry == PRESENT and self._repeat >= FROZEN_SAMPLES:
            add("A-IMU-FROZEN", f"IMU SUSPECT: ROLL AND RATE IDENTICAL FOR {self._repeat} SAMPLES")
        if telemetry == PRESENT and self._output is not None and abs(self._output) >= self._limits["max_deflection_deg"]:
            add("A-CANARD-LIMIT", f"SERVO AT LIMIT: {self._output:g} DEG")
        if reference["state"] == WEAK_GEOMETRY:
            add("A-ROLL-REFERENCE-WEAK", f"ROLL REFERENCE WEAK: PITCH {reference['pitch_deg']:+.1f} DEG")
        if calibration["state"] == "NO CHANGE SEEN" and calibration["age_s"] <= EVENT_HOLD_S:
            add("A-CALIBRATION-NO-CHANGE", "CALIBRATION SENT; SKEW UNCHANGED")
        for advisory_id, (text, at) in list(self._events.items()):
            if now - at <= EVENT_HOLD_S:
                add(advisory_id, text)
            else:
                del self._events[advisory_id]
        return active

    def _advisories(self, conditions, now):
        current = {}
        for advisory_id, text in conditions:
            level, detail = ADVISORIES[advisory_id]
            if advisory_id not in self._active_since:
                self._active_since[advisory_id] = now
                self.timeline.append({"id": advisory_id, "level": level, "text": text, "start": now, "end": None})
            current[advisory_id] = {"id": advisory_id, "level": level, "text": text, "detail": detail,
                                    "since": self._active_since[advisory_id]}
        for advisory_id in list(self._active_since):
            if advisory_id not in current:
                del self._active_since[advisory_id]
                for entry in reversed(self.timeline):
                    if entry["id"] == advisory_id and entry["end"] is None:
                        entry["end"] = now
                        break
        return sorted(current.values(), key=lambda item: (LEVEL_ORDER[item["level"]], item["since"], item["id"]))

    def snapshot(self, at=None):
        """Everything the board shows, computed from packets seen up to now."""
        with self._lock:
            now = self.clock() if at is None else at
            states = self._channel_states(now)
            analysis = diagnose(states, self.model)
            unit_status = analysis["unit_status"]
            capabilities = {capability["id"]: capability_status(capability, unit_status, analysis["diagnoses"])
                            for capability in self.model["capabilities"]}
            rocket = self._rocket_view(states, now)
            telemetry_present = states["rocket_telemetry"] == PRESENT
            gains = self._gains(now, telemetry_present)
            reference = self._roll_reference(states)
            calibration = self._calibration(now, telemetry_present)
            advisories = self._advisories(self._conditions(states, analysis, rocket, gains, reference, calibration, now), now)
            return {
                "packets": self.packets,
                "channels": states,
                "units": unit_status,
                "diagnoses": analysis["diagnoses"],
                "next_test": analysis["next_test"],
                "isolation": isolation_text(analysis["diagnoses"], analysis["next_test"], states),
                "capabilities": capabilities,
                "rocket": rocket,
                "launcher": self._launcher_inference(states),
                "attitude": self._attitude(now, reference),
                "gains": gains,
                "calibration": calibration,
                "advisories": advisories,
            }


def gains_line(gains):
    """One line for the entry panel: what is active, what is typed, what was sent."""
    def pair(values):
        return f"Kp {values[0]:.2f} / Kd {values[1]:.2f}"

    state = gains["state"]
    observed = "not received" if gains["observed"] is None else pair(gains["observed"])
    parts = [f"ACTIVE {observed}"]
    if gains["commanded"] is not None:
        parts.append(f"SENT {pair(gains['commanded'])} ({state})")
    if gains["preselect_error"]:
        parts.append(f"ENTRY INVALID: {gains['preselect_error']}")
    elif gains["preselect"] is not None:
        parts.append(f"PRESELECT {pair(gains['preselect'])} (not sent)")
    return " · ".join(parts)


def calibration_line(calibration):
    """One line for the panel. Skew is reported to 0.01 deg, so an unchanged value proves nothing."""
    skew = calibration["skew_deg"]
    reading = "not received" if skew is None else f"{skew:+.2f} deg"
    return f"CALIBRATION {calibration['state']} · SKEW {reading}"


def reference_text(reference):
    """The pose-based limit on roll, in words. It describes geometry and says nothing about sensor health."""
    state = reference["state"]
    if state == GYRO_ONLY:
        return "Roll reference: gyro only in FLIGHT."
    if reference["pitch_deg"] is None:
        return "Roll reference: not observed (needs live telemetry and [FUSION])."
    size = "very large" if reference["magnification"] is None else f"{reference['magnification']:.1f} x"
    return f"Roll reference: {state}, pitch {reference['pitch_deg']:+.1f} deg, axis error magnified {size}."


def next_test_text(next_test):
    if not next_test:
        return None

    def names(diagnoses):
        return " or ".join("+".join(diagnosis) for diagnosis in diagnoses)

    return (f"Press DUMP LOG. A reply leaves {names(next_test['if_reply'])}; "
            f"silence leaves {names(next_test['if_silent'])}.")


def isolation_text(diagnoses, next_test, states):
    """What the operator can do next to narrow the fault, if anything."""
    if not diagnoses:
        return None
    if len(diagnoses) == 1:
        return "Isolated as far as this model can go."
    if next_test:
        return next_test_text(next_test)
    if states.get("log_reply") == PENDING:
        return "Waiting for the log-dump reply."
    return "No dashboard test separates these; inspect the hardware."


def diagnosis_text(snapshot):
    if not snapshot["diagnoses"]:
        return "No fault explanation needed." if snapshot["packets"] else "No packets yet."
    return "Consistent with failure of: " + " or ".join("+".join(item) for item in snapshot["diagnoses"])


# ---- replay of a recorded session -------------------------------------------------------


class _ReplayClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now


def _timestamp(text):
    return datetime.fromisoformat(text.strip().replace("Z", "+00:00")).timestamp()


def session_events(session_dir):
    """Packets and sent commands from a session folder, merged in received order."""
    session_dir = Path(session_dir)
    events, origins = [], set()
    with (session_dir / "telemetry.csv").open(newline="", encoding="utf-8") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            if row.get("received_at_iso") and row.get("raw") is not None:
                events.append((_timestamp(row["received_at_iso"]), index, "packet", row["raw"]))
                if row.get("origin"):
                    origins.add(row["origin"])
    commands = session_dir / "commands.csv"
    if commands.exists():
        with commands.open(newline="", encoding="utf-8") as handle:
            for index, row in enumerate(csv.DictReader(handle)):
                if row.get("outcome") == "sent" and row.get("sent_utc"):
                    events.append((_timestamp(row["sent_utc"]), -1 - index, "command", row["command"]))
    events.sort(key=lambda event: (event[0], event[1]))
    return events, sorted(origins)


def replay(events, model=None, step_s=0.25, max_gap_ticks=240):
    """Run recorded events through the board, ticking through silent gaps."""
    if not events:
        raise ValueError("Session has no timestamped packets to replay.")
    clock = _ReplayClock(events[0][0])
    status = GroundStatus(model=model, clock=clock)
    start = previous = events[0][0]
    for at, _, kind, payload in events:
        ticks = 0
        tick = previous + step_s
        while tick < at and ticks < max_gap_ticks:
            clock.now = tick
            status.snapshot()
            tick += step_s
            ticks += 1
        clock.now = previous = max(at, previous)
        if kind == "packet":
            status.observe(payload)
        else:
            status.command_sent(payload)
        status.snapshot()
    final = status.snapshot()
    duration = previous - start
    # Trailing silence is not modeled as a fault: a capture ending is not a link failure.
    timeline = [dict(entry, start=entry["start"] - start, end=None if entry["end"] is None else entry["end"] - start)
                for entry in status.timeline]
    return {"duration_s": duration, "packets": status.packets, "timeline": timeline, "final": final}


def build_report(session_dir, model=None):
    events, origins = session_events(session_dir)
    report = replay(events, model=model)
    report.update(session=Path(session_dir).name, origins=origins,
                  stage="DERIVED VIEW of a raw session. Not evidence; it cannot accept a session or establish hardware behavior.")
    return report


def format_report(report):
    final = report["final"]
    lines = [f"Session: {report['session']}", report["stage"]]
    if report["origins"]:
        lines.append("In-band origin column: " + ", ".join(report["origins"]))
    lines += [f"Packets: {report['packets']} over {report['duration_s']:.1f} s", "", "Advisories in time order:"]
    if not report["timeline"]:
        lines.append("  none")
    for entry in report["timeline"]:
        end = "still active at end of capture" if entry["end"] is None else f"to {entry['end']:.1f} s"
        lines.append(f"  {entry['start']:8.1f} s  {entry['level']:<8} {entry['text']} ({end})")
    lines += ["", "At end of capture:", f"  Rocket: {final['rocket']['display']}", f"  Launcher: {final['launcher']}",
              f"  {diagnosis_text(final)}"]
    if final["isolation"]:
        lines.append(f"  {final['isolation']}")
    lines.append("  Units: " + ", ".join(f"{unit} {state}" for unit, state in final["units"].items()))
    return "\n".join(lines)


def synthetic_demo_events():
    """Invented packets for software demonstration. NOT a recording of any hardware."""
    events = []

    def add(at, kind, payload):
        events.append((at, len(events), kind, payload))

    for tenth in range(0, 340):
        at = tenth / 10
        if tenth % 10 == 0 and not 14 <= at < 20:
            add(at, "packet", f"ENV,0.000000,0.000000,{212.0 + (tenth % 30) / 10:.1f},1")
        if tenth % 5 == 0 and not 14 <= at < 20:
            add(at, "packet", "[FUSION] Hdg: 141.0 | Pitch: +0.4")
    for step in range(0, 480):
        at = step * 0.05
        roll = 6.0 * math.sin(at * 0.7)
        rate = 4.2 * math.cos(at * 0.7)
        kp, kd = ("0.50", "0.20") if at < 6.2 else ("1.00", "0.30")
        add(at, "packet", f"T,{1000 + step * 50},{roll:.2f},{rate:.2f},0")
        skew = "1.30" if at < 3.4 else "1.42" if at < 10 else "1.37"  # Calibrating moves it; so does ARM.
        add(at, "packet", f"STATUS:{'IDLE' if at < 10 else 'ARMED'},{kp},{kd},{skew}")
    add(3.0, "command", "calibrate")
    add(6.0, "command", "PID,1.0,0.3")
    add(14.0, "packet", "ABORT:Arming switch flipped OFF.")
    add(28.0, "command", "dumplog")  # Stays unanswered: this script's UART has "failed".
    events.sort(key=lambda event: (event[0], event[1]))
    return events


def main(argv=None):
    parser = argparse.ArgumentParser(description="Replay a raw dashboard session through the ground status logic. Sends nothing.")
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
