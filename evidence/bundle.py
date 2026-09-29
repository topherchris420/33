"""Portable, deterministic review packets with independently checked file hashes."""

from pathlib import Path
import platform
import re
import subprocess

from . import __version__
from . import assess as A
from . import evaluate as E
from . import records as R
from .common import (EvidenceError, canonical_json, digest, load_json, new_directory, read_bytes, safe_path)
from .telemetry import audit_bytes

HEX = re.compile(r"[0-9a-f]{64}\Z")
KINDS = {
    "project_review": {"records/catalog.json", "assessment.json", "questions.json"},
    "telemetry_quality": {"audit.json", "telemetry.csv"},
    "session_passport": {"passport.json", "audit.json", "session/telemetry.csv"},
}


def provenance(root):
    result = {"commit": None, "worktree_dirty": None, "python": platform.python_version(),
              "reviewer": f"project33-evidence/{__version__}"}
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


def _seal(stage, kind, source):
    # Include the actual reviewer implementation so the bundle can be checked offline.
    for path in sorted(Path(__file__).parent.glob("*.py")):
        _write(stage, "reviewer/evidence/" + path.name, read_bytes(path))
    _write(stage, "reviewer/LICENSE", read_bytes(Path(__file__).parent.parent / "LICENSE"))
    files = []
    for path in sorted(stage.rglob("*")):
        if path.is_file():
            data = read_bytes(path)
            files.append({"path": path.relative_to(stage).as_posix(), "bytes": len(data), "sha256": digest(data)})
    manifest = {"schema_version": 1, "kind": kind, "producer": f"project33-evidence/{__version__}",
                "provenance": source, "files": files}
    data = canonical_json(manifest)
    _write(stage, "manifest.json", data)
    _write(stage, "manifest.sha256", (digest(data) + "\n").encode())
    return manifest


def load_assessment(root, catalog_path="evidence/catalog.json", *, execution_record=None,
                    reproduction_record=None):
    """Load, validate, and assess the working tree. Returns (records, data, assessment, attachments)."""
    from .workflow import validate_reproduction

    root = Path(root).resolve()
    records = R.load(root, catalog_path)
    data = E.load_artifact_data(records)
    attachments = {}
    execution = reproduction = None
    if execution_record is not None:
        raw = read_bytes(execution_record)
        execution = E.parse_junit(raw)
        attachments["execution/junit.xml"] = raw
    if reproduction_record is not None:
        raw = read_bytes(reproduction_record)
        reproduction = validate_reproduction(load_json(raw))
        attachments["execution/reproduction.json"] = raw
    assessment = A.assess(records, data, provenance=provenance(root), execution=execution,
                          reproduction=reproduction)
    return records, data, assessment, attachments


def build_review(root, output, catalog_path="evidence/catalog.json", *, execution_record=None,
                 reproduction_record=None):
    from .report import render_review

    records, data, assessment, attachments = load_assessment(
        root, catalog_path, execution_record=execution_record, reproduction_record=reproduction_record)
    with new_directory(output) as stage:
        catalog_dir = Path(records.catalog_path).parent
        for kind, (path, raw) in sorted(records.raw.items()):
            _write(stage, "records/" + Path(path).relative_to(catalog_dir).as_posix(), raw)
        for item in assessment["artifacts"]:
            _write(stage, item["snapshot_path"], data[item["id"]])
        for name, raw in sorted(attachments.items()):
            _write(stage, name, raw)
        _write(stage, "assessment.json", canonical_json(assessment))
        _write(stage, "questions.json", canonical_json({"questions": assessment["questions"],
                                                         "ai_boundary": assessment["ai_boundary"]}))
        _write(stage, "index.html", render_review(assessment).encode())
        _write(stage, "README.txt", _instructions(assessment).encode())
        _seal(stage, "project_review", assessment["provenance"])
    return assessment


