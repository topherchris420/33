"""Bench-session passports and conservative evidence ingestion.

RAW SESSION -> AUDITED -> REVIEW CANDIDATE -> HUMAN-ACCEPTED -> claim review.

Tooling may produce the first three. Only `accept`, run with a named reviewer,
produces the fourth, and nothing here turns clean telemetry into a claim result.
Raw capture files are never modified: the operator's declaration is a separate
file, and what was not recorded is reported as NOT RECORDED.
"""

from datetime import date as _date, datetime, timezone
from pathlib import Path
import shutil

from . import records as R
from .common import EvidenceError, canonical_json, csv_rows, digest, load_json, new_directory, read_bytes, safe_path
from .telemetry import audit_bytes

DECLARATION = "declaration.json"
METADATA = "session.json"
NOT_RECORDED = "NOT RECORDED"
DECLARATION_FIELDS = {
    "operator": "Person who ran the session",
    "origin": "bench, synthetic, or unknown",
    "purpose": "The single question this session addresses",
    "tests": "Measurement tags, e.g. timing, gyro_drift, arming, log_recovery",
    "hardware_revision": "Physical build identifier",
    "firmware_commit": "Commit flashed to both boards",
    "inert_configuration": "Propulsion/ignition state and disconnected actuators",
    "ignition_servo_disconnected": "true or false",
    "measurement_equipment": "Instruments used, with calibration dates",
    "calibration": "How and when the IMU was calibrated",
    "controller_gains_intended": "Gains the operator intended to test",
    "anomalies": "Anything unexpected during the run",
    "preregistration": "Pre-registration ID, if any",
}
LIMITATIONS = [
    "The declared origin is the operator's statement; the files cannot prove hardware was present.",
    "Clean data quality is necessary for evidence, not sufficient: it says nothing about physical performance.",
    "Firmware revision, hardware revision, and boot identity are not carried by the protocol.",
    "Live T timestamps are launcher relay times; only LOG rows carry the rocket clock.",
    "This passport does not enter the evidence record; a named human must accept the session first.",
]


def _session_files(directory):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise EvidenceError("Session must be a regular directory")
    files = {}
    for path in sorted(directory.iterdir()):
        if path.is_symlink():
            raise EvidenceError(f"Symlinks are not evidence files: {path.name}")
        if path.is_file():
            files[path.name] = read_bytes(path)
    if "telemetry.csv" not in files:
        raise EvidenceError("Session folder has no telemetry.csv")
    return files


def declare(directory, fields, *, now=None):
    """Write the operator's declaration next to the raw files. Never overwrites."""
    target = Path(directory) / DECLARATION
    _session_files(directory)
    if target.exists() or target.is_symlink():
        raise EvidenceError("A declaration already exists; declarations are not edited after the fact")
    unknown = set(fields) - set(DECLARATION_FIELDS)
    if unknown:
        raise EvidenceError(f"Unknown declaration fields: {sorted(unknown)}")
    origin = fields.get("origin") or "unknown"
    if origin not in ("bench", "synthetic", "unknown"):
        raise EvidenceError("origin must be bench, synthetic, or unknown")
    document = {"schema": "project33.declaration/1", "session_id": Path(directory).resolve().name,
                "declared_utc": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
                **{key: fields.get(key) for key in DECLARATION_FIELDS}, "origin": origin}
    target.write_bytes(canonical_json(document))
    return document


def _current_digest(root, path):
    try:
        return digest(read_bytes(safe_path(root, path)))
    except (EvidenceError, OSError):
        return None


