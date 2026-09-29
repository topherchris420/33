"""Evaluate the record against the artifacts it cites.

Nothing here upgrades a claim. Support levels are derived from evidence classes,
requirement results carry the class of the evidence they were computed from,
and anything that cannot be computed is reported as such rather than as zero.
"""

import math
import re
import xml.etree.ElementTree as ET

from .common import EvidenceError, csv_rows, digest, load_json, read_bytes, safe_path
from .records import fingerprint
from . import vocabulary as V

RELATIVE_DRIFT = 1e-9
SEVERITY = ["passed", "skipped", "failed"]
FIRMWARE_PROJECTS = ("Firmware/Rocket", "Firmware/Launcher")
MAX_JUNIT_BYTES = 8 * 1024 * 1024


class Missing:
    """A value the extractor expected but the artifact does not contain."""

    def __init__(self, reason):
        self.reason = reason


# --------------------------------------------------------------------------- artifacts

def load_artifact_data(records):
    """Artifact bytes by ID; None when the file is missing (reported, never zero-filled)."""
    data = {}
    for key, item in records.artifacts.items():
        path = safe_path(records.root, item["path"])
        data[key] = read_bytes(path) if path.exists() or path.is_symlink() else None
    return data


def _table(data):
    rows = csv_rows(data)
    fields = next(rows)
    return fields, [row for _, row in rows]


def inspect_artifact(item, data):
    """Structural facts about one artifact. Raises on data that cannot support review."""
    if data is None:
        raise EvidenceError(f"Missing artifact: {item['path']}")
    if not data:
        raise EvidenceError(f"Empty artifact: {item['path']}")
    details = {**item, "status": item.get("status", "current"), "sha256": digest(data), "bytes": len(data),
               "class_label": V.EVIDENCE_CLASSES[item["class"]]["label"],
               "snapshot_path": "artifacts/" + item["path"]}
    if item["format"] == "csv":
        fields, rows = _table(data)
        if not set(item["columns"]).issubset(fields):
            raise EvidenceError(f"Missing CSV columns: {item['path']}")
        if len(rows) < item["min_rows"]:
            raise EvidenceError(f"Insufficient rows in {item['path']}: {len(rows)}")
        details["row_count"] = len(rows)
        column = item.get("origin_column")
        if column:
            origins = sorted({row[column] for row in rows})
            synthetic = [value.lower().startswith("synthetic") for value in origins]
            if item["class"] == "synthetic" and not all(synthetic):
                raise EvidenceError(f"{item['path']}: declared synthetic but rows claim origin {origins}")
            if item["class"] != "synthetic" and any(synthetic):
                raise EvidenceError(f"{item['path']}: rows say synthetic but the artifact is declared "
                                    f"{item['class']}; synthetic data cannot be relabeled")
            details["origins_in_data"] = origins
    elif item["format"] == "json":
        load_json(data)
    return details


# --------------------------------------------------------------------------- extraction

def _pointer(document, pointer):
    current = document
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            return Missing(f"{pointer} not present")
    return current


def _number(value, where):
    if isinstance(value, Missing) or value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and math.isfinite(value):
        return value
    if isinstance(value, str):
        try:
            number = float(value)
        except ValueError:
            return Missing(f"{where}: non-numeric value {value!r}")
        return number if math.isfinite(number) else Missing(f"{where}: non-finite value")
    return Missing(f"{where}: unsupported value type")


def extract(spec, records, data):
    """Return (values, note). values is a list, None (no value exists), or Missing."""
    artifact = records.artifacts[spec["artifact"]]
    raw = data.get(spec["artifact"])
    if raw is None:
        return Missing(f"{artifact['path']} is missing"), None
    if "json" in spec:
        document = load_json(raw)
        pointers = spec["json"] if isinstance(spec["json"], list) else [spec["json"]]
        values = [_number(_pointer(document, pointer), artifact["path"]) for pointer in pointers]
    elif "rows" in spec:
        return [len(_table(raw)[1])], None
    elif "regex" in spec:
        match = re.search(spec["regex"], raw.decode("utf-8", errors="replace"))
        values = [_number(match.group(1), artifact["path"]) if match else Missing("pattern not found")]
    else:
        _, rows = _table(raw)
        wanted = spec.get("row", {})
        rows = [row for row in rows if all(row.get(key) == value for key, value in wanted.items())]
        if not rows:
            return Missing(f"no matching rows in {artifact['path']}"), None
        values = [_number(row[spec["csv"]], artifact["path"]) for row in rows]
    for value in values:
        if isinstance(value, Missing):
            return value, None
    if any(value is None for value in values):
        return None, "artifact reports no value (null means no value exists)"
    reducer = spec.get("reduce", "values")
    if reducer == "min":
        values = [min(values)]
    elif reducer == "max":
        values = [max(values)]
    elif reducer == "sum":
        values = [sum(values)]
    elif reducer == "relative_excess":
        if len(values) != 2 or values[1] == 0:
            return Missing("relative_excess needs two values and a nonzero reference"), None
        values = [(values[0] - values[1]) / values[1]]
    if "round" in spec:
        values = [round(value, spec["round"]) for value in values]
    return values, None


