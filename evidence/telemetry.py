"""Audit recorded CSV quality without interpreting control effectiveness."""

from collections import Counter
from datetime import datetime
import math
import statistics

from .common import EvidenceError, csv_rows, digest, read_bytes


ORIGINS = {"unknown", "synthetic", "bench"}
REQUIRED = {"received_at_iso", "source", "message_type", "time_ms",
            "roll_deg", "rate_deg_s", "servo_output"}
MAX_DETAILS = 100
MAX_SERIES_POINTS = 1500
# Whose clock stamped time_ms. The launcher builds T packets with its own millis()
# when it relays a rocket DATA line; LOG rows carry the rocket's sample time.
CLOCK_DOMAINS = {"T": "launcher_relay_millis", "LOG": "rocket_millis"}
# Firmware send period (Firmware/Rocket/src/main.cpp, PRED-TLM-T-INTERVAL). T spacing
# reflects relay cadence, so it approximates this period without measuring it.
EXPECTED_INTERVAL_MS = {"T": 50, "LOG": 50}
EXPECTED_TOLERANCE = 0.2
RESPONSE_PREFIXES = ("CMD_REJECT:", "CMD_ACK:", "ABORT:")


def audit_csv(path, *, origin="unknown", gap_ms=500):
    return audit_bytes(read_bytes(path), origin=origin, gap_ms=gap_ms)


def _downsample(points):
    if len(points) <= MAX_SERIES_POINTS:
        return points
    stride = math.ceil(len(points) / MAX_SERIES_POINTS)
    kept = [point for index, point in enumerate(points) if index % stride == 0 or point.get("break")]
    return kept


