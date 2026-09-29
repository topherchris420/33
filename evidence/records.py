"""Load and structurally validate the evidence record.

A structural error here means no report is produced: a review built on a
malformed or self-promoting record could mislead. Judgements that depend on
evaluating artifacts (drift, staleness, status consistency) live in evaluate.py.
"""

from pathlib import Path
import re

from .common import EvidenceError, canonical_json, digest, load_json, read_bytes, safe_path
from . import vocabulary as V

IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,63}\Z")
HEX = re.compile(r"[0-9a-f]{64}\Z")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
RECORD_KINDS = ("requirements", "predictions", "measurements", "discrepancies",
                "sessions", "preregistrations", "archive", "reviews")
RECORD_LISTS = {"requirements": "requirements", "predictions": "predictions",
                "measurements": "measurements", "discrepancies": "discrepancies",
                "sessions": "sessions", "preregistrations": "preregistrations",
                "archive": "entries"}
FORMATS = {"file", "csv", "json"}
REDUCERS = {"values", "min", "max", "sum", "relative_excess"}


def keys(value, required, optional=(), where="record"):
    if not isinstance(value, dict):
        raise EvidenceError(f"{where}: expected a JSON object")
    extra = set(value) - set(required) - set(optional)
    missing = set(required) - set(value)
    if extra or missing:
        raise EvidenceError(f"{where}: unexpected keys {sorted(extra)} or missing keys {sorted(missing)}")


def text(value, where):
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"{where}: expected a nonempty string")


def optional_text(value, where):
    if value is not None:
        text(value, where)


def strings(values, where, nonempty=True):
    if not isinstance(values, list) or (nonempty and not values):
        raise EvidenceError(f"{where}: expected a {'nonempty ' if nonempty else ''}list")
    for value in values:
        text(value, where)
    if len(set(values)) != len(values):
        raise EvidenceError(f"{where}: duplicate entries")


def number(value, where, *, nullable=False):
    if value is None and nullable:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceError(f"{where}: expected a finite number")


def identifier(value, where):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise EvidenceError(f"{where}: invalid identifier {value!r}")


def date(value, where, *, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, str) or not DATE.fullmatch(value):
        raise EvidenceError(f"{where}: expected a YYYY-MM-DD date")


def fingerprint(value):
    return digest(canonical_json(value))


def preregistration_fingerprint(entry):
    """The parts of a pre-registration a result is judged against."""
    return fingerprint({key: entry.get(key) for key in (
        "question", "prediction", "variables", "interpretation_rule", "measurement_method",
        "predictions", "requirements")})


class Records:
    """All record files, their raw bytes, and id lookups."""

    def __init__(self, root, catalog_path):
        self.root = Path(root).resolve()
        self.catalog_path = catalog_path
        self.raw = {}
        catalog_bytes = read_bytes(safe_path(self.root, catalog_path))
        self.raw["catalog"] = (catalog_path, catalog_bytes)
        self.catalog = load_json(catalog_bytes)
        keys(self.catalog, {"schema_version", "project", "scope", "artifacts", "claims"},
             {"recipes", "consistency", "records"}, "catalog")
        if type(self.catalog["schema_version"]) is not int or self.catalog["schema_version"] != 2:
            raise EvidenceError("Unsupported catalog schema_version (expected 2)")
        declared = self.catalog.get("records", {})
        keys(declared, (), RECORD_KINDS, "catalog.records")
        self.declared = {}
        for kind, name in declared.items():
            text(name, f"catalog.records.{kind}")
            path = (Path(catalog_path).parent / name).as_posix()
            self.declared[kind] = path
            data = read_bytes(safe_path(self.root, path))
            self.raw[kind] = (path, data)
        self.docs = {kind: load_json(self.raw[kind][1]) for kind in self.declared}
        for kind, document in self.docs.items():
            if kind == "reviews":
                keys(document, {"schema_version", "reviews"}, {"note"}, kind)
            else:
                keys(document, {"schema_version", RECORD_LISTS[kind]}, {"note"}, kind)
            if document["schema_version"] != 1 or type(document["schema_version"]) is not int:
                raise EvidenceError(f"{kind}: unsupported schema_version")

    def entries(self, kind):
        """Entries of a record kind; None when the project does not keep that record."""
        if kind not in self.docs:
            return None
        return self.docs[kind]["reviews" if kind == "reviews" else RECORD_LISTS[kind]]

    def list(self, kind):
        return self.entries(kind) or ([] if kind != "reviews" else {})