def _gather(specs, records, data):
    specs = specs if isinstance(specs, list) else [specs]
    values, classes = [], []
    for spec in specs:
        result, note = extract(spec, records, data)
        classes.append(records.artifacts[spec["artifact"]]["class"])
        if isinstance(result, Missing) or result is None:
            return result, note, classes
        values.extend(result)
    return values, None, classes


def _weakest(classes):
    ranked = sorted(classes, key=lambda key: (V.EVIDENCE_CLASSES[key]["rank"], key))
    return ranked[0] if ranked else None


def _within(values, bound):
    for value in values:
        if "equals" in bound and value != bound["equals"]:
            return False
        if "min" in bound and (isinstance(value, bool) or value < bound["min"]):
            return False
        if "max" in bound and (isinstance(value, bool) or value > bound["max"]):
            return False
    return True


def _observed(values):
    if values is None or isinstance(values, Missing):
        return None
    if len(values) > 2 and all(not isinstance(v, bool) for v in values):
        return [min(values), max(values)]
    return values


# --------------------------------------------------------------------------- execution records

def parse_junit(data):
    """Summarize a pytest JUnit XML file. DTDs and entities are refused."""
    if len(data) > MAX_JUNIT_BYTES:
        raise EvidenceError("Execution record too large")
    lowered = data[:4096].lower()
    if b"<!doctype" in lowered or b"<!entity" in data.lower():
        raise EvidenceError("Execution record must not contain a DTD or entities")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise EvidenceError(f"Invalid execution record: {exc}") from exc
    outcomes = {}
    for case in root.iter("testcase"):
        module = case.get("classname", "").split(".")[-1]
        name = case.get("name", "").split("[")[0]
        if not module or not name:
            continue
        if case.find("failure") is not None or case.find("error") is not None:
            outcome = "failed"
        elif case.find("skipped") is not None:
            outcome = "skipped"
        else:
            outcome = "passed"
        key = f"{module}::{name}"
        # A parametrized test passes only if every parameter passed.
        outcomes[key] = max(outcomes.get(key, outcome), outcome, key=SEVERITY.index)
    if not outcomes:
        raise EvidenceError("Execution record contains no test cases")
    counts = {state: sum(value == state for value in outcomes.values()) for state in ("passed", "failed", "skipped")}
    return {"sha256": digest(data), "tests": len(outcomes), **counts, "outcomes": dict(sorted(outcomes.items()))}


# --------------------------------------------------------------------------- requirements

def evaluate_requirement(req, records, data, execution=None, accepted=None):
    base = {"id": req["id"], "check": req["check"], "text": req["text"], "bound": req.get("bound"),
            "unit": req.get("unit"), "observed": None, "evidence_class": None, "alternates": [], "reason": None}
    check = req["check"]
    if check == "machine":
        values, note, classes = _gather(req["value"], records, data)
        base["evidence_class"] = _weakest(classes)
        if isinstance(values, Missing):
            return {**base, "result": "not_evaluable", "reason": values.reason, "missing_value": True}
        if values is None:
            return {**base, "result": "not_evaluable", "reason": note}
        primary = "satisfied" if _within(values, req["bound"]) else "not_satisfied"
        base["observed"] = _observed(values)
        result = primary
        for alternate in req.get("alternate_values", []):
            other, other_note, other_classes = _gather(alternate["value"], records, data)
            if isinstance(other, Missing) or other is None:
                outcome = "not_evaluable"
                reason = other.reason if isinstance(other, Missing) else other_note
            else:
                outcome = "satisfied" if _within(other, req["bound"]) else "not_satisfied"
                reason = None
            base["alternates"].append({"label": alternate["label"], "result": outcome,
                                       "observed": _observed(other), "evidence_class": _weakest(other_classes),
                                       "reason": reason})
            if outcome in ("satisfied", "not_satisfied") and outcome != primary:
                result = "conflicting"
        if result == "conflicting":
            base["reason"] = "Models that are both on record disagree about this requirement."
        return {**base, "result": result}
    if check == "test":
        if execution is None:
            return {**base, "result": "not_evaluated",
                    "reason": "No execution record attached; test source alone is not a run."}
        states = [execution["outcomes"].get(name, "absent") for name in req["tests_required"]]
        base["evidence_class"] = "execution_record"
        base["observed"] = dict(zip(req["tests_required"], states))
        if "failed" in states:
            return {**base, "result": "not_satisfied", "reason": "A required test failed."}
        if any(state != "passed" for state in states):
            return {**base, "result": "not_evaluated",
                    "reason": "A required test was skipped or absent; skipped is not passed."}
        return {**base, "result": "satisfied"}
    if check == "human_review":
        return {**base, "result": "requires_human_review", "reason": "Engineering judgement; software cannot close it."}
    measured = [m for pred in req.get("measured_by", []) for m in (accepted or {}).get(pred, [])]
    if not measured:
        return {**base, "result": "not_measured", "reason": "No accepted inert measurement exists."}
    values = [m["value"] for m in measured]
    base["observed"] = _observed(values)
    base["evidence_class"] = max((m["evidence_class"] for m in measured),
                                 key=lambda key: V.EVIDENCE_CLASSES[key]["rank"])
    if "bound" not in req:
        return {**base, "result": "requires_human_review", "reason": "Measured, but no bound is stated."}
    return {**base, "result": "satisfied" if _within(values, req["bound"]) else "not_satisfied"}