def passport(directory, *, root=None, gap_ms=500, catalog_path="evidence/catalog.json"):
    """Assemble a session passport and its audit. Returns (passport, audit, files)."""
    files = _session_files(directory)
    declaration = load_json(files[DECLARATION]) if DECLARATION in files else None
    metadata = load_json(files[METADATA]) if METADATA in files else None
    origin = (declaration or {}).get("origin") or "unknown"
    audit = audit_bytes(files["telemetry.csv"], origin=origin, gap_ms=gap_ms, keep_series=True)
    warnings = []

    def warn(code, text):
        warnings.append({"code": code, "text": text})

    def declared(key):
        value = (declaration or {}).get(key)
        return NOT_RECORDED if value in (None, "", []) else value

    if declaration is None:
        warn("no_declaration", "No operator declaration: purpose, origin, hardware, and firmware are unknown.")
    if origin != "bench":
        warn("origin_not_bench", f"Declared origin is '{origin}'; only a bench declaration can become physical evidence.")
    if metadata is None:
        warn("session_metadata_missing", "No session.json: capture times and software revisions were not recorded.")
    elif not metadata.get("closed_cleanly"):
        warn("capture_not_closed", "The dashboard did not record a clean close: the capture may be partial.")
    versions = {"firmware_commit": declared("firmware_commit"), "hardware_revision": declared("hardware_revision")}
    if root is not None and metadata:
        for key, path in (("dashboard", "Firmware/dashboard.py"), ("protocol", "protocol/project33_protocol.json")):
            recorded = (metadata.get(key) or {}).get("sha256")
            current = _current_digest(root, path)
            versions[f"{key}_sha256_recorded"] = recorded or NOT_RECORDED
            versions[f"{key}_matches_current_checkout"] = None if not recorded or not current else recorded == current
            if recorded and current and recorded != current:
                warn(f"{key}_revision_mismatch", f"Captured with a different {path} than this checkout.")
    if versions["firmware_commit"] == NOT_RECORDED:
        warn("firmware_revision_not_recorded", "Firmware revision was not declared and is not reported by the device.")
    commands = []
    if "commands.csv" in files:
        rows = csv_rows(files["commands.csv"])
        next(rows)
        commands = [row for _, row in rows]
    calibrations = [row for row in commands if row.get("command") == "calibrate"]
    calibration = declared("calibration")
    if calibration == NOT_RECORDED and not calibrations:
        warn("calibration_not_recorded", "No calibration was declared or sent from the dashboard during this capture.")
    if audit["quality"] == "error":
        warn("audit_errors", "The data-quality audit found errors; see the findings.")
    tags = set((declaration or {}).get("tests") or [])
    affected = []
    if root is not None:
        try:
            records = R.load(root, catalog_path)
            affected = sorted(c["id"] for c in records.claims.values() if tags & set(c["measurement_tags"]))
        except (EvidenceError, OSError):
            affected = []
    ready = declaration is not None and origin == "bench" and audit["quality"] != "error" and \
        all(declared(key) != NOT_RECORDED for key in ("operator", "purpose", "inert_configuration"))
    document = {
        "schema": "project33.session_passport/1",
        "session_id": Path(directory).resolve().name,
        "stage": "review_candidate" if ready else "audited",
        "stage_meaning": ("Declaration and audit present; awaiting a named human reviewer." if ready else
                          "Audited only. Complete the declaration (operator, bench origin, purpose, inert configuration) "
                          "and resolve audit errors before it can be a review candidate."),
        "what_was_tested": {"purpose": declared("purpose"), "tests": sorted(tags) or NOT_RECORDED,
                            "preregistration": declared("preregistration")},
        "versions": versions,
        "configuration": {
            "gains_observed_in_status_packets": audit.get("gain_windows") or NOT_RECORDED,
            "gains_intended": declared("controller_gains_intended"),
            "calibration_declared": calibration,
            "calibrate_commands_sent": [row.get("sent_utc") for row in calibrations],
            "inert_configuration": declared("inert_configuration"),
            "ignition_servo_disconnected": declared("ignition_servo_disconnected"),
            "measurement_equipment": declared("measurement_equipment"),
        },
        "capture": {key: (metadata or {}).get(key, NOT_RECORDED) for key in
                    ("capture_started_utc", "capture_ended_utc", "closed_cleanly", "packets_logged")},
        "operator": declared("operator"), "origin_declared": origin, "anomalies": declared("anomalies"),
        "raw_files": [{"path": name, "bytes": len(data), "sha256": digest(data)} for name, data in files.items()],
        "data_quality": {"quality": audit["quality"], "findings": audit["findings"]},
        "commands_sent": len(commands) if "commands.csv" in files else NOT_RECORDED,
        "potentially_affected_claims": affected,
        "warnings": warnings,
        "cannot_establish": LIMITATIONS,
        "next_step": "A named human reviews this packet. If accepted, run python -m evidence session register, "
                     "then python -m evidence session accept --reviewer NAME.",
    }
    return document, audit, files