def audit_bytes(data, *, origin="unknown", gap_ms=500, keep_series=False):
    if not isinstance(origin, str) or origin not in ORIGINS:
        raise EvidenceError(f"Unknown telemetry origin: {origin}")
    if isinstance(gap_ms, bool) or not isinstance(gap_ms, (int, float)):
        raise EvidenceError("gap_ms must be a finite positive number")
    if not math.isfinite(gap_ms) or gap_ms <= 0:
        raise EvidenceError("gap_ms must be a finite positive number")
    rows = csv_rows(data)
    fields = next(rows)
    if not REQUIRED.issubset(fields):
        raise EvidenceError(f"Missing telemetry columns: {sorted(REQUIRED - set(fields))}")
    has_raw = "raw" in fields
    has_gains = {"kp", "kd"}.issubset(fields)
    findings, details, streams, types = Counter(), [], {}, Counter()
    previous_received = {}
    responses = Counter()
    dumps, open_dump = [], None
    gains, last_gain = [], {}
    stray_log_rows = 0
    count = invalid = 0

    def finding(code, line, severity="warning"):
        findings[(severity, code)] += 1
        if len(details) < MAX_DETAILS:
            details.append({"line": line, "code": code, "severity": severity})

    def close_dump(line, terminated):
        nonlocal open_dump
        if open_dump is None:
            return
        open_dump["terminated"] = terminated
        announced, received = open_dump["announced"], open_dump["received"]
        if not terminated:
            state = "unterminated"
            finding("log_dump_unterminated", line)
        elif announced is None:
            state = "announcement_unreadable"
            finding("log_dump_count_unreadable", line)
        elif received < announced:
            state = "incomplete"
            finding("log_dump_incomplete", line)
        elif received > announced:
            state = "overfull"
            finding("log_dump_overfull", line)
        else:
            state = "complete"
        open_dump["state"] = state
        dumps.append(open_dump)
        open_dump = None

    for line, row in rows:
        count += 1
        kind, source = row["message_type"], row["source"]
        types[kind] += 1
        raw = row.get("raw", "") if has_raw else ""
        bad = False
        if not source or not kind:
            finding("missing_source_or_type", line, "error")
            bad = True
        received_text = row["received_at_iso"]
        try:
            received = datetime.fromisoformat(received_text)
            if received.utcoffset() is None:
                raise ValueError("Timestamp needs a timezone")
            if source in previous_received and received < previous_received[source]:
                finding("receive_clock_regression", line)
            previous_received[source] = received
        except (ValueError, OverflowError):
            finding("invalid_receive_timestamp", line, "error")
            bad = True
        if kind == "RAW" and raw:
            if raw.startswith("LOG_START"):
                close_dump(line, terminated=False)
                text = raw.partition(",")[2].strip()
                open_dump = {"index": len(dumps) + 1, "line": line,
                             "announced": int(text) if text.isascii() and text.isdecimal() else None,
                             "received": 0}
            elif raw.startswith("LOG_END"):
                if open_dump is None:
                    finding("log_end_without_start", line)
                close_dump(line, terminated=True)
            elif raw.startswith(RESPONSE_PREFIXES):
                responses[raw.strip()] += 1
        if kind == "STATUS" and has_gains and not bad:
            key = (row["kp"], row["kd"])
            if last_gain.get(source) != key:
                gains.append({"source": source, "kp": row["kp"], "kd": row["kd"],
                              "first_received": received_text, "last_received": received_text,
                              "status_rows": 0})
                last_gain[source] = key
            window = [g for g in gains if g["source"] == source][-1]
            window["last_received"] = received_text
            window["status_rows"] += 1
        if kind not in {"T", "LOG"}:
            if kind not in {"STATUS", "ENV", "RAW"}:
                finding("unknown_message_type", line)
            invalid += int(bad)
            continue
        if kind == "LOG" and has_raw:
            if open_dump is not None:
                open_dump["received"] += 1
            else:
                stray_log_rows += 1

        key = (source, kind)
        stream = streams.setdefault(key, {
            "source": source, "message_type": kind, "clock_domain": CLOCK_DOMAINS[kind],
            "valid_samples": 0, "invalid_samples": 0, "duplicate_samples": 0, "timestamp_conflicts": 0,
            "clock_regressions": 0, "segments": 0, "gaps_over_threshold": 0,
            "_previous": None, "_seen": {}, "_intervals": [], "_points": [],
        })
        try:
            text = row["time_ms"]
            if not text.isascii() or not text.isdecimal():
                raise ValueError("Device timestamp is not an unsigned integer")
            device = int(text)
            if not 0 <= device <= 0xFFFFFFFF:
                raise ValueError("Device timestamp is outside uint32 range")
            values = tuple(float(row[field]) for field in ("roll_deg", "rate_deg_s", "servo_output"))
            if not all(math.isfinite(value) for value in values):
                raise ValueError("Non-finite sample")
        except (ValueError, OverflowError):
            finding("invalid_numeric_sample", line, "error")
            bad = True
        if bad:
            invalid += 1
            stream["invalid_samples"] += 1
            continue
        stream["valid_samples"] += 1
        previous = stream["_previous"]
        brk = False
        if previous is None:
            stream["segments"] = 1
        elif device < previous:
            # Reset, reordering, and uint32 rollover are indistinguishable here.
            # Start a segment, preserve the finding, and never invent elapsed time.
            finding("device_clock_regression", line)
            stream["clock_regressions"] += 1
            stream["segments"] += 1
            stream["_seen"].clear()
            brk = True
        elif device > previous:
            interval = device - previous
            stream["_intervals"].append(interval)
            if interval > gap_ms:
                finding("device_time_gap", line)
                stream["gaps_over_threshold"] += 1
                brk = True
        if device in stream["_seen"]:
            if values == stream["_seen"][device]:
                finding("duplicate_sample", line)
                stream["duplicate_samples"] += 1
            else:
                finding("timestamp_conflict", line, "error")
                stream["timestamp_conflicts"] += 1
        stream["_seen"][device] = values
        stream["_previous"] = device
        if keep_series:
            stream["_points"].append({"t": device, "segment": stream["segments"], "break": brk,
                                      "roll_deg": values[0], "rate_deg_s": values[1], "servo_output": values[2]})

    close_dump(count + 1, terminated=False)
    if stray_log_rows:
        findings[("warning", "log_rows_outside_dump")] += stray_log_rows
    if not sum(stream["valid_samples"] for stream in streams.values()):
        finding("no_valid_telemetry", 1, "error")
    if origin == "unknown":
        finding("undeclared_origin", 1)
    output_streams, series = [], []
    for key in sorted(streams):
        stream = streams[key]
        intervals = stream["_intervals"]
        median = statistics.median(intervals) if intervals else None
        stream["median_positive_interval_ms"] = median
        stream["max_positive_interval_ms"] = max(intervals) if intervals else None
        expected = EXPECTED_INTERVAL_MS.get(stream["message_type"])
        stream["expected_interval_ms"] = expected
        if median is not None and expected and abs(median - expected) > EXPECTED_TOLERANCE * expected:
            findings[("warning", "interval_differs_from_expected")] += 1
        if keep_series:
            series.append({"source": stream["source"], "message_type": stream["message_type"],
                           "clock_domain": stream["clock_domain"], "invalid_samples": stream["invalid_samples"],
                           "points": _downsample(stream["_points"])})
        output_streams.append({k: value for k, value in stream.items() if not k.startswith("_")})
    result = {
        "schema_version": 2, "kind": "telemetry_quality", "origin": origin,
        "origin_is_operator_declared": True, "input_sha256": digest(data),
        "quality": "error" if any(severity == "error" for severity, _ in findings)
        else "warning" if findings else "clean",
        "row_count": count, "invalid_rows": invalid, "message_types": dict(sorted(types.items())),
        "gap_threshold_ms": gap_ms, "streams": output_streams,
        "log_dumps": dumps if has_raw else None,
        "gain_windows": gains if has_gains else None,
        "command_responses": [{"code": code, "count": total} for code, total in sorted(responses.items())],
        "findings": [{"severity": severity, "code": code, "count": total}
                     for (severity, code), total in sorted(findings.items())],
        "details": details, "details_truncated": sum(findings.values()) > len(details),
        "limitations": [
            "Origin is a declaration, not proof that hardware was present.",
            "This checks recorded data quality, not physical performance or readiness.",
            "T and LOG are separate streams; log recovery never increases live sample coverage.",
            "T time_ms is the launcher's clock at relay, not the rocket's sample time; LOG time_ms is the rocket's clock.",
            "The protocol has no sequence ID or boot identifier: gaps do not establish packet-loss counts.",
            "Clock regressions may be reset, reordering, or rollover; no cause is inferred.",
            "Invalid samples are counted and excluded, never replaced with zero.",
            "Positive intervals use successive valid rows, so invalid rows can span an interval.",
            "STATUS, ENV, and RAW payload values are preserved but not numerically audited.",
            "Firmware revision, hardware revision, and calibration state are not carried by the protocol; "
            "they are known only if a session declaration records them.",
        ],
    }
    if keep_series:
        result["series"] = series
    return result
