"""Offline configuration binding and measurement metadata review.

No command transport, numerical performance verdict, evidence registration or
human acceptance lives here. A complete record is a review candidate only.
"""

from datetime import date, datetime, timezone
import html
import math
from pathlib import Path

from . import records as R
from .common import EvidenceError, canonical_json, csv_rows, digest, load_json, new_directory, read_bytes, safe_path

UNITS = {
    "elapsed_time": "s", "angle": "deg", "angular_rate": "deg/s",
    "length": "m", "mass": "kg", "density": "kg/m^3", "torque": "N*m",
    "torsional_rate": "N*m/rad", "elastic_modulus": "Pa", "bending_rigidity": "N*m^2",
}
SOURCES = {
    "command_request": "command",
    "electrical_transition": "independent_instrument",
    "mechanical_motion": "independent_instrument",
    "static_property": "independent_instrument",
    "telemetry_estimate": "telemetry_estimate",
}
PROFILES = {
    "P-001": ("output_delay", "elapsed_time", "electrical_transition"),
    "P-002": ("spring_rate", "torsional_rate", "static_property"),
    "P-003": ("stationary_roll_estimate", "angle", "telemetry_estimate"),
}
LIMITATIONS = [
    "Source hashes identify bytes; they do not resolve contradictions between designs.",
    "Specimen, installed firmware, origin and instrument metadata are declarations, not authenticated observations.",
    "Metadata completeness does not establish calibration validity, scientific validity or hardware performance.",
    "No value is judged against a performance limit; no session or measurement is registered or accepted.",
    "This workflow does not authorize hardware operation, release, flight or field use.",
]


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _timestamp(value, where):
    try:
        result = datetime.fromisoformat(value)
        if result.tzinfo is None or result.utcoffset() is None:
            raise ValueError("timezone missing")
        return result.astimezone(timezone.utc)
    except (TypeError, ValueError) as exc:
        raise EvidenceError(f"{where}: expected an ISO timestamp with timezone") from exc


def _sha(value, where):
    if not isinstance(value, str) or not R.HEX.fullmatch(value):
        raise EvidenceError(f"{where}: expected a SHA-256 digest")


def _items(value, where):
    if not isinstance(value, list) or not value or len(value) > 1000:
        raise EvidenceError(f"{where}: expected 1-1000 entries")
    ids = []
    for item in value:
        if not isinstance(item, dict):
            raise EvidenceError(f"{where}: entries must be objects")
        R.identifier(item.get("id"), where)
        ids.append(item["id"])
    if len(set(ids)) != len(ids):
        raise EvidenceError(f"{where}: duplicate identities")


def source_snapshot(root, records):
    """Catalog, evidence implementation and firmware/capture inputs; no secrets."""
    root = Path(root)
    paths = {path for path, _ in records.raw.values()}
    paths.update(a["path"] for a in records.artifacts.values() if a.get("status", "current") == "current")
    for pattern in ("evidence/*.py", "Firmware/*.py", "Firmware/requirements*.txt",
                    "Firmware/*/platformio.ini", "Firmware/*/src/**/*", "Firmware/shared/**/*"):
        paths.update(p.relative_to(root).as_posix() for p in root.glob(pattern)
                     if p.is_file() and p.name != "wifi_config.h")
    return [{"path": path, "sha256": digest(read_bytes(safe_path(root, path)))} for path in sorted(paths)]