def _extractor(spec, artifacts, where):
    keys(spec, {"artifact"}, {"json", "csv", "reduce", "rows", "regex", "row", "round"}, where)
    if spec["artifact"] not in artifacts:
        raise EvidenceError(f"{where}: unknown artifact {spec['artifact']}")
    artifact = artifacts[spec["artifact"]]
    modes = [name for name in ("json", "csv", "rows", "regex") if name in spec]
    if len(modes) != 1:
        raise EvidenceError(f"{where}: exactly one of json, csv, rows, regex is required")
    mode = modes[0]
    expected = {"json": "json", "csv": "csv", "rows": "csv", "regex": "file"}[mode]
    if mode != "regex" and artifact["format"] != expected:
        raise EvidenceError(f"{where}: {mode} extractor on a {artifact['format']} artifact")
    if mode == "json":
        pointers = spec["json"] if isinstance(spec["json"], list) else [spec["json"]]
        for pointer in pointers:
            if not isinstance(pointer, str) or not pointer.startswith("/"):
                raise EvidenceError(f"{where}: JSON pointers start with '/'")
    if mode == "csv":
        text(spec["csv"], where)
        if spec["csv"] not in artifact.get("columns", []):
            raise EvidenceError(f"{where}: column {spec['csv']} is not a declared column")
        if "row" in spec:
            keys(spec["row"], (), artifact["columns"], where)
    if mode == "rows" and spec["rows"] is not True:
        raise EvidenceError(f"{where}: rows must be true")
    if mode == "regex":
        text(spec["regex"], where)
        try:
            if re.compile(spec["regex"]).groups != 1:
                raise EvidenceError(f"{where}: regex needs exactly one group")
        except re.error as exc:
            raise EvidenceError(f"{where}: invalid regex") from exc
    if "reduce" in spec and spec["reduce"] not in REDUCERS:
        raise EvidenceError(f"{where}: unknown reducer")
    if "round" in spec and (type(spec["round"]) is not int or not 0 <= spec["round"] <= 12):
        raise EvidenceError(f"{where}: round must be an integer 0-12")


def _extractors(value, artifacts, where):
    for index, spec in enumerate(value if isinstance(value, list) else [value]):
        _extractor(spec, artifacts, f"{where}[{index}]")


def _acyclic(artifacts):
    state = {}

    def visit(key, path):
        if state.get(key) == "done":
            return
        if state.get(key) == "active":
            raise EvidenceError(f"Artifact dependency cycle: {' -> '.join(path + [key])}")
        state[key] = "active"
        for parent in artifacts[key].get("derived_from", []):
            visit(parent, path + [key])
        state[key] = "done"

    for key in artifacts:
        visit(key, [])


