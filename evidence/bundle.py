"""Portable, deterministic review bundles with independently checked file hashes."""

from collections import Counter
from pathlib import Path
import platform
import re
import subprocess

from . import __version__
from .common import (EvidenceError, canonical_json, csv_rows, digest, load_json,
                     new_directory, read_bytes, safe_path)
from .telemetry import audit_bytes


KINDS = {"source", "test", "analytical", "synthetic", "physical", "documentation"}
BASES = {"software", "analytical", "synthetic", "physical"}
HEX = re.compile(r"[0-9a-f]{64}\Z")
IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")


def _keys(value, required, optional=()):
    if not isinstance(value, dict):
        raise EvidenceError("Expected a JSON object")
    if set(value) - set(required) - set(optional) or set(required) - set(value):
        raise EvidenceError(f"Unexpected or missing keys; expected {sorted(required)}")


def _strings(values, *, nonempty=True):
    if not isinstance(values, list) or (nonempty and not values):
        raise EvidenceError("Expected a nonempty list" if nonempty else "Expected a list")
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise EvidenceError("Expected nonempty strings")


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError("Expected a nonempty string")


def validate_catalog(catalog):
    _keys(catalog, {"schema_version", "project", "scope", "artifacts", "claims"})
    if type(catalog["schema_version"]) is not int or catalog["schema_version"] != 1:
        raise EvidenceError("Unsupported catalog schema_version")
    _text(catalog["project"])
    _text(catalog["scope"])
    artifacts, paths = {}, set()
    for name in ("artifacts", "claims"):
        if not isinstance(catalog[name], list) or not catalog[name]:
            raise EvidenceError(f"Catalog {name} must be a nonempty list")
        if len(catalog[name]) > 1000:
            raise EvidenceError(f"Too many {name}")
    for item in catalog["artifacts"]:
        _keys(item, {"id", "path", "kind", "format", "description"}, {"columns", "min_rows"})
        _text(item["id"])
        if not IDENTIFIER.fullmatch(item["id"]) or item["id"] in artifacts:
            raise EvidenceError(f"Invalid or duplicate artifact ID: {item['id']}")
        _text(item["kind"])
        _text(item["format"])
        if item["kind"] not in KINDS or item["format"] not in {"file", "csv", "json"}:
            raise EvidenceError(f"Unknown artifact classification: {item['id']}")
        _text(item["description"])
        _text(item["path"])
        if item["path"] in paths:
            raise EvidenceError(f"Duplicate artifact path: {item['path']}")
        paths.add(item["path"])
        if item["format"] == "csv":
            _strings(item.get("columns"))
            if len(set(item["columns"])) != len(item["columns"]):
                raise EvidenceError("CSV columns must be unique")
            minimum = item.get("min_rows")
            if type(minimum) is not int or minimum < 0:
                raise EvidenceError("CSV min_rows must be a nonnegative integer")
        elif "columns" in item or "min_rows" in item:
            raise EvidenceError("CSV options on a non-CSV artifact")
        artifacts[item["id"]] = item
    seen = set()
    for claim in catalog["claims"]:
        _keys(claim, {"id", "title", "statement", "basis", "evidence", "assumptions",
                      "limitations", "next_evidence", "concerns"})
        for name in ("id", "title", "statement", "basis"):
            _text(claim[name])
        if not IDENTIFIER.fullmatch(claim["id"]) or claim["id"] in seen:
            raise EvidenceError(f"Invalid or duplicate claim ID: {claim['id']}")
        seen.add(claim["id"])
        if claim["basis"] not in BASES:
            raise EvidenceError(f"Unknown claim basis: {claim['basis']}")
        for name in ("evidence", "assumptions", "limitations", "next_evidence", "concerns"):
            _strings(claim[name], nonempty=name != "concerns")
        if len(set(claim["evidence"])) != len(claim["evidence"]):
            raise EvidenceError(f"Duplicate evidence reference: {claim['id']}")
        if any(ref not in artifacts for ref in claim["evidence"]):
            raise EvidenceError(f"Unknown artifact reference: {claim['id']}")
        kinds = {artifacts[ref]["kind"] for ref in claim["evidence"]}
        required = {"source", "test"} if claim["basis"] == "software" else {claim["basis"]}
        if not kinds.intersection(required):
            raise EvidenceError(f"Declared basis has no matching evidence: {claim['id']}")
    return catalog


def provenance(root):
    result = {"commit": None, "worktree_dirty": None, "python": platform.python_version()}
    try:
        def git(*args):
            return subprocess.check_output(["git", "-C", str(root), *args],
                                           stderr=subprocess.DEVNULL, timeout=10).decode().strip()
        if Path(git("rev-parse", "--show-toplevel")).resolve() == Path(root).resolve():
            result["commit"] = git("rev-parse", "HEAD")
            result["worktree_dirty"] = bool(git("status", "--porcelain", "--untracked-files=all"))
    except (OSError, subprocess.SubprocessError, UnicodeError):
        pass
    return result