def create_plan(root, output, *, catalog_path="evidence/catalog.json"):
    """Create an editable proposal with unknown identities, never an as-built record."""
    records = R.load(root, catalog_path)
    observables = []
    for prereg_id, (name, quantity, phenomenon) in PROFILES.items():
        if prereg_id not in records.preregistrations:
            continue
        prereg = records.preregistrations[prereg_id]
        exploratory = prereg_id == "P-003"
        observables.append({
            "id": name, "preregistration": prereg_id,
            "preregistration_sha256": R.preregistration_fingerprint(prereg),
            "quantity": quantity, "unit": UNITS[quantity], "phenomenon": phenomenon,
            "source_kind": SOURCES[phenomenon], "conditions": None, "method": None,
            "interpretation": {"mode": "characterize" if exploratory else "compare",
                               "rule": "Describe the estimate only; no physical-angle or pass/fail claim." if exploratory else None,
                               "criterion_source": None},
        })
    if not observables:
        raise EvidenceError("No supported proposed experiments exist in this catalog")
    plan = {"schema": "project33.bench_plan/1", "created_utc": _now(),
            "scope": "stationary_inert_demonstrator", "id": "BENCH-PROPOSAL",
            "purpose": "Prepare traceable observations of the inert educational testbed",
            "hardware_revision": None, "specimen": {"id": None, "description": None},
            "installed_firmware": [{"id": name, "sha256": None} for name in ("rocket", "launcher")],
            "source_snapshot": source_snapshot(root, records), "observables": observables}
    with new_directory(output) as stage:
        (stage / "plan.json").write_bytes(canonical_json(plan))
        (stage / "README.txt").write_text(
            "PROPOSED CONFIGURATION: identities and measurement details are unknown.\n"
            "Complete plan.json before creating an observation template. Preserve this exact\n"
            "plan with the capture; editing it later invalidates the capture binding.\n"
            "No test is authorized and no physical data has been generated.\n", encoding="utf-8")
    return plan


def _load_plan(path):
    raw = read_bytes(path)
    plan = load_json(raw)
    R.keys(plan, {"schema", "created_utc", "scope", "id", "purpose", "hardware_revision",
                  "specimen", "installed_firmware", "source_snapshot", "observables"}, where="bench plan")
    if plan["schema"] != "project33.bench_plan/1" or plan["scope"] != "stationary_inert_demonstrator":
        raise EvidenceError("Unsupported bench plan schema or scope")
    R.identifier(plan["id"], "plan.id")
    R.text(plan["purpose"], "plan.purpose")
    _timestamp(plan["created_utc"], "plan.created_utc")
    R.keys(plan["specimen"], {"id", "description"}, where="specimen")
    _items(plan["installed_firmware"], "installed_firmware")
    for item in plan["installed_firmware"]:
        R.keys(item, {"id", "sha256"}, where="installed_firmware")
    _items(plan["observables"], "observables")
    for item in plan["observables"]:
        R.keys(item, {"id", "preregistration", "preregistration_sha256", "quantity", "unit", "phenomenon",
                      "source_kind", "conditions", "method", "interpretation"}, where="observable")
        if not isinstance(item["quantity"], str) or item["quantity"] not in UNITS or item["unit"] != UNITS[item["quantity"]]:
            raise EvidenceError("Observable quantity and canonical unit do not agree")
        if not isinstance(item["phenomenon"], str) or SOURCES.get(item["phenomenon"]) != item["source_kind"]:
            raise EvidenceError("Command, estimate and independent observation sources are not interchangeable")
        R.identifier(item["preregistration"], "observable.preregistration")
        _sha(item["preregistration_sha256"], "observable.preregistration_sha256")
        profile = PROFILES.get(item["preregistration"])
        if profile and (item["quantity"], item["phenomenon"]) != profile[1:]:
            raise EvidenceError("Observable does not describe its referenced pre-registration")
        R.keys(item["interpretation"], {"mode", "rule", "criterion_source"}, where="interpretation")
        if item["interpretation"]["mode"] not in ("compare", "characterize"):
            raise EvidenceError("Interpretation must compare with a sourced criterion or characterize only")
    return plan, raw


