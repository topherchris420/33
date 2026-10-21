"""Extract cached OpenRocket CP/CG samples without changing or fitting models.

A loaded simulation cache has no generating-geometry digest in this file.
Extracting it preserves simulated evidence; it does not verify the current model.
"""

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

COLUMNS = {"Time": ("time_s", "s"), "CP location": ("cp_m", "m"),
           "CG location": ("cg_m", "m"), "Stability margin calibers": ("margin_calibers", "calibers")}
UNIT_SOURCE = "https://openrocket.readthedocs.io/en/latest/dev_guide/codebase_walkthrough.html"


def summarize(rows):
    result = {}
    for column, unit in COLUMNS.values():
        values = [r[column] for r in rows if r[column] is not None]
        result[column] = {"unit": unit, "finite_samples": len(values), "missing_samples": len(rows) - len(values),
                          "min": min(values) if values else None, "max": max(values) if values else None}
    return result


def extract(path):
    path = Path(path)
    data = path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = [i for i in archive.infolist() if i.filename == "rocket.ork"]
        if len(members) != 1 or members[0].file_size > 32 * 1024 * 1024:
            raise ValueError("Expected exactly one rocket.ork XML member under 32 MiB")
        root = ET.fromstring(archive.read(members[0]))
    simulations = []
    for simulation in root.findall("./simulations/simulation"):
        branches = []
        for branch in simulation.findall("./flightdata/databranch"):
            types = branch.get("types", "").split(",")
            if len(set(types)) != len(types) or not set(COLUMNS).issubset(types):
                raise ValueError("Cached branch must have unique Time, CP, CG and stability columns")
            indices = {key: types.index(key) for key in COLUMNS}
            rows = []
            for point in branch.findall("datapoint"):
                values = (point.text or "").split(",")
                if len(values) != len(types):
                    raise ValueError("Cached datapoint column count mismatch")
                row = {}
                for name, index in indices.items():
                    value = float(values[index])
                    row[COLUMNS[name][0]] = value if math.isfinite(value) else None
                rows.append(row)
            if not rows:
                raise ValueError("Cached branch has no datapoints")
            times = [r["time_s"] for r in rows]
            if any(t is None for t in times) or times != sorted(times):
                raise ValueError("Cached timestamps must be finite and nondecreasing")
            ignition = [float(e.get("time")) for e in branch.findall("event") if e.get("type") == "ignition"]
            burnout = [float(e.get("time")) for e in branch.findall("event") if e.get("type") == "burnout"]
            # Multiple motor events need a configuration-aware interpretation.
            window = [ignition[0], burnout[0]] if len(ignition) == len(burnout) == 1 else None
            if window and (not all(math.isfinite(t) for t in window) or window[1] < window[0]):
                raise ValueError("Invalid ignition/burnout times")
            burn_rows = [r for r in rows if window[0] <= r["time_s"] <= window[1]] if window else []
            branches.append({"name": branch.get("name"), "samples": rows, "summary": summarize(rows),
                             "single_motor_burn_window_s": window,
                             "burn_summary": summarize(burn_rows) if burn_rows else None})
        simulations.append({"name": simulation.findtext("name"), "status_as_saved": simulation.get("status"),
                            "simulator": simulation.findtext("simulator"), "calculator": simulation.findtext("calculator"),
                            "config_id": simulation.findtext("./conditions/configid"), "branches": branches})
    if not any(s["branches"] for s in simulations):
        raise ValueError("No cached CP/CG trajectory is available")
    return {"schema": "project33.openrocket_cache/1", "evidence_class": "simulated", "source_file": path.name,
            "source_sha256": hashlib.sha256(data).hexdigest(), "creator_as_saved": root.get("creator"),
            "format_version": root.get("version"), "unit_convention_source": UNIT_SOURCE,
            "generating_geometry_sha256": None, "simulations": simulations,
            "limitations": ["Cached simulation only; OpenRocket was not run by this extraction.",
                            "The cache cannot establish which geometry revision generated it.",
                            "Nonfinite serialized values remain null, never zero or interpolated.",
                            "No model is fitted or replaced; different configurations require engineering reconciliation.",
                            "Trajectory extrema are not restricted to the burn; inspect burn_summary separately.",
                            "Only a single ignition and burnout pair define an automatic burn window."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ork", type=Path, required=True)
    parser.add_argument("--emit", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = extract(args.ork)
        args.emit.parent.mkdir(parents=True, exist_ok=True)
        with args.emit.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, indent=2, allow_nan=False)
            handle.write("\n")
        print(json.dumps({"output": str(args.emit), "evidence_class": "simulated",
                          "source_sha256": result["source_sha256"]}))
        return 0
    except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile) as exc:
        parser.exit(2, f"openrocket_reference: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
