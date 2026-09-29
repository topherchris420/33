"""A small, fully synthetic evidence project for exercising the reviewer."""

import copy
import json
from pathlib import Path

from evidence.common import canonical_json, digest

MODEL = "import json, sys\njson.dump({'value': 0.25, 'flag': True, 'missing': None}, open(sys.argv[1], 'w'))\n"


def base_records():
    catalog = {
        "schema_version": 2, "project": "Review fixture", "scope": "Synthetic software test only.",
        "records": {"requirements": "requirements.json", "predictions": "predictions.json",
                    "measurements": "measurements.json", "discrepancies": "discrepancies.json",
                    "sessions": "sessions.json", "preregistrations": "preregistrations.json",
                    "archive": "archive/index.json", "reviews": "reviews.json"},
        "artifacts": [
            {"id": "model", "path": "model.py", "class": "implementation", "format": "file", "description": "Model"},
            {"id": "out", "path": "out.json", "class": "analytical", "format": "json", "derived_from": ["model"],
             "description": "Model output"},
            {"id": "fixture", "path": "sample.csv", "class": "synthetic", "format": "csv",
             "columns": ["time_ms", "value", "origin"], "min_rows": 1, "origin_column": "origin",
             "description": "Synthetic"},
            {"id": "tests", "path": "test_model.py", "class": "test_procedure", "format": "file", "description": "Tests"},
        ],
        "recipes": [{"id": "model", "command": ["{python}", "model.py", "{out}/out.json"], "outputs": {"out": "out.json"}}],
        "consistency": [],
        "claims": [{
            "id": "C1", "title": "Fixture", "question": "Does the fixture value exceed 0.2?",
            "statement": "The calculated value exceeds 0.2.", "status": "supported_within_limits",
            "gate": "software_reproduction", "evidence": ["model", "out", "fixture", "tests"], "historical": [],
            "requirements": ["R-1"], "predictions": ["P-1"], "assumptions": ["Synthetic values."],
            "limitations": ["No measurement."], "concerns": [], "measurement_needed": ["Physical data."],
            "measurement_tags": ["timing"]}],
    }
    requirements = {"schema_version": 1, "requirements": [{
        "id": "R-1", "claims": ["C1"], "check": "machine", "text": "Value is at least 0.2.", "source": "Fixture",
        "quantity": "value", "unit": "fraction", "bound": {"min": 0.2},
        "value": {"artifact": "out", "json": "/value"}, "assumptions": [], "implementation": ["model"], "tests": ["tests"]}]}
    predictions = {"schema_version": 1, "predictions": [{
        "id": "P-1", "claims": ["C1"], "status": "active", "quantity": "value", "unit": "fraction",
        "condition": "fixture", "value": 0.25, "uncertainty": None, "evidence_class": "analytical",
        "source": {"artifact": "out", "json": "/value"}, "basis": "Fixture model.",
        "measurement_method": "None.", "acceptance": {"type": "absolute", "tolerance": 0.05},
        "preregistration": None, "registered": "2026-01-01"}]}
    empty = lambda key: {"schema_version": 1, key: []}  # noqa: E731
    return {
        "catalog.json": catalog, "requirements.json": requirements, "predictions.json": predictions,
        "measurements.json": empty("measurements"), "discrepancies.json": empty("discrepancies"),
        "sessions.json": empty("sessions"), "preregistrations.json": empty("preregistrations"),
        "archive/index.json": {"schema_version": 1, "entries": []},
        "reviews.json": {"schema_version": 1, "reviews": {}},
    }


class Project:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "model.py").write_text(MODEL)
        (self.root / "out.json").write_text(json.dumps({"value": 0.25, "flag": True, "missing": None}))
        (self.root / "sample.csv").write_text("time_ms,value,origin\n0,1,synthetic-fixture\n50,2,synthetic-fixture\n")
        (self.root / "test_model.py").write_text("def test_value():\n    assert True\n")
        self.records = base_records()
        self.save()

    @property
    def catalog(self):
        return self.records["catalog.json"]

    @property
    def claim(self):
        return self.catalog["claims"][0]

    def save(self):
        for name, document in self.records.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(canonical_json(document))

    def add_session(self, session_id, raw_text, stage="human_accepted", origin="bench"):
        folder = self.root / "sessions" / session_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "telemetry.csv").write_text(raw_text)
        entry = {"id": session_id, "stage": stage, "origin": origin, "declaration": True,
                 "raw_files": [{"path": f"sessions/{session_id}/telemetry.csv", "sha256": digest(raw_text.encode())}],
                 "audit_manifest_sha256": "a" * 64}
        if stage == "human_accepted":
            entry.update(accepted_by="A. Reviewer", accepted_on="2026-02-01")
        self.records["sessions.json"]["sessions"].append(entry)
        return entry

    def add_measurement(self, measurement_id, session_id, value=0.26, **extra):
        entry = {"id": measurement_id, "prediction": "P-1", "value": value, "unit": "fraction",
                 "uncertainty": 0.01, "evidence_class": "bench_measured", "session": session_id,
                 "instrument": "Calibrated gauge", "calibration": "2026-01-15 certificate", "method": "Fixture",
                 "recorded": "2026-02-02", **extra}
        self.records["measurements.json"]["measurements"].append(entry)
        return entry

    def copy(self):
        return copy.deepcopy(self.records)