def create_observation_template(plan_path, output):
    plan, raw = _load_plan(plan_path)
    document = {
        "schema": "project33.bench_observations/1", "origin": "unknown", "plan_sha256": digest(raw),
        "operator": None, "captured_utc": None, "hardware_revision": None, "specimen_id": None,
        "installed_firmware": [{"id": item["id"], "sha256": None} for item in plan["installed_firmware"]],
        "observations": [{"id": item["id"], "quantity": item["quantity"], "unit": item["unit"],
                          "phenomenon": item["phenomenon"], "source_kind": item["source_kind"],
                          "value": None, "uncertainty": None, "timebase": None,
                          "raw_file": None, "instrument": None} for item in plan["observables"]],
    }
    with new_directory(output) as stage:
        (stage / "observations.json").write_bytes(canonical_json(document))
        (stage / "README.txt").write_text(
            "EMPTY OBSERVATION TEMPLATE: no data was captured or invented.\n"
            "Keep raw instrument files here unchanged. Add identities, raw-file digests,\n"
            "units, uncertainty and calibration provenance from the actual session.\n"
            "Do not use command logs as evidence that a physical action occurred.\n", encoding="utf-8")
    return document


def assess_plan(root, plan_path, observation_path=None, *, catalog_path="evidence/catalog.json"):
    records = R.load(root, catalog_path)
    plan, raw = _load_plan(plan_path)
    files = {"inputs/plan.json": raw}
    findings = []

    def finding(code, where, message):
        findings.append({"code": code, "where": where, "message": message})

    def required(value, where):
        if value is None or value == "":
            finding("not_recorded", where, "Required metadata is not recorded")
        else:
            R.text(value, where)

    if _timestamp(plan["created_utc"], "plan.created_utc") > datetime.now(timezone.utc):
        finding("future_timestamp", "plan.created_utc", "Plan creation time is in the future")
    for key in ("hardware_revision",):
        required(plan[key], key)
    for key in ("id", "description"):
        required(plan["specimen"][key], f"specimen.{key}")
    expected_firmware = {}
    for item in plan["installed_firmware"]:
        if item["sha256"] is None:
            finding("not_recorded", f"firmware.{item['id']}", "Installed binary digest is not recorded")
        else:
            _sha(item["sha256"], "installed_firmware.sha256")
        expected_firmware[item["id"]] = item["sha256"]
    snapshot = plan["source_snapshot"]
    if not isinstance(snapshot, list) or not snapshot:
        raise EvidenceError("Source snapshot must be nonempty")
    expected = {}
    for item in snapshot:
        R.keys(item, {"path", "sha256"}, where="source_snapshot")
        safe_path(root, item["path"])
        _sha(item["sha256"], "source_snapshot.sha256")
        if item["path"] in expected:
            raise EvidenceError("Duplicate source path")
        expected[item["path"]] = item["sha256"]
    current = {item["path"]: item["sha256"] for item in source_snapshot(root, records)}
    changed = sorted(p for p in expected.keys() | current.keys() if expected.get(p) != current.get(p))
    for path in changed:
        finding("configuration_drift", path, "Missing, added or changed source; the plan describes a different configuration")
    for item in plan["observables"]:
        name = item["id"]
        for key in ("conditions", "method"):
            required(item[key], f"{name}.{key}")
        rule = item["interpretation"]
        required(rule["rule"], f"{name}.interpretation.rule")
        if rule["mode"] == "compare":
            required(rule["criterion_source"], f"{name}.interpretation.criterion_source")
        prereg = records.preregistrations.get(item["preregistration"])
        if prereg is None:
            finding("preregistration_missing", name, "Referenced pre-registration does not exist")
        else:
            if prereg["status"] != "registered":
                finding("preregistration_not_registered", name, "A named human has not registered this experiment")
            if R.preregistration_fingerprint(prereg) != item["preregistration_sha256"]:
                finding("preregistration_changed", name, "Interpretation no longer matches the referenced pre-registration")

    observation_summary = []
    origin = "not_supplied"
    if observation_path is not None:
        observation_path = Path(observation_path)
        capture_raw = read_bytes(observation_path)
        capture = load_json(capture_raw)
        files["inputs/observations.json"] = capture_raw
        R.keys(capture, {"schema", "origin", "plan_sha256", "operator", "captured_utc", "hardware_revision",
                         "specimen_id", "installed_firmware", "observations"}, where="observations")
        if capture["schema"] != "project33.bench_observations/1" or capture["origin"] not in ("bench", "unknown", "synthetic"):
            raise EvidenceError("Unsupported observation schema or origin")
        origin = capture["origin"]
        _sha(capture["plan_sha256"], "capture.plan_sha256")
        if capture["origin"] != "bench":
            finding("origin_not_bench", "capture", "Unknown or synthetic data cannot become a physical review candidate")
        if capture["plan_sha256"] != digest(raw):
            finding("plan_binding_mismatch", "capture", "Captured observations refer to a different plan")
        required(capture["operator"], "capture.operator")
        captured = _timestamp(capture["captured_utc"], "capture.captured_utc") if capture["captured_utc"] else None
        if captured is None:
            finding("not_recorded", "capture.captured_utc", "Capture timestamp is not recorded")
        elif captured < _timestamp(plan["created_utc"], "plan.created_utc"):
            finding("plan_created_after_capture", "capture", "A plan cannot be registered retroactively for this capture")
        if captured and captured > datetime.now(timezone.utc):
            finding("future_timestamp", "capture.captured_utc", "Capture time is in the future")
        if captured:
            for observable in plan["observables"]:
                prereg = records.preregistrations.get(observable["preregistration"])
                if prereg and prereg["status"] == "registered":
                    try:
                        registered = date.fromisoformat(prereg["registered_on"])
                    except (TypeError, ValueError, KeyError) as exc:
                        raise EvidenceError("Registered experiment needs a real registration date") from exc
                    if registered > captured.date():
                        finding("registration_after_capture", observable["id"], "Experiment was registered after the capture")
        for key, value in (("hardware_revision", plan["hardware_revision"]), ("specimen_id", plan["specimen"]["id"])):
            if not capture[key] or capture[key] != value:
                finding("specimen_mismatch", f"capture.{key}", "Capture and planned specimen identities do not agree")
        _items(capture["installed_firmware"], "capture.installed_firmware")
        for item in capture["installed_firmware"]:
            R.keys(item, {"id", "sha256"}, where="capture.installed_firmware")
            if item["sha256"] is not None:
                _sha(item["sha256"], "capture.installed_firmware.sha256")
        actual_firmware = {item["id"]: item["sha256"] for item in capture["installed_firmware"]}
        if actual_firmware != expected_firmware or any(v is None for v in actual_firmware.values()):
            finding("firmware_mismatch", "capture", "Recorded installed binaries do not match the planned binaries")

        def attachment(ref, where):
            if ref is None:
                finding("not_recorded", where, "Raw supporting file and digest are not recorded")
                return None
            R.keys(ref, {"path", "sha256"}, where=where)
            _sha(ref["sha256"], where)
            path = safe_path(observation_path.parent, ref["path"])
            try:
                data = read_bytes(path)
            except (EvidenceError, OSError) as exc:
                finding("attachment_missing", where, str(exc))
                return None
            if not data or digest(data) != ref["sha256"]:
                finding("attachment_mismatch", where, "Raw file is empty or its digest does not match")
            files["inputs/capture/" + ref["path"]] = data
            return data

        _items(capture["observations"], "capture.observations")
        planned = {item["id"]: item for item in plan["observables"]}
        if set(planned) != {item["id"] for item in capture["observations"]}:
            finding("observation_coverage", "capture", "Exactly one observation record per planned observable is required")
        for item in capture["observations"]:
            R.keys(item, {"id", "quantity", "unit", "phenomenon", "source_kind", "value", "uncertainty",
                          "timebase", "raw_file", "instrument"}, where="observation")
            name = item["id"]
            specification = planned.get(name)
            if specification is None:
                continue
            for key in ("quantity", "unit", "phenomenon", "source_kind"):
                if item[key] != specification[key]:
                    finding("observation_type_mismatch", f"{name}.{key}", "Observation and planned quantity/source are different")
            for key in ("value", "uncertainty"):
                value = item[key]
                if value is None:
                    finding("not_recorded", f"{name}.{key}", "No measured value or uncertainty was supplied")
                elif (type(value) not in (int, float) or (type(value) is float and not math.isfinite(value))
                      or (key == "uncertainty" and value < 0)):
                    raise EvidenceError(f"{name}.{key}: expected a finite number and nonnegative uncertainty")
            required(item["timebase"], f"{name}.timebase")
            raw_data = attachment(item["raw_file"], f"{name}.raw_file")
            if item["raw_file"] and specification["source_kind"] == "independent_instrument":
                if Path(item["raw_file"]["path"]).name.lower() in ("commands.csv", "telemetry.csv"):
                    finding("not_independent", name, "Dashboard command/telemetry files are not independent instrument observations")
            if raw_data and item["raw_file"]["path"].endswith(".csv"):
                rows = csv_rows(raw_data)
                fields = next(rows)
                if "origin" in fields and any(row["origin"].lower().startswith("synthetic") for _, row in rows):
                    finding("synthetic_raw_data", name, "Raw CSV explicitly declares synthetic origin")
            if specification["source_kind"] == "independent_instrument":
                instrument = item["instrument"]
                if instrument is None:
                    finding("instrument_missing", name, "Independent instrument identity and calibration are not recorded")
                else:
                    R.keys(instrument, {"id", "calibration_file", "calibrated_on", "valid_until"}, where="instrument")
                    required(instrument["id"], f"{name}.instrument.id")
                    attachment(instrument["calibration_file"], f"{name}.calibration_file")
                    try:
                        start = date.fromisoformat(instrument["calibrated_on"])
                        end = date.fromisoformat(instrument["valid_until"])
                    except (TypeError, ValueError) as exc:
                        raise EvidenceError("Instrument calibration needs real ISO dates") from exc
                    if end < start or (captured and not start <= captured.date() <= end):
                        finding("calibration_out_of_date", name, "Declared calibration dates do not cover the capture")
            observation_summary.append({"id": name, "quantity": item["quantity"], "unit": item["unit"],
                                        "source_kind": item["source_kind"], "value": item["value"],
                                        "uncertainty": item["uncertainty"], "performance_verdict": "NOT EVALUATED"})

    stage = "blocked" if findings else "observation_review_candidate" if observation_path else "plan_review_candidate"
    report = {"schema": "project33.bench_readiness/1", "stage": stage, "plan_id": plan["id"],
              "plan_sha256": digest(raw), "source_files_checked": len(current), "changed_sources": changed,
              "observations": observation_summary, "findings": findings, "release_authorized": False,
              "origin_declared": origin,
              "human_signoff": None, "measurement_acceptance": "NOT PERFORMED", "limitations": LIMITATIONS}
    return report, files