# --------------------------------------------------------------------------- predictions

def _accepted_measurements(records):
    accepted = {}
    for item in records.measurements.values():
        accepted.setdefault(item["prediction"], []).append(item)
    return accepted


def compare_prediction(pred, records, data, accepted):
    current, note = extract(pred["source"], records, data)
    drift = None
    if pred["status"] == "active":
        if isinstance(current, Missing) or current is None:
            drift = f"source value unavailable: {current.reason if isinstance(current, Missing) else note}"
        elif len(current) != 1:
            drift = "source extractor must yield exactly one value"
        elif abs(current[0] - pred["value"]) > RELATIVE_DRIFT * max(1.0, abs(pred["value"])):
            drift = f"registered {pred['value']}, source now reports {current[0]}"
    rows = []
    for item in accepted.get(pred["id"], []):
        error = item["value"] - pred["value"]
        relative = error / abs(pred["value"]) if pred["value"] != 0 else None
        criterion = pred["acceptance"]
        if criterion is None:
            result = "no_criterion"
        else:
            measure = abs(error) if criterion["type"] == "absolute" else (abs(relative) if relative is not None else None)
            result = "not_comparable" if measure is None else (
                "within_criterion" if measure <= criterion["tolerance"] else "outside_criterion")
        rows.append({"measurement": item["id"], "measured": item["value"], "measurement_uncertainty": item["uncertainty"],
                     "evidence_class": item["evidence_class"], "absolute_error": error,
                     "relative_error": relative, "result": result})
    return {
        "id": pred["id"], "claims": pred["claims"], "status": pred["status"], "quantity": pred["quantity"],
        "unit": pred["unit"], "condition": pred["condition"], "predicted": pred["value"],
        "model_uncertainty": pred["uncertainty"], "evidence_class": pred["evidence_class"],
        "basis": pred["basis"], "measurement_method": pred["measurement_method"],
        "acceptance": pred["acceptance"], "preregistration": pred["preregistration"],
        "registered": pred["registered"], "measurements": rows,
        "result": rows[-1]["result"] if rows else "not_measured", "drift": drift,
    }


# --------------------------------------------------------------------------- dependencies and freshness

def claim_dependencies(claim, records):
    """Every artifact a claim's current review rests on, closed over derived_from."""
    direct = set(claim["evidence"])
    for ref in claim["requirements"]:
        req = records.requirements[ref]
        direct.update(req["implementation"] + req["tests"])
        specs = req.get("value", [])
        specs = specs if isinstance(specs, list) else [specs]
        for alternate in req.get("alternate_values", []):
            more = alternate["value"]
            specs = specs + (more if isinstance(more, list) else [more])
        direct.update(spec["artifact"] for spec in specs)
    for ref in claim["predictions"]:
        direct.add(records.predictions[ref]["source"]["artifact"])
    closed, stack = set(), list(direct)
    while stack:
        key = stack.pop()
        if key not in closed:
            closed.add(key)
            stack.extend(records.artifacts[key].get("derived_from", []))
    return sorted(closed)


def statement_fingerprint(claim):
    return fingerprint({key: claim[key] for key in ("title", "question", "statement", "status", "gate")})


