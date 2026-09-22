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


def audit_csv(path, *, origin="unknown", gap_ms=500):
    return audit_bytes(read_bytes(path), origin=origin, gap_ms=gap_ms)


def audit_bytes(data, *, origin="unknown", gap_ms=500):
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
    findings, details, streams, types = Counter(), [], {}, Counter()
    previous_received = {}
    count = invalid = 0

    def finding(code, line, severity="warning"):
        findings[(severity, code)] += 1
        if len(details) < MAX_DETAILS:
            details.append({"line": line, "code": code, "severity": severity})

    for line, row in rows:
        count += 1
        kind, source = row["message_type"], row["source"]
        types[kind] += 1
        bad = False
        if not source or not kind:
            finding("missing_source_or_type", line, "error")
            bad = True
        try:
            received = datetime.fromisoformat(row["received_at_iso"])
            if received.utcoffset() is None:
                raise ValueError("Timestamp needs a timezone")
            if source in previous_received and received < previous_received[source]:
                finding("receive_clock_regression", line)
            previous_received[source] = received
        except (ValueError, OverflowError):
            finding("invalid_receive_timestamp", line, "error")
            bad = True
        if kind not in {"T", "LOG"}:
            if kind not in {"STATUS", "ENV", "RAW"}:
                finding("unknown_message_type", line)
            invalid += int(bad)
            continue

        key = (source, kind)
        stream = streams.setdefault(key, {
            "source": source, "message_type": kind, "valid_samples": 0,
            "invalid_samples": 0, "duplicate_samples": 0, "timestamp_conflicts": 0,
            "clock_regressions": 0, "segments": 0, "gaps_over_threshold": 0,
            "_previous": None, "_seen": {}, "_intervals": [],
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
        if previous is None:
            stream["segments"] = 1
        elif device < previous:
            # Reset, reordering, and uint32 rollover are indistinguishable here.
            # Start a segment, preserve the finding, and never invent elapsed time.
            finding("device_clock_regression", line)
            stream["clock_regressions"] += 1
            stream["segments"] += 1
            stream["_seen"].clear()
        elif device > previous:
            interval = device - previous
            stream["_intervals"].append(interval)
            if interval > gap_ms:
                finding("device_time_gap", line)
                stream["gaps_over_threshold"] += 1
        if device in stream["_seen"]:
            if values == stream["_seen"][device]:
                finding("duplicate_sample", line)
                stream["duplicate_samples"] += 1
            else:
                finding("timestamp_conflict", line, "error")
                stream["timestamp_conflicts"] += 1
        stream["_seen"][device] = values
        stream["_previous"] = device

    if not sum(stream["valid_samples"] for stream in streams.values()):
        finding("no_valid_telemetry", 1, "error")
    if origin == "unknown":
        finding("undeclared_origin", 1)
    output_streams = []
    for key in sorted(streams):
        stream = streams[key]
        intervals = stream["_intervals"]
        stream["median_positive_interval_ms"] = statistics.median(intervals) if intervals else None
        stream["max_positive_interval_ms"] = max(intervals) if intervals else None
        output_streams.append({key: value for key, value in stream.items() if not key.startswith("_")})
    return {
        "schema_version": 1, "kind": "telemetry_quality", "origin": origin,
        "origin_is_operator_declared": True, "input_sha256": digest(data),
        "quality": "error" if any(severity == "error" for severity, _ in findings)
        else "warning" if findings else "clean",
        "row_count": count, "invalid_rows": invalid, "message_types": dict(sorted(types.items())),
        "gap_threshold_ms": gap_ms, "streams": output_streams,
        "findings": [{"severity": severity, "code": code, "count": total}
                     for (severity, code), total in sorted(findings.items())],
        "details": details, "details_truncated": sum(findings.values()) > len(details),
        "limitations": [
            "Origin is a declaration, not proof that hardware was present.",
            "This checks recorded data quality, not physical performance or readiness.",
            "T and LOG are separate streams; log recovery never increases live sample coverage.",
            "The protocol has no sequence ID: gaps do not establish packet-loss counts.",
            "Clock regressions may be reset, reordering, or rollover; no cause is inferred.",
            "Invalid samples are counted and excluded, never replaced with zero.",
            "Positive intervals use successive valid rows, so invalid rows can span an interval.",
            "STATUS, ENV, and RAW payload values are preserved but not numerically audited.",
        ],
    }
