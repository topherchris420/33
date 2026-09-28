"""Operations that change or re-derive the record: review snapshots and model reproduction.

A snapshot records what a claim looked like when it was last looked at. Tooling
may record a 'snapshot'; only a person who names themselves records a 'human'
review. Reproduction re-runs model recipes into a temporary directory and
compares values with the committed artifacts; it never overwrites them.
"""

from datetime import date as _date
import math
import platform
from pathlib import Path
import subprocess
import sys
import tempfile

from .common import EvidenceError, canonical_json, csv_rows, digest, load_json, read_bytes, safe_path
from . import evaluate as E
from . import records as R


def snapshot(root, claim_ids, note, *, catalog_path="evidence/catalog.json", reviewer=None,
             independent=False, today=None):
    """Record the current state of the named claims in reviews.json."""
    records = R.load(root, catalog_path)
    if "reviews" not in records.declared:
        raise EvidenceError("This catalog does not keep a reviews record")
    if not isinstance(note, str) or not note.strip():
        raise EvidenceError("A snapshot needs a note saying why it was recorded")
    if independent and not reviewer:
        raise EvidenceError("Only a named human reviewer can record an independent review")
    unknown = sorted(set(claim_ids) - set(records.claims))
    if unknown or not claim_ids:
        raise EvidenceError(f"Unknown or missing claim IDs: {unknown}")
    data = E.load_artifact_data(records)
    missing = [key for key, value in data.items() if value is None]
    if missing:
        raise EvidenceError(f"Cannot snapshot while artifacts are missing: {missing}")
    path = records.declared["reviews"]
    document = records.docs["reviews"]
    stamp = today or _date.today().isoformat()
    for claim_id in sorted(set(claim_ids)):
        entry = {
            "kind": "human" if reviewer else "snapshot",
            "recorded": stamp,
            "recorded_by": reviewer.strip() if reviewer else "tooling snapshot (no human review)",
            "note": note.strip(),
            **E.review_snapshot(records.claims[claim_id], records, data),
        }
        if independent:
            entry["independent"] = True
        previous = document["reviews"].get(claim_id)
        history = []
        if previous:
            history = [previous["current"]] + previous["history"]
        document["reviews"][claim_id] = {"current": entry, "history": history}
    document["reviews"] = dict(sorted(document["reviews"].items()))
    safe_path(records.root, path).write_bytes(canonical_json(document))
    R.load(root, catalog_path)  # the written record must itself validate
    return {"recorded": sorted(set(claim_ids)), "kind": "human" if reviewer else "snapshot",
            "file": path}


# --------------------------------------------------------------------------- reproduction

def _same(a, b, where="$"):
    """First difference between two parsed values, or None. Floats compare with a tight tolerance."""
    if isinstance(a, bool) or isinstance(b, bool):
        return None if a is b else f"{where}: {a!r} != {b!r}"
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12):
            return None
        return f"{where}: {a!r} != {b!r}"
    if type(a) is not type(b):
        return f"{where}: type {type(a).__name__} != {type(b).__name__}"
    if isinstance(a, dict):
        if set(a) != set(b):
            return f"{where}: keys differ {sorted(set(a) ^ set(b))}"
        for key in sorted(a):
            found = _same(a[key], b[key], f"{where}/{key}")
            if found:
                return found
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{where}: length {len(a)} != {len(b)}"
        for index, (left, right) in enumerate(zip(a, b)):
            found = _same(left, right, f"{where}[{index}]")
            if found:
                return found
        return None
    return None if a == b else f"{where}: {a!r} != {b!r}"


def _cell(value):
    try:
        number = float(value)
    except ValueError:
        return value
    return number if math.isfinite(number) else value


def compare_values(fmt, committed, produced):
    if fmt == "json":
        return _same(load_json(committed), load_json(produced))
    if fmt == "csv":
        left = [row for row in csv_rows(committed)]
        right = [row for row in csv_rows(produced)]
        if left[0] != right[0]:
            return f"columns {left[0]} != {right[0]}"
        rows_a = [[_cell(v) for v in row.values()] for _, row in left[1:]]
        rows_b = [[_cell(v) for v in row.values()] for _, row in right[1:]]
        return _same(rows_a, rows_b, "rows")
    return None if committed == produced else "bytes differ"


def reproduce(root, *, catalog_path="evidence/catalog.json", only=None, python=None, timeout=900):
    records = R.load(root, catalog_path)
    recipes = records.catalog.get("recipes", [])
    by_output = {name: recipe["id"] for recipe in recipes for name in recipe["outputs"].values()}
    selected = {recipe["id"] for recipe in recipes} if not only else set(only)
    unknown = selected - {recipe["id"] for recipe in recipes}
    if unknown:
        raise EvidenceError(f"Unknown recipes: {sorted(unknown)}")
    # Pull in recipes whose outputs a selected command reads from the shared output directory.
    changed = True
    while changed:
        changed = False
        for recipe in recipes:
            if recipe["id"] in selected:
                for arg in recipe["command"]:
                    if arg.startswith("{out}/") and arg[6:] in by_output and by_output[arg[6:]] != recipe["id"] \
                            and by_output[arg[6:]] not in selected and arg[6:] not in recipe["outputs"].values():
                        selected.add(by_output[arg[6:]])
                        changed = True
    python = python or sys.executable
    results = []
    with tempfile.TemporaryDirectory(prefix="evidence-reproduce-") as out:
        for recipe in recipes:
            if recipe["id"] not in selected:
                continue
            command = [arg.replace("{python}", python).replace("{out}", out) for arg in recipe["command"]]
            try:
                run = subprocess.run(command, cwd=records.root, capture_output=True, text=True, timeout=timeout)
                failure = None if run.returncode == 0 else (run.stderr.strip().splitlines() or ["no output"])[-1]
            except (OSError, subprocess.SubprocessError) as exc:
                failure = str(exc)
            for artifact_id, name in sorted(recipe["outputs"].items()):
                item = records.artifacts[artifact_id]
                committed = read_bytes(safe_path(records.root, item["path"]))
                produced_path = Path(out) / name
                row = {"artifact": artifact_id, "path": item["path"], "recipe": recipe["id"],
                       "committed_sha256": digest(committed), "produced_sha256": None}
                if failure:
                    row.update(result="failed", detail=failure[:500])
                elif not produced_path.is_file():
                    row.update(result="missing", detail=f"recipe did not write {name}")
                else:
                    produced = read_bytes(produced_path)
                    row["produced_sha256"] = digest(produced)
                    difference = compare_values(item["format"], committed, produced)
                    row.update(result="differs" if difference else "reproduced", detail=difference)
                results.append(row)
    return {"schema": "project33.reproduction/1", "python": platform.python_version(),
            "compared": "parsed values (JSON structure, CSV cells) with relative tolerance 1e-9; rendered images excluded",
            "results": results}


def validate_reproduction(document):
    R.keys(document, {"schema", "python", "compared", "results"}, (), "reproduction record")
    if document["schema"] != "project33.reproduction/1" or not isinstance(document["results"], list):
        raise EvidenceError("Unsupported reproduction record")
    for row in document["results"]:
        R.keys(row, {"artifact", "path", "recipe", "committed_sha256", "produced_sha256", "result", "detail"},
               (), "reproduction result")
        if row["result"] not in ("reproduced", "differs", "missing", "failed"):
            raise EvidenceError("Unknown reproduction result")
    return document