def build_readiness(root, plan_path, output, observation_path=None, *, catalog_path="evidence/catalog.json"):
    from .bundle import _instructions, _seal, _write, provenance

    report, files = assess_plan(root, plan_path, observation_path, catalog_path=catalog_path)
    with new_directory(output) as stage:
        for name, data in files.items():
            _write(stage, name, data)
        _write(stage, "readiness.json", canonical_json(report))
        rows = "".join("<tr>" + "".join(f"<td>{html.escape(str(item[key]))}</td>" for key in ("where", "message")) + "</tr>"
                       for item in report["findings"])
        page = ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Bench review readiness</title>'
                '<style>body{font:18px system-ui;max-width:1000px;margin:3rem auto;padding:1rem;color:#17232e}'
                'td,th{text-align:left;padding:.7rem;border-bottom:1px solid #ccc}a{color:#075ba5}</style>'
                f'<h1>Bench review: {html.escape(report["stage"])}</h1>'
                '<p>This checks metadata completeness and file identity. Physical performance has not been evaluated.</p>'
                '<p><a href="readiness.json">Complete findings</a> · <a href="inputs/plan.json">Configuration and plan</a></p>'
                '<table><tr><th>Record</th><th>Finding</th></tr>' + rows + '</table>'
                '<p>No hardware operation, measurement acceptance or release is authorized.</p></html>')
        _write(stage, "index.html", page.encode())
        _write(stage, "README.txt", _instructions().encode())
        _seal(stage, "bench_readiness", provenance(root))
    return report