def _write(stage, name, data):
    path = safe_path(stage, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _inspect(item, data):
    details = {**item, "sha256": digest(data), "bytes": len(data),
               "snapshot_path": "artifacts/" + item["path"]}
    if not data:
        raise EvidenceError(f"Empty artifact: {item['path']}")
    if item["format"] == "csv":
        rows = csv_rows(data)
        columns = next(rows)
        if not set(item["columns"]).issubset(columns):
            raise EvidenceError(f"Missing CSV columns: {item['path']}")
        count = sum(1 for _ in rows)
        if count < item["min_rows"]:
            raise EvidenceError(f"Insufficient rows in {item['path']}: {count}")
        details["row_count"] = count
    elif item["format"] == "json":
        load_json(data)
    return details


def _seal(stage, kind, source):
    # Include the actual reviewer implementation so the bundle can be checked offline.
    for path in sorted(Path(__file__).parent.glob("*.py")):
        _write(stage, "reviewer/evidence/" + path.name, read_bytes(path))
    _write(stage, "reviewer/LICENSE", read_bytes(Path(__file__).parent.parent / "LICENSE"))
    files = []
    for path in sorted(stage.rglob("*")):
        if path.is_file():
            data = read_bytes(path)
            files.append({"path": path.relative_to(stage).as_posix(),
                          "bytes": len(data), "sha256": digest(data)})
    manifest = {"schema_version": 1, "kind": kind,
                "producer": f"project33-evidence/{__version__}",
                "provenance": source, "files": files}
    data = canonical_json(manifest)
    _write(stage, "manifest.json", data)
    _write(stage, "manifest.sha256", (digest(data) + "\n").encode())
    return manifest


def build_review(root, output, catalog_path="evidence/catalog.json"):
    from .report import render_review

    root = Path(root).resolve()
    catalog_data = read_bytes(safe_path(root, catalog_path))
    catalog = validate_catalog(load_json(catalog_data))
    source = provenance(root)
    with new_directory(output) as stage:
        _write(stage, "catalog.json", catalog_data)
        artifacts = []
        for item in sorted(catalog["artifacts"], key=lambda item: item["id"]):
            data = read_bytes(safe_path(root, item["path"]))
            detail = _inspect(item, data)
            artifacts.append(detail)
            _write(stage, detail["snapshot_path"], data)
        lookup = {item["id"]: item for item in artifacts}
        claims = []
        for claim in sorted(catalog["claims"], key=lambda item: item["id"]):
            types = sorted({lookup[ref]["kind"] for ref in claim["evidence"]})
            claims.append({**claim, "evidence_types": types,
                           "review_state": "unresolved" if claim["concerns"] else "limited",
                           "has_declared_physical_evidence": "physical" in types})
        assessment = {
            "schema_version": 1, "kind": "project_review", "project": catalog["project"],
            "scope": catalog["scope"], "provenance": source, "artifacts": artifacts,
            "claims": claims, "basis_counts": dict(sorted(Counter(c["basis"] for c in claims).items())),
            "physical_evidence_count": sum(a["kind"] == "physical" for a in artifacts),
            "unresolved_claim_count": sum(c["review_state"] == "unresolved" for c in claims),
            "limitations": [
                "Artifact presence and hash integrity are not scientific validation.",
                "Evidence classifications, assumptions, and concerns are authored declarations.",
                "This build checks file structure; it does not run models, tests, or hardware.",
                "A digest detects changes against a trusted reference; it is not a signature.",
                "No flight readiness, certification, or agency endorsement is asserted.",
            ],
        }
        _write(stage, "assessment.json", canonical_json(assessment))
        _write(stage, "index.html", render_review(assessment).encode())
        _write(stage, "README.txt", _instructions().encode())
        _seal(stage, "project_review", source)
    return assessment


def _instructions():
    return ("PROJECT 33 / OFFLINE EVIDENCE REVIEW\n\n"
            "Open index.html for the report. No server or network is required.\n"
            "From the original repository: python -m evidence verify PATH_TO_THIS_FOLDER\n"
            "Standalone: cd reviewer, then python -m evidence verify ..\n"
            "Python 3.11+; standard library only.\n\n"
            "For independent verification, use reviewer code from a trusted checkout.\n"
            "Compare manifest.sha256 against a digest received through a trusted channel.\n"
            "Use verify --expected-sha256 DIGEST to pin that reference. A changed manifest\n"
            "and a new digest can be created by anyone: hashes are not authentication.\n"
            "This package checks files, not scientific truth or hardware readiness.\n")


def build_audit(csv_path, output, *, origin="unknown", gap_ms=500):
    from .report import render_audit

    data = read_bytes(csv_path)
    audit = audit_bytes(data, origin=origin, gap_ms=gap_ms)
    with new_directory(output) as stage:
        _write(stage, "telemetry.csv", data)
        _write(stage, "audit.json", canonical_json(audit))
        _write(stage, "index.html", render_audit(audit).encode())
        _write(stage, "README.txt", _instructions().encode())
        _seal(stage, "telemetry_quality", {"python": platform.python_version()})
    return audit


def verify_bundle(directory, expected_sha256=None):
    root = Path(directory)
    if root.is_symlink() or not root.is_dir():
        raise EvidenceError("Bundle must be a regular directory")
    data = read_bytes(safe_path(root, "manifest.json"))
    actual = digest(data)
    recorded = read_bytes(safe_path(root, "manifest.sha256")).decode("ascii").strip()
    if not HEX.fullmatch(recorded) or recorded != actual:
        raise EvidenceError("Manifest digest mismatch")
    if expected_sha256 is not None and expected_sha256 != actual:
        raise EvidenceError("Manifest does not match the trusted digest")
    manifest = load_json(data)
    _keys(manifest, {"schema_version", "kind", "producer", "provenance", "files"})
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise EvidenceError("Unsupported manifest schema_version")
    if manifest["kind"] not in ("project_review", "telemetry_quality"):
        raise EvidenceError("Unknown manifest kind")
    if not isinstance(manifest["files"], list) or not manifest["files"] or len(manifest["files"]) > 5000:
        raise EvidenceError("Invalid manifest file list")
    seen = {"manifest.json", "manifest.sha256"}
    for item in manifest["files"]:
        _keys(item, {"path", "bytes", "sha256"})
        path = safe_path(root, item["path"])
        if item["path"] in seen:
            raise EvidenceError(f"Duplicate or reserved manifest path: {item['path']}")
        seen.add(item["path"])
        if type(item["bytes"]) is not int or item["bytes"] < 0:
            raise EvidenceError("Invalid byte count")
        if not isinstance(item["sha256"], str) or not HEX.fullmatch(item["sha256"]):
            raise EvidenceError("Invalid file digest")
        content = read_bytes(path)
        if len(content) != item["bytes"] or digest(content) != item["sha256"]:
            raise EvidenceError(f"Artifact integrity mismatch: {item['path']}")
    required = {"index.html", "README.txt"}
    required |= {"catalog.json", "assessment.json"} if manifest["kind"] == "project_review" else {"audit.json", "telemetry.csv"}
    if not required.issubset(seen):
        raise EvidenceError("Manifest is missing required bundle files")
    found = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise EvidenceError("Unexpected symlink in bundle")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            # Running the included verifier may create bytecode; it is not evidence.
            if "__pycache__" in path.relative_to(root).parts and path.suffix == ".pyc":
                continue
            found.add(relative)
    if found != seen:
        raise EvidenceError(f"Unexpected or missing bundle files: {sorted(found ^ seen)}")
    return {"integrity": "ok", "manifest_sha256": actual, "file_count": len(manifest["files"]),
            "trusted_digest_checked": expected_sha256 is not None, "kind": manifest["kind"]}


def compare_reviews(before, after):
    manifests = []
    for path in (before, after):
        checked = verify_bundle(path)
        if checked["kind"] != "project_review":
            raise EvidenceError("Compare requires two project review bundles")
        manifests.append(load_json(read_bytes(Path(path) / "manifest.json")))
    old = load_json(read_bytes(Path(before) / "assessment.json"))
    new = load_json(read_bytes(Path(after) / "assessment.json"))
    old_artifacts = {a["path"]: a["sha256"] for a in old["artifacts"]}
    new_artifacts = {a["path"]: a["sha256"] for a in new["artifacts"]}
    changed = sorted(path for path in old_artifacts.keys() | new_artifacts.keys()
                     if old_artifacts.get(path) != new_artifacts.get(path))
    old_claims = {c["id"]: c for c in old["claims"]}
    new_claims = {c["id"]: c for c in new["claims"]}
    affected = {key for key in old_claims.keys() | new_claims.keys()
                if old_claims.get(key) != new_claims.get(key)}
    for review in (old, new):
        lookup = {a["id"]: a for a in review["artifacts"]}
        for claim in review["claims"]:
            if any(lookup[ref]["path"] in changed for ref in claim["evidence"]):
                affected.add(claim["id"])
    # Classification and assumption edits matter even if the file bytes are identical.
    old_meta = {a["id"]: a for a in old["artifacts"]}
    new_meta = {a["id"]: a for a in new["artifacts"]}
    changed_meta = {key for key in old_meta.keys() | new_meta.keys() if old_meta.get(key) != new_meta.get(key)}
    for review in (old, new):
        affected.update(c["id"] for c in review["claims"] if changed_meta.intersection(c["evidence"]))
    context_changed = any(old[key] != new[key] for key in ("project", "scope", "limitations"))
    reviewer_files = [{item["path"]: item["sha256"] for item in manifest["files"]
                       if item["path"].startswith("reviewer/")} for manifest in manifests]
    reviewer_changed = reviewer_files[0] != reviewer_files[1]
    if context_changed or reviewer_changed:
        affected.update(old_claims.keys() | new_claims.keys())
    return {"changed_artifacts": changed, "changed_artifact_records": sorted(changed_meta),
            "affected_claims": sorted(affected), "provenance_changed": old["provenance"] != new["provenance"],
            "review_context_changed": context_changed, "reviewer_changed": reviewer_changed,
            "meaning": "Changed evidence needs review; this is not a performance comparison."}