def _instructions(assessment=None):
    scope = ""
    if assessment:
        scope = "WHAT THIS PACKET ESTABLISHES, AND WHAT IT DOES NOT\n" + "".join(
            f"  - {item['text']}\n" for item in assessment["scopes"]) + "\n"
        source = assessment["provenance"]
        scope += (f"Source commit: {source['commit'] or 'unavailable'}; working tree "
                  f"{ {True: 'MODIFIED', False: 'clean', None: 'unknown'}[source['worktree_dirty']] }.\n\n")
    return ("PROJECT 33 / OFFLINE EVIDENCE REVIEW\n\n" + scope +
            "Open index.html for the report. No server or network is required.\n"
            "From the original repository: python -m evidence verify PATH_TO_THIS_FOLDER\n"
            "Standalone: cd reviewer, then python -m evidence verify ..\n"
            "Python 3.11+; standard library only.\n\n"
            "For independent verification, use reviewer code from a trusted checkout.\n"
            "Compare manifest.sha256 against a digest received through a trusted channel.\n"
            "Use verify --expected-sha256 DIGEST to pin that reference. A changed manifest\n"
            "and a new digest can be created by anyone: hashes are not authentication.\n\n"
            "Contents: records/ (every record file as committed), artifacts/ (byte copies of\n"
            "cited files), assessment.json (evaluated record), questions.json (grounded answers),\n"
            "execution/ (attached test or reproduction records, if any), reviewer/ (verifier).\n\n"
            "FOR AUTOMATED OR AI REVIEWERS: interpret the record; do not rewrite it. Answers must\n"
            "cite assessment.json or records/. Never treat a model, test, hash, or clean dataset\n"
            "as a physical measurement, and never fill a missing value.\n\n"
            "This package checks files and record consistency, not scientific truth or hardware readiness.\n")


def build_audit(csv_path, output, *, origin="unknown", gap_ms=500):
    from .report import render_audit

    data = read_bytes(csv_path)
    audit = audit_bytes(data, origin=origin, gap_ms=gap_ms, keep_series=True)
    html = render_audit(audit)
    audit.pop("series")  # display-only; the CSV itself is the data
    with new_directory(output) as stage:
        _write(stage, "telemetry.csv", data)
        _write(stage, "audit.json", canonical_json(audit))
        _write(stage, "index.html", html.encode())
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
    R.keys(manifest, {"schema_version", "kind", "producer", "provenance", "files"}, (), "manifest")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise EvidenceError("Unsupported manifest schema_version")
    if manifest["kind"] not in KINDS:
        raise EvidenceError("Unknown manifest kind")
    if not isinstance(manifest["files"], list) or not manifest["files"] or len(manifest["files"]) > 5000:
        raise EvidenceError("Invalid manifest file list")
    seen = {"manifest.json", "manifest.sha256"}
    for item in manifest["files"]:
        R.keys(item, {"path", "bytes", "sha256"}, (), "manifest entry")
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
    required = {"index.html", "README.txt"} | KINDS[manifest["kind"]]
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
    return {"bundle_integrity": "verified", "manifest_sha256": actual, "file_count": len(manifest["files"]),
            "trusted_digest_checked": expected_sha256 is not None, "kind": manifest["kind"],
            "not_established": ["scientific validity", "physical performance", "flight readiness",
                                "authorship (a digest is not a signature)"]}


def _load_review(path):
    checked = verify_bundle(path)
    if checked["kind"] != "project_review":
        raise EvidenceError("Compare requires two project review bundles")
    manifest = load_json(read_bytes(Path(path) / "manifest.json"))
    return load_json(read_bytes(Path(path) / "assessment.json")), manifest