def assumptions_fingerprint(claim, records):
    return fingerprint({
        "assumptions": claim["assumptions"], "limitations": claim["limitations"],
        "concerns": claim["concerns"], "measurement_needed": claim["measurement_needed"],
        "requirements": [records.requirements[ref] for ref in claim["requirements"]],
        "predictions": [records.predictions[ref] for ref in claim["predictions"]],
        "discrepancies": [item for item in records.discrepancies.values() if claim["id"] in item["claims"]],
    })


def review_snapshot(claim, records, data):
    return {
        "statement_sha256": statement_fingerprint(claim),
        "assumptions_sha256": assumptions_fingerprint(claim, records),
        "dependencies": {key: (digest(data[key]) if data.get(key) is not None else None)
                         for key in claim_dependencies(claim, records)},
    }


def freshness(claim, records, data):
    entry = records.reviews.get(claim["id"])
    now = review_snapshot(claim, records, data)
    missing = sorted(key for key, value in now["dependencies"].items() if value is None)
    if entry is None:
        return {"state": "never_reviewed", "states": ["never_reviewed"] + (["missing_dependency"] if missing else []),
                "changed": [], "missing": missing, "review": None}
    review = entry["current"]
    states, changed = [], sorted(
        key for key in set(review["dependencies"]) | set(now["dependencies"])
        if review["dependencies"].get(key) != now["dependencies"].get(key) and key not in missing)
    if missing:
        states.append("missing_dependency")
    if review["statement_sha256"] != now["statement_sha256"]:
        states.append("statement_changed")
    if review["assumptions_sha256"] != now["assumptions_sha256"]:
        states.append("assumption_changed")
    if changed:
        states.append("source_changed")
    return {"state": states[0] if states else "current", "states": states or ["current"],
            "changed": changed, "missing": missing,
            "review": {key: review[key] for key in ("kind", "recorded", "recorded_by", "note")}
            | {"independent": bool(review.get("independent"))}}


def impact(records, paths):
    """Which records, claims, and checks depend on the given repository paths."""
    by_path = {item["path"]: key for key, item in records.artifacts.items()}
    children = {}
    for key, item in records.artifacts.items():
        for parent in item.get("derived_from", []):
            children.setdefault(parent, set()).add(key)
    results = []
    for path in paths:
        root = by_path.get(path)
        if root is None:
            touched = [d["id"] for d in records.discrepancies.values() if any(s.get("path") == path for s in d["sides"])]
            results.append({"path": path, "tracked": False, "discrepancies": touched,
                            "meaning": "Not an artifact in the evidence record; no claim depends on it directly."})
            continue
        affected, stack = set(), [root]
        while stack:
            key = stack.pop()
            if key not in affected:
                affected.add(key)
                stack.extend(children.get(key, ()))
        claims = sorted(c["id"] for c in records.claims.values()
                        if affected & set(claim_dependencies(c, records)) or affected & set(c["historical"]))
        requirements = sorted(r["id"] for r in records.requirements.values()
                              if affected & set(_requirement_artifacts(r)))
        predictions = sorted(p["id"] for p in records.predictions.values() if p["source"]["artifact"] in affected)
        discrepancies = sorted(d["id"] for d in records.discrepancies.values()
                               if any(s.get("artifact") in affected or s.get("path") == path for s in d["sides"]))
        recipes = sorted({records.produced_by[key] for key in affected if key in records.produced_by})
        tests = sorted({records.artifacts[ref]["path"] for claim in claims
                        for ref in records.claims[claim]["evidence"]
                        if records.artifacts[ref]["class"] == "test_procedure"})
        results.append({
            "path": path, "tracked": True, "artifact": root,
            "derived_artifacts": sorted(affected - {root}), "claims": claims,
            "requirements": requirements, "predictions": predictions, "discrepancies": discrepancies,
            "stale_generated_docs": ([f"docs/claims/{claim}.md" for claim in claims]
                                     + (["docs/claims/README.md", "docs/TRACEABILITY.md"] if claims else [])),
            "rerun": ([f"python -m evidence reproduce --only {recipe}" for recipe in recipes]
                      + [f"python -m pytest {test}" for test in tests]
                      + [f"pio run -d {project}" for project in FIRMWARE_PROJECTS if path.startswith(project + "/")]
                      + (["python tools/generate_protocol.py --check"] if path.startswith("protocol/") else [])
                      + ["python -m evidence check"]),
            "reviews_no_longer_sufficient": claims,
            "meaning": "Listed claims need another review. A changed dependency does not make a claim false.",
        })
    return results