def validate(records):
    """Structural validation across every record file. Raises EvidenceError."""
    catalog = records.catalog
    text(catalog["project"], "catalog.project")
    text(catalog["scope"], "catalog.scope")
    for name in ("artifacts", "claims"):
        if not isinstance(catalog[name], list) or not catalog[name] or len(catalog[name]) > 1000:
            raise EvidenceError(f"Catalog {name} must be a nonempty list of at most 1000 entries")

    artifacts, paths = {}, set()
    for item in catalog["artifacts"]:
        where = f"artifact {item.get('id') if isinstance(item, dict) else '?'}"
        if isinstance(item, dict) and "kind" in item:
            raise EvidenceError(f"{where}: 'kind' was replaced by 'class' in schema 2")
        keys(item, {"id", "path", "class", "format", "description"},
             {"columns", "min_rows", "origin_column", "derived_from", "status", "session"}, where)
        identifier(item["id"], where)
        if item["id"] in artifacts:
            raise EvidenceError(f"Duplicate artifact ID: {item['id']}")
        if item["class"] in V.FORBIDDEN_CLASSES:
            raise EvidenceError(f"{where}: class '{item['class']}' refused. {V.FORBIDDEN_CLASSES[item['class']]}")
        if item["class"] not in V.EVIDENCE_CLASSES:
            raise EvidenceError(f"{where}: unknown evidence class {item['class']!r}")
        if item["class"] == "execution_record":
            raise EvidenceError(f"{where}: execution records are attached at build time, never cataloged")
        if item["format"] not in FORMATS:
            raise EvidenceError(f"{where}: unknown format")
        text(item["description"], where)
        text(item["path"], where)
        safe_path(records.root, item["path"])
        if item["path"] in paths:
            raise EvidenceError(f"Duplicate artifact path: {item['path']}")
        paths.add(item["path"])
        if item.get("status", "current") not in ("current", "superseded"):
            raise EvidenceError(f"{where}: status must be current or superseded")
        if item["format"] == "csv":
            strings(item.get("columns"), where)
            if type(item.get("min_rows")) is not int or item["min_rows"] < 0:
                raise EvidenceError(f"{where}: CSV min_rows must be a nonnegative integer")
            if "origin_column" in item and item["origin_column"] not in item["columns"]:
                raise EvidenceError(f"{where}: origin_column must be a declared column")
        elif any(name in item for name in ("columns", "min_rows", "origin_column")):
            raise EvidenceError(f"{where}: CSV options on a non-CSV artifact")
        if V.EVIDENCE_CLASSES[item["class"]]["physical"] and "session" not in item:
            raise EvidenceError(f"{where}: a {item['class']} artifact must name the bench session it came from")
        artifacts[item["id"]] = item
    for item in artifacts.values():
        strings(item.get("derived_from", []), f"artifact {item['id']}.derived_from", nonempty=False)
        for parent in item.get("derived_from", []):
            if parent not in artifacts:
                raise EvidenceError(f"artifact {item['id']}: unknown dependency {parent}")
    _acyclic(artifacts)

    produced = {}
    recipe_ids = set()
    for recipe in catalog.get("recipes", []):
        keys(recipe, {"id", "command", "outputs"}, (), "recipe")
        identifier(recipe["id"], "recipe")
        if recipe["id"] in recipe_ids:
            raise EvidenceError(f"Duplicate recipe: {recipe['id']}")
        recipe_ids.add(recipe["id"])
        strings(recipe["command"], f"recipe {recipe['id']}.command")
        if not isinstance(recipe["outputs"], dict) or not recipe["outputs"]:
            raise EvidenceError(f"recipe {recipe['id']}: outputs must be a nonempty object")
        for artifact_id, name in recipe["outputs"].items():
            if artifact_id not in artifacts or artifact_id in produced:
                raise EvidenceError(f"recipe {recipe['id']}: unknown or doubly produced artifact {artifact_id}")
            if artifacts[artifact_id]["class"] not in ("analytical", "simulated"):
                raise EvidenceError(f"recipe {recipe['id']}: only model outputs are reproduced")
            if not isinstance(name, str) or "/" in name or not name:
                raise EvidenceError(f"recipe {recipe['id']}: output names are plain file names")
            produced[artifact_id] = recipe["id"]

    check_ids = set()
    for check in catalog.get("consistency", []):
        keys(check, {"id", "claims", "description", "left", "right", "tolerance"}, (), "consistency")
        identifier(check["id"], "consistency")
        if check["id"] in check_ids:
            raise EvidenceError(f"Duplicate consistency check: {check['id']}")
        check_ids.add(check["id"])
        text(check["description"], check["id"])
        number(check["tolerance"], check["id"])
        if check["tolerance"] < 0:
            raise EvidenceError(f"{check['id']}: tolerance must be nonnegative")
        _extractor(check["left"], artifacts, f"{check['id']}.left")
        _extractor(check["right"], artifacts, f"{check['id']}.right")

    requirements = {}
    for item in records.list("requirements"):
        where = f"requirement {item.get('id') if isinstance(item, dict) else '?'}"
        keys(item, {"id", "claims", "check", "text", "source", "assumptions", "implementation", "tests"},
             {"quantity", "unit", "bound", "value", "alternate_values", "tests_required", "measured_by", "note"}, where)
        identifier(item["id"], where)
        if item["id"] in requirements:
            raise EvidenceError(f"Duplicate requirement: {item['id']}")
        if item["check"] not in V.CHECK_TYPES:
            raise EvidenceError(f"{where}: unknown check type")
        text(item["text"], where)
        text(item["source"], where)
        for name in ("assumptions", "implementation", "tests"):
            strings(item[name], f"{where}.{name}", nonempty=False)
        for ref in item["implementation"] + item["tests"]:
            if ref not in artifacts:
                raise EvidenceError(f"{where}: unknown artifact {ref}")
        if "bound" in item:
            keys(item["bound"], (), ("min", "max", "equals"), f"{where}.bound")
            if not item["bound"]:
                raise EvidenceError(f"{where}: empty bound")
            for name in ("min", "max"):
                if name in item["bound"]:
                    number(item["bound"][name], f"{where}.bound.{name}")
        if item["check"] == "machine":
            if "bound" not in item or "value" not in item:
                raise EvidenceError(f"{where}: machine checks need a bound and a value extractor")
            _extractors(item["value"], artifacts, f"{where}.value")
            for index, alternate in enumerate(item.get("alternate_values", [])):
                keys(alternate, {"label", "value"}, (), f"{where}.alternate_values[{index}]")
                text(alternate["label"], where)
                _extractors(alternate["value"], artifacts, f"{where}.alternate_values[{index}]")
        elif "value" in item or "alternate_values" in item:
            raise EvidenceError(f"{where}: only machine checks read artifact values")
        if item["check"] == "test":
            strings(item.get("tests_required"), f"{where}.tests_required")
            for name in item["tests_required"]:
                if name.count("::") != 1:
                    raise EvidenceError(f"{where}: tests are named module::test_name")
        elif "tests_required" in item:
            raise EvidenceError(f"{where}: tests_required only applies to test checks")
        requirements[item["id"]] = item

    predictions = {}
    for item in records.list("predictions"):
        where = f"prediction {item.get('id') if isinstance(item, dict) else '?'}"
        keys(item, {"id", "claims", "status", "quantity", "unit", "condition", "value", "uncertainty",
                    "evidence_class", "source", "basis", "measurement_method", "acceptance",
                    "preregistration", "registered"}, {"superseded_by"}, where)
        identifier(item["id"], where)
        if item["id"] in predictions:
            raise EvidenceError(f"Duplicate prediction: {item['id']}")
        if item["status"] not in ("active", "superseded"):
            raise EvidenceError(f"{where}: status must be active or superseded")
        if item["status"] == "superseded" and not item.get("superseded_by"):
            raise EvidenceError(f"{where}: superseded predictions name their successor")
        for name in ("quantity", "unit", "condition", "basis", "measurement_method"):
            text(item[name], f"{where}.{name}")
        number(item["value"], f"{where}.value")
        number(item["uncertainty"], f"{where}.uncertainty", nullable=True)
        if item["evidence_class"] not in V.EVIDENCE_CLASSES or V.EVIDENCE_CLASSES[item["evidence_class"]]["physical"]:
            raise EvidenceError(f"{where}: a prediction's class must be non-physical")
        _extractor(item["source"], artifacts, f"{where}.source")
        if item["acceptance"] is not None:
            keys(item["acceptance"], {"type", "tolerance"}, (), f"{where}.acceptance")
            if item["acceptance"]["type"] not in ("absolute", "relative"):
                raise EvidenceError(f"{where}: acceptance type is absolute or relative")
            number(item["acceptance"]["tolerance"], where)
            if item["acceptance"]["tolerance"] <= 0:
                raise EvidenceError(f"{where}: acceptance tolerance must be positive")
        date(item["registered"], where)
        predictions[item["id"]] = item
    for item in predictions.values():
        if item.get("superseded_by") and item["superseded_by"] not in predictions:
            raise EvidenceError(f"prediction {item['id']}: unknown successor")

    for item in requirements.values():
        for ref in item.get("measured_by", []):
            if ref not in predictions:
                raise EvidenceError(f"requirement {item['id']}: unknown prediction {ref}")
        if item["check"] == "physical_measurement" and "bound" in item and not item.get("measured_by"):
            raise EvidenceError(f"requirement {item['id']}: a bounded physical requirement names its prediction")

    sessions = {}
    for item in records.list("sessions"):
        where = f"session {item.get('id') if isinstance(item, dict) else '?'}"
        keys(item, {"id", "stage", "origin", "raw_files", "declaration"},
             {"audit_manifest_sha256", "accepted_by", "accepted_on", "rejection_reason", "notes", "tags"}, where)
        identifier(item["id"], where)
        if item["id"] in sessions:
            raise EvidenceError(f"Duplicate session: {item['id']}")
        if item["stage"] not in V.SESSION_STAGES or item["origin"] not in V.SESSION_ORIGINS:
            raise EvidenceError(f"{where}: unknown stage or origin")
        if not isinstance(item["raw_files"], list) or not item["raw_files"]:
            raise EvidenceError(f"{where}: raw_files must list the captured files")
        for raw in item["raw_files"]:
            keys(raw, {"path", "sha256"}, (), where)
            if not isinstance(raw["sha256"], str) or not HEX.fullmatch(raw["sha256"]):
                raise EvidenceError(f"{where}: invalid raw-file digest")
            data = read_bytes(safe_path(records.root, raw["path"]))
            if digest(data) != raw["sha256"]:
                raise EvidenceError(f"{where}: raw file changed after registration: {raw['path']}")
        if item["stage"] in ("audited", "review_candidate", "human_accepted"):
            if not HEX.fullmatch(str(item.get("audit_manifest_sha256", ""))):
                raise EvidenceError(f"{where}: stage {item['stage']} requires an audit manifest digest")
        if item["stage"] in ("review_candidate", "human_accepted") and not item["declaration"]:
            raise EvidenceError(f"{where}: stage {item['stage']} requires an operator declaration")
        if item["stage"] == "human_accepted":
            text(item.get("accepted_by"), f"{where}.accepted_by")
            date(item.get("accepted_on"), where)
            if item["origin"] != "bench":
                raise EvidenceError(f"{where}: only a declared bench origin can be accepted as physical evidence")
        elif "accepted_by" in item or "accepted_on" in item:
            raise EvidenceError(f"{where}: acceptance fields on a session that is not human_accepted")
        if item["stage"] == "rejected":
            text(item.get("rejection_reason"), where)
        sessions[item["id"]] = item
    for item in artifacts.values():
        if "session" in item:
            if item["session"] not in sessions:
                raise EvidenceError(f"artifact {item['id']}: unknown session {item['session']}")

    preregistrations = {}
    for item in records.list("preregistrations"):
        where = f"preregistration {item.get('id') if isinstance(item, dict) else '?'}"
        keys(item, {"id", "status", "title", "claims", "predictions", "requirements", "proposed_by",
                    "registered_by", "registered_on", "question", "prediction", "variables",
                    "interpretation_rule", "measurement_method", "known_limitations", "safety"},
             {"roadmap_stage", "withdrawn_reason"}, where)
        identifier(item["id"], where)
        if item["id"] in preregistrations:
            raise EvidenceError(f"Duplicate preregistration: {item['id']}")
        if item["status"] not in V.PREREGISTRATION_STATUSES:
            raise EvidenceError(f"{where}: unknown status")
        for name in ("title", "proposed_by", "question", "prediction", "interpretation_rule",
                     "measurement_method", "safety"):
            text(item[name], f"{where}.{name}")
        strings(item["known_limitations"], where)
        keys(item["variables"], {"controlled", "measured", "recorded"}, (), f"{where}.variables")
        for ref in item["predictions"]:
            if ref not in predictions:
                raise EvidenceError(f"{where}: unknown prediction {ref}")
        for ref in item["requirements"]:
            if ref not in requirements:
                raise EvidenceError(f"{where}: unknown requirement {ref}")
        if item["status"] in ("registered", "executed"):
            text(item["registered_by"], f"{where}.registered_by")
            date(item["registered_on"], where)
        elif item["status"] == "proposed" and (item["registered_by"] or item["registered_on"]):
            raise EvidenceError(f"{where}: a proposed entry has not been registered by anyone")
        preregistrations[item["id"]] = item
    for item in predictions.values():
        if item["preregistration"] is not None and item["preregistration"] not in preregistrations:
            raise EvidenceError(f"prediction {item['id']}: unknown preregistration")

    measurements = {}
    for item in records.list("measurements"):
        where = f"measurement {item.get('id') if isinstance(item, dict) else '?'}"
        keys(item, {"id", "prediction", "value", "unit", "uncertainty", "evidence_class", "session",
                    "instrument", "method", "recorded"}, {"preregistration", "preregistration_fingerprint",
                                                         "calibration", "notes"}, where)
        identifier(item["id"], where)
        if item["id"] in measurements:
            raise EvidenceError(f"Duplicate measurement: {item['id']}")
        if item["prediction"] not in predictions:
            raise EvidenceError(f"{where}: unknown prediction")
        number(item["value"], f"{where}.value")
        if item["evidence_class"] not in ("bench_observed", "bench_measured"):
            raise EvidenceError(f"{where}: measurements are bench_observed or bench_measured")
        if item["evidence_class"] == "bench_measured":
            number(item["uncertainty"], f"{where}.uncertainty")
            text(item.get("calibration"), f"{where}.calibration")
        else:
            number(item["uncertainty"], f"{where}.uncertainty", nullable=True)
        if item["unit"] != predictions[item["prediction"]]["unit"]:
            raise EvidenceError(f"{where}: unit differs from its prediction; convert before recording")
        text(item["instrument"], where)
        text(item["method"], where)
        date(item["recorded"], where)
        session = sessions.get(item["session"])
        if session is None or session["stage"] != "human_accepted":
            raise EvidenceError(f"{where}: measurements enter the record only from a human-accepted session")
        registered = predictions[item["prediction"]]["preregistration"]
        if registered is not None or item.get("preregistration") is not None:
            entry = preregistrations.get(item.get("preregistration"))
            if entry is None or item["preregistration"] != registered:
                raise EvidenceError(f"{where}: must cite its prediction's preregistration {registered}")
            if entry["status"] not in ("registered", "executed"):
                raise EvidenceError(f"{where}: preregistration {entry['id']} was never registered by a human")
            if item.get("preregistration_fingerprint") != preregistration_fingerprint(entry):
                raise EvidenceError(f"{where}: preregistration {entry['id']} changed after this result was judged")
            if item["recorded"] < entry["registered_on"]:
                raise EvidenceError(f"{where}: recorded before its preregistration")
        measurements[item["id"]] = item

    claims = {}
    for claim in catalog["claims"]:
        where = f"claim {claim.get('id') if isinstance(claim, dict) else '?'}"
        if isinstance(claim, dict) and ("basis" in claim or "verified" in claim):
            raise EvidenceError(f"{where}: 'basis' and 'verified' are not schema-2 fields; support is derived")
        keys(claim, {"id", "title", "question", "statement", "status", "gate", "evidence", "historical",
                     "requirements", "predictions", "assumptions", "limitations", "concerns",
                     "measurement_needed", "measurement_tags"}, {"superseded_by"}, where)
        identifier(claim["id"], where)
        if claim["id"] in claims:
            raise EvidenceError(f"Duplicate claim ID: {claim['id']}")
        for name in ("title", "question", "statement"):
            text(claim[name], f"{where}.{name}")
        if claim["status"] not in V.CLAIM_STATUSES:
            raise EvidenceError(f"{where}: unknown status {claim['status']!r}")
        if claim["gate"] not in V.GATE_INDEX:
            raise EvidenceError(f"{where}: unknown gate {claim['gate']!r}")
        for name in ("evidence", "assumptions", "limitations", "measurement_needed"):
            strings(claim[name], f"{where}.{name}")
        for name in ("historical", "requirements", "predictions", "concerns", "measurement_tags"):
            strings(claim[name], f"{where}.{name}", nonempty=False)
        for ref in claim["evidence"]:
            if ref not in artifacts:
                raise EvidenceError(f"{where}: unknown artifact reference {ref}")
            if artifacts[ref].get("status") == "superseded":
                raise EvidenceError(f"{where}: superseded artifact {ref} cited as current evidence")
        for ref in claim["historical"]:
            if ref not in artifacts or artifacts[ref].get("status") != "superseded":
                raise EvidenceError(f"{where}: historical reference {ref} must be a superseded artifact")
        for ref in claim["requirements"]:
            if ref not in requirements or claim["id"] not in requirements[ref]["claims"]:
                raise EvidenceError(f"{where}: requirement {ref} missing or not linked back")
        for ref in claim["predictions"]:
            if ref not in predictions or claim["id"] not in predictions[ref]["claims"]:
                raise EvidenceError(f"{where}: prediction {ref} missing or not linked back")
        if claim["status"] == "superseded" and not claim.get("superseded_by"):
            raise EvidenceError(f"{where}: superseded claims name their successor")
        claims[claim["id"]] = claim
    for collection, name in ((requirements, "requirement"), (predictions, "prediction")):
        for item in collection.values():
            strings(item["claims"], f"{name} {item['id']}.claims", nonempty=False)
            for ref in item["claims"]:
                if ref not in claims or item["id"] not in claims[ref][name + "s"]:
                    raise EvidenceError(f"{name} {item['id']}: claim {ref} missing or not linked back")
    for check in catalog.get("consistency", []):
        strings(check["claims"], check["id"], nonempty=False)
        for ref in check["claims"]:
            if ref not in claims:
                raise EvidenceError(f"{check['id']}: unknown claim {ref}")
    for item in preregistrations.values():
        for ref in item["claims"]:
            if ref not in claims:
                raise EvidenceError(f"preregistration {item['id']}: unknown claim {ref}")

    discrepancies = {}
    for item in records.list("discrepancies"):
        where = f"discrepancy {item.get('id') if isinstance(item, dict) else '?'}"
        keys(item, {"id", "kind", "claims", "effect", "status", "title", "sides", "found_by",
                    "next_action", "resolution", "resolved_by"}, {"progress"}, where)
        if not isinstance(item["id"], str) or not re.fullmatch(r"D-\d{3}", item["id"]):
            raise EvidenceError(f"{where}: discrepancy IDs look like D-001")
        if item["id"] in discrepancies:
            raise EvidenceError(f"Duplicate discrepancy: {item['id']}")
        if item["kind"] not in V.DISCREPANCY_KINDS or item["effect"] not in V.DISCREPANCY_EFFECTS \
                or item["status"] not in V.DISCREPANCY_STATUSES:
            raise EvidenceError(f"{where}: unknown kind, effect, or status")
        for name in ("title", "found_by", "next_action"):
            text(item[name], f"{where}.{name}")
        optional_text(item.get("progress"), f"{where}.progress")
        strings(item["claims"], f"{where}.claims", nonempty=False)
        for ref in item["claims"]:
            if ref not in claims:
                raise EvidenceError(f"{where}: unknown claim {ref}")
        if not isinstance(item["sides"], list) or len(item["sides"]) < 2:
            raise EvidenceError(f"{where}: a discrepancy has at least two sides")
        for side in item["sides"]:
            if not isinstance(side, dict) or len({"artifact", "path"} & set(side)) != 1:
                raise EvidenceError(f"{where}: each side names one artifact or one path")
            keys(side, {"says"}, {"artifact", "path"}, where)
            text(side["says"], where)
            if "artifact" in side and side["artifact"] not in artifacts:
                raise EvidenceError(f"{where}: unknown artifact {side['artifact']}")
            if "path" in side:
                target = safe_path(records.root, side["path"])
                if not target.is_file():
                    raise EvidenceError(f"{where}: missing file {side['path']}")
        if item["status"] == "open":
            if item["resolution"] is not None or item["resolved_by"] is not None:
                raise EvidenceError(f"{where}: an open discrepancy has no resolution yet (use progress)")
        else:
            text(item["resolution"], f"{where}.resolution")
            text(item["resolved_by"], f"{where}.resolved_by")
        discrepancies[item["id"]] = item

    archived = {}
    for item in records.list("archive"):
        where = f"archive entry {item.get('path') if isinstance(item, dict) else '?'}"
        keys(item, {"path", "original_path", "sha256", "kind", "archived", "reason", "discrepancies",
                    "superseded_by"}, (), where)
        text(item["reason"], where)
        text(item["original_path"], where)
        date(item["archived"], where)
        data = read_bytes(safe_path(records.root, item["path"]))
        if digest(data) != item["sha256"]:
            raise EvidenceError(f"{where}: archived bytes changed; the archive is append-only")
        if item["path"] in archived:
            raise EvidenceError(f"Duplicate archive entry: {item['path']}")
        for ref in item["discrepancies"]:
            if ref not in discrepancies:
                raise EvidenceError(f"{where}: unknown discrepancy {ref}")
        if item["superseded_by"] is not None and item["superseded_by"] not in artifacts:
            raise EvidenceError(f"{where}: unknown successor artifact")
        archived[item["path"]] = item
    if records.entries("archive") is not None:
        for item in artifacts.values():
            if item.get("status") == "superseded" and item["path"] not in archived:
                raise EvidenceError(f"artifact {item['id']}: superseded artifacts must be in the archive index")

    reviews = records.list("reviews")
    if not isinstance(reviews, dict):
        raise EvidenceError("reviews: expected an object keyed by claim ID")
    for claim_id, entry in reviews.items():
        if claim_id not in claims:
            raise EvidenceError(f"reviews: unknown claim {claim_id}")
        keys(entry, {"current", "history"}, (), f"reviews.{claim_id}")
        for record in [entry["current"]] + list(entry["history"]):
            keys(record, {"kind", "recorded", "recorded_by", "note", "statement_sha256",
                          "assumptions_sha256", "dependencies"}, {"independent"}, f"reviews.{claim_id}")
            if record["kind"] not in V.REVIEW_KINDS:
                raise EvidenceError(f"reviews.{claim_id}: unknown review kind")
            date(record["recorded"], f"reviews.{claim_id}")
            text(record["recorded_by"], f"reviews.{claim_id}")
            text(record["note"], f"reviews.{claim_id}")
            if record.get("independent") and record["kind"] != "human":
                raise EvidenceError(f"reviews.{claim_id}: only a human review can be independent")
            for name in ("statement_sha256", "assumptions_sha256"):
                if not HEX.fullmatch(str(record[name])):
                    raise EvidenceError(f"reviews.{claim_id}: invalid {name}")
            if not isinstance(record["dependencies"], dict):
                raise EvidenceError(f"reviews.{claim_id}: dependencies must map artifact IDs to digests")
            for value in record["dependencies"].values():
                if value is not None and not HEX.fullmatch(str(value)):
                    raise EvidenceError(f"reviews.{claim_id}: invalid dependency digest")

    records.artifacts = artifacts
    records.claims = claims
    records.requirements = requirements
    records.predictions = predictions
    records.measurements = measurements
    records.sessions = sessions
    records.preregistrations = preregistrations
    records.discrepancies = discrepancies
    records.archived = archived
    records.reviews = reviews
    records.produced_by = produced
    return records


def load(root, catalog_path="evidence/catalog.json"):
    return validate(Records(root, catalog_path))