def compare_reviews(before, after):
    (old, old_manifest), (new, new_manifest) = _load_review(before), _load_review(after)
    old_artifacts = {a["path"]: a for a in old["artifacts"]}
    new_artifacts = {a["path"]: a for a in new["artifacts"]}
    changed = sorted(path for path in old_artifacts.keys() | new_artifacts.keys()
                     if (old_artifacts.get(path) or {}).get("sha256") != (new_artifacts.get(path) or {}).get("sha256"))
    fields = ("id", "class", "description", "derived_from", "status", "format", "columns", "min_rows")
    changed_records = sorted(path for path in old_artifacts.keys() & new_artifacts.keys()
                             if {k: old_artifacts[path].get(k) for k in fields}
                             != {k: new_artifacts[path].get(k) for k in fields})
    old_claims = {c["id"]: c for c in old["claims"]}
    new_claims = {c["id"]: c for c in new["claims"]}
    authored = ("title", "question", "statement", "status", "gate", "evidence", "historical", "requirements",
                "predictions", "assumptions", "limitations", "concerns", "measurement_needed")
    affected = {key for key in old_claims.keys() | new_claims.keys()
                if {k: (old_claims.get(key) or {}).get(k) for k in authored}
                != {k: (new_claims.get(key) or {}).get(k) for k in authored}}
    touched = set(changed) | set(changed_records)
    for review in (old, new):
        for claim in review["claims"]:
            if touched & set(claim["affected_by_changes"]):
                affected.add(claim["id"])
    requirement_changes = []
    old_req = {r["id"]: r for r in old["requirements"]}
    new_req = {r["id"]: r for r in new["requirements"]}
    for key in sorted(old_req.keys() | new_req.keys()):
        before_result = (old_req.get(key) or {}).get("result")
        after_result = (new_req.get(key) or {}).get("result")
        if before_result != after_result or (old_req.get(key) or {}).get("observed") != (new_req.get(key) or {}).get("observed"):
            requirement_changes.append({"requirement": key, "before": before_result, "after": after_result})
            affected.update((new_req.get(key) or old_req.get(key))["claims"])
    old_disc = {d["id"]: d for d in old["discrepancies"]}
    new_disc = {d["id"]: d for d in new["discrepancies"]}
    discrepancy_changes = sorted(key for key in old_disc.keys() | new_disc.keys() if old_disc.get(key) != new_disc.get(key))
    for key in discrepancy_changes:
        affected.update((new_disc.get(key) or old_disc.get(key))["claims"])
    context_changed = any(old[key] != new[key] for key in ("project", "scope", "limitations"))
    reviewer_files = [{item["path"]: item["sha256"] for item in manifest["files"] if item["path"].startswith("reviewer/")}
                      for manifest in (old_manifest, new_manifest)]
    reviewer_changed = reviewer_files[0] != reviewer_files[1]
    if context_changed or reviewer_changed:
        affected.update(old_claims.keys() | new_claims.keys())
    return {
        "changed_artifacts": changed, "changed_artifact_records": changed_records,
        "affected_claims": sorted(affected),
        "claim_status_changes": [{"claim": key, "before": (old_claims.get(key) or {}).get("status"),
                                  "after": (new_claims.get(key) or {}).get("status")}
                                 for key in sorted(old_claims.keys() | new_claims.keys())
                                 if (old_claims.get(key) or {}).get("status") != (new_claims.get(key) or {}).get("status")],
        "requirement_changes": requirement_changes, "discrepancy_changes": discrepancy_changes,
        "provenance_changed": old["provenance"] != new["provenance"],
        "review_context_changed": context_changed, "reviewer_changed": reviewer_changed,
        "meaning": "Changed evidence needs review; this is not a performance comparison.",
    }


def drift(bundle, root, catalog_path="evidence/catalog.json"):
    """Which files in the working tree differ from what a review packet recorded."""
    review, _ = _load_review(bundle)
    records = R.load(root, catalog_path)
    current = E.load_artifact_data(records)
    by_path = {item["path"]: key for key, item in records.artifacts.items()}
    changed, missing, removed = [], [], []
    for item in review["artifacts"]:
        key = by_path.get(item["path"])
        if key is None:
            removed.append(item["path"])
        elif current[key] is None:
            missing.append(item["path"])
        elif digest(current[key]) != item["sha256"]:
            changed.append(item["path"])
    added = sorted(set(by_path) - {item["path"] for item in review["artifacts"]})
    return {"bundle_commit": review["provenance"].get("commit"),
            "changed_since_bundle": sorted(changed), "missing_now": sorted(missing),
            "no_longer_cataloged": sorted(removed), "newly_cataloged": added,
            "impact": E.impact(records, sorted(changed + missing)),
            "meaning": "The packet no longer describes these files. Its conclusions about affected claims are stale."}