def build_passport(directory, output, *, root=None, gap_ms=500):
    from .bundle import _instructions, _seal, _write
    from .report import render_session

    document, audit, files = passport(directory, root=root, gap_ms=gap_ms)
    html = render_session(document, audit)
    audit.pop("series")
    with new_directory(output) as stage:
        for name, data in files.items():
            _write(stage, "session/" + name, data)
        _write(stage, "audit.json", canonical_json(audit))
        _write(stage, "passport.json", canonical_json(document))
        _write(stage, "index.html", html.encode())
        _write(stage, "README.txt", _instructions().encode())
        _seal(stage, "session_passport", {"session_id": document["session_id"]})
    return document


def register(bundle, root, *, catalog_path="evidence/catalog.json"):
    """Copy a verified passport's raw files into the repository and list the session as a review candidate."""
    from .bundle import verify_bundle

    checked = verify_bundle(bundle)
    if checked["kind"] != "session_passport":
        raise EvidenceError("register needs a session passport bundle")
    document = load_json(read_bytes(Path(bundle) / "passport.json"))
    records = R.load(root, catalog_path)
    if "sessions" not in records.declared:
        raise EvidenceError("This catalog does not keep a sessions registry")
    session_id = document["session_id"]
    R.identifier(session_id, "session")
    if session_id in records.sessions:
        raise EvidenceError(f"Session {session_id} is already registered")
    destination = safe_path(records.root, f"evidence/sessions/{session_id}")
    if destination.exists():
        raise EvidenceError(f"{destination} already exists")
    destination.mkdir(parents=True)
    raw_files = []
    for item in document["raw_files"]:
        source = Path(bundle) / "session" / item["path"]
        shutil.copyfile(source, destination / item["path"])
        raw_files.append({"path": f"evidence/sessions/{session_id}/{item['path']}", "sha256": item["sha256"]})
    stage = document["stage"]
    entry = {"id": session_id, "stage": stage, "origin": document["origin_declared"], "raw_files": raw_files,
             "declaration": document["origin_declared"] != "unknown" and document["operator"] != NOT_RECORDED,
             "audit_manifest_sha256": checked["manifest_sha256"],
             "tags": sorted(document["what_was_tested"]["tests"]) if isinstance(document["what_was_tested"]["tests"], list) else []}
    _write_sessions(records, entry)
    return entry


def accept(root, session_id, reviewer, *, catalog_path="evidence/catalog.json", today=None, reject_reason=None):
    """A named human accepts (or rejects) a registered review candidate."""
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise EvidenceError("Acceptance needs the reviewer's name")
    records = R.load(root, catalog_path)
    entry = records.sessions.get(session_id)
    if entry is None:
        raise EvidenceError(f"Unknown session {session_id}")
    if entry["stage"] != "review_candidate":
        raise EvidenceError(f"Only a review candidate can be accepted or rejected (stage is {entry['stage']})")
    updated = dict(entry)
    if reject_reason:
        updated.update(stage="rejected", rejection_reason=reject_reason.strip(),
                       notes=f"Rejected by {reviewer.strip()} on {today or _date.today().isoformat()}")
    else:
        updated.update(stage="human_accepted", accepted_by=reviewer.strip(),
                       accepted_on=today or _date.today().isoformat())
    _write_sessions(records, updated, replace=True)
    return updated


def _write_sessions(records, entry, replace=False):
    path = records.declared["sessions"]
    document = records.docs["sessions"]
    sessions = [item for item in document["sessions"] if not (replace and item["id"] == entry["id"])]
    sessions.append(entry)
    document["sessions"] = sorted(sessions, key=lambda item: item["id"])
    safe_path(records.root, path).write_bytes(canonical_json(document))
    R.load(records.root, records.catalog_path)  # the written registry must validate