def _requirement_artifacts(req):
    specs = req.get("value", [])
    specs = specs if isinstance(specs, list) else [specs]
    for alternate in req.get("alternate_values", []):
        more = alternate["value"]
        specs = specs + (more if isinstance(more, list) else [more])
    return req["implementation"] + req["tests"] + [spec["artifact"] for spec in specs]


# --------------------------------------------------------------------------- claims

SUPPORT_ORDER = [key for key, _ in V.SUPPORT_LEVELS]


def support_level(claim, records, requirement_results, accepted):
    level = "none"

    def lift(candidate):
        nonlocal level
        if SUPPORT_ORDER.index(candidate) > SUPPORT_ORDER.index(level):
            level = candidate

    classes = {records.artifacts[ref]["class"] for ref in claim["evidence"]}
    if classes & {"implementation", "test_procedure"}:
        lift("implementation")
    if classes & {"analytical", "simulated"}:
        lift("model")
    if any(r["check"] == "test" and r["result"] == "satisfied" for r in requirement_results):
        lift("software")
    for ref in claim["evidence"]:
        item = records.artifacts[ref]
        if V.EVIDENCE_CLASSES[item["class"]]["physical"] and \
                records.sessions[item["session"]]["stage"] == "human_accepted":
            lift(item["class"])
    for pred in claim["predictions"]:
        for item in accepted.get(pred, []):
            lift(item["evidence_class"])
    review = records.reviews.get(claim["id"], {}).get("current")
    if review and review.get("independent") and level in ("bench_observed", "bench_measured"):
        lift("independently_reviewed")
    return level


def allowed_gate(claim, records, accepted, fresh):
    classes = {records.artifacts[ref]["class"] for ref in claim["evidence"]}
    allowed = -1
    if classes & {"implementation", "analytical", "simulated", "test_procedure"}:
        allowed = V.GATE_INDEX["analytical_model"]
    if "test_procedure" in classes or any(ref in records.produced_by for ref in claim["evidence"]):
        allowed = max(allowed, V.GATE_INDEX["software_reproduction"])
    if "synthetic" in classes:
        allowed = max(allowed, V.GATE_INDEX["synthetic_test"])
    if any(p["status"] in ("registered", "executed") and claim["id"] in p["claims"]
           for p in records.preregistrations.values()):
        allowed = max(allowed, V.GATE_INDEX["inert_bench_setup"])
    measurements = [m for pred in claim["predictions"] for m in accepted.get(pred, [])]
    physical_artifacts = [records.artifacts[ref] for ref in claim["evidence"]
                          if V.EVIDENCE_CLASSES[records.artifacts[ref]["class"]]["physical"]
                          and records.sessions[records.artifacts[ref]["session"]]["stage"] == "human_accepted"]
    if measurements or physical_artifacts:
        allowed = max(allowed, V.GATE_INDEX["inert_physical_measurement"])
    # Repeats must come from distinct sessions whose raw bytes differ.
    raw_sets = {frozenset(raw["sha256"] for raw in records.sessions[m["session"]]["raw_files"]) for m in measurements}
    if len({m["session"] for m in measurements}) >= 2 and len(raw_sets) >= 2:
        allowed = max(allowed, V.GATE_INDEX["repeated_measurement"])
    review = records.reviews.get(claim["id"], {}).get("current")
    if (allowed >= V.GATE_INDEX["repeated_measurement"] and review and review.get("independent")
            and fresh["state"] == "current"):
        allowed = V.GATE_INDEX["independent_review"]
    return allowed


def status_findings(claim, results, discrepancies):
    """(hard_errors, soft_findings) for an authored status against evaluated evidence."""
    hard, soft = [], []
    blocking = [r["id"] for r in results if r["result"] in ("not_satisfied", "conflicting")]
    contradicting = [d["id"] for d in discrepancies if d["status"] == "open" and d["effect"] == "contradicts_claim"]
    open_items = [r["id"] for r in results if r["result"] != "satisfied"] + \
        [d["id"] for d in discrepancies if d["status"] == "open"]
    if claim["status"] == "supported_within_limits":
        if claim["concerns"] or blocking or contradicting:
            hard.append(f"{claim['id']} is marked supported but has open concerns, failing or conflicting "
                        f"requirements {blocking}, or contradicting discrepancies {contradicting}")
    elif claim["status"] == "contradicted":
        if not [r["id"] for r in results if r["result"] == "not_satisfied"] and not contradicting:
            soft.append(f"{claim['id']} is marked contradicted but no requirement fails and no open "
                        "discrepancy contradicts it; the status may be stale")
    elif claim["status"] == "open":
        if not claim["concerns"] and not open_items:
            soft.append(f"{claim['id']} is marked open but nothing on record is open; review the status")
    return hard, soft
