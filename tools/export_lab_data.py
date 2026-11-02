"""Export read-only data views for the Living Engineering Laboratory (``lab/``).

Everything the laboratory shows about Project 33 is read from committed sources,
either directly (the lab fetches ``evidence/*.json``, ``protocol/*.json`` and
``docs/EVIDENCE/*`` as published files) or through the derived views written
here. A derived view is never a new source: the evidence record stays canonical,
and every output lists the exact input bytes (SHA-256) it was produced from.

    python tools/export_lab_data.py           # regenerate the stdlib-derived views
    python tools/export_lab_data.py --check   # fail if any view or recorded digest is stale

CAD-derived views (the STEP mesh and the Fusion 360 archive inventory) need
cadquery and zstandard and are produced by ``tools/cad_to_web.py``. ``--check``
verifies those by digest only, so it runs on the standard library alone.

This tool reads files and writes JSON. It opens no network connection and has no
path to firmware, hardware, or any command interface.
"""

import argparse
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("lab/data")
SCHEMA = "project33.lab"

ORK_CURRENT = "Simulation/Folding Stabilized Rocket.ork"
ORK_PRE_RETUNE = "evidence/archive/C5_openrocket_pre_retune.ork.xml"
NACA_SOURCE = "CAD Files/naca_fin_generator.py"
CAD_MANIFEST = OUT / "cad" / "manifest.json"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def dump(value):
    return (json.dumps(value, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


# ---------------------------------------------------------------------------
# Evidence: the evaluated record, exactly as the Observatory computes it.
# ---------------------------------------------------------------------------

def evidence_view(root):
    sys.path.insert(0, str(root))
    try:
        from evidence.bundle import load_assessment
        from evidence import vocabulary as V
    finally:
        sys.path.pop(0)
    records, _data, assessment, _ = load_assessment(root)
    view = {key: value for key, value in assessment.items() if key != "provenance"}
    # Scopes describe what a review packet build checked; the lab is not a review packet.
    view.pop("scopes", None)
    gates = json.loads((root / "evidence/safety_gates.json").read_text(encoding="utf-8"))
    reviews = json.loads((root / "evidence/reviews.json").read_text(encoding="utf-8"))
    view["safety_gates"] = gates["gates"]
    view["reviews"] = reviews["reviews"]
    view["discrepancy_vocabulary"] = {
        "kinds": V.DISCREPANCY_KINDS, "statuses": V.DISCREPANCY_STATUSES, "effects": V.DISCREPANCY_EFFECTS,
    }
    inputs = sorted({str(Path(p).relative_to(root).as_posix()) if Path(p).is_absolute() else p
                     for p, _ in records.raw.values()} | {"evidence/safety_gates.json", "evidence/reviews.json"})
    view["lab_note"] = ("Derived view of `python -m evidence` assessment for display. It carries no authority: "
                        "statuses, support levels, and requirement results are computed by evidence/assess.py "
                        "from the committed record. Provenance (commit, worktree state) is omitted so the view "
                        "depends only on committed bytes.")
    return view, inputs + [a["path"] for a in assessment["artifacts"]]


# ---------------------------------------------------------------------------
# OpenRocket: parametric component geometry with source paths and stations.
# ---------------------------------------------------------------------------

BODY = {"nosecone", "bodytube", "transition"}
ATTACHED = {"trapezoidfinset", "ellipticalfinset", "freeformfinset", "innertube", "launchlug",
            "centeringring", "bulkhead", "engineblock", "masscomponent", "parachute", "shockcord",
            "streamer", "tubecoupler", "railbutton"}
NUMERIC = {"length", "thickness", "radius", "aftradius", "foreradius", "aftshoulderradius",
           "aftshoulderlength", "rootchord", "tipchord", "sweeplength", "height", "fincount",
           "instancecount", "angleoffset", "rotation", "cant", "filletradius", "overridemass",
           "overridecg", "diameter", "delay", "radiusoffset", "shapeparameter", "overhang"}
TEXT = {"name", "id", "shape", "material", "crosssection", "finish", "designation", "manufacturer",
        "type", "overridesubcomponentsmass", "overridesubcomponentscg", "ignitionevent"}


def _axial(element):
    node = element.find("axialoffset")
    if node is None:
        node = element.find("position")
    if node is None:
        return "top", 0.0
    method = node.get("method") or node.get("type") or "top"
    return method, float(node.text)


def _fields(element, path):
    fields = {}
    for child in element:
        if child.tag in NUMERIC and child.text is not None:
            try:
                value = float(child.text)
            except ValueError:
                continue
            fields[child.tag] = {"value": value, "path": f"{path}/{child.tag}", "text": child.text}
        elif child.tag in TEXT and child.text is not None:
            fields[child.tag] = {"value": child.text, "path": f"{path}/{child.tag}"}
        elif child.tag in ("axialoffset", "position"):
            fields[child.tag] = {"value": float(child.text), "path": f"{path}/{child.tag}",
                                 "method": child.get("method") or child.get("type"), "text": child.text}
    return fields


def _num(fields, key, default=None):
    item = fields.get(key)
    return default if item is None else item["value"]


def _component_length(tag, fields):
    if tag.endswith("finset"):
        return _num(fields, "rootchord", 0.0)
    return _num(fields, "length", 0.0)


def _place(method, offset, length, parent_start, parent_length):
    """OpenRocket axial-method semantics: start of a component measured from the nose tip."""
    if method == "absolute":
        return offset
    if method == "top":
        return parent_start + offset
    if method == "middle":
        return parent_start + (parent_length - length) / 2.0 + offset
    if method == "bottom":
        return parent_start + (parent_length - length) + offset
    raise ValueError(f"unsupported axial method {method!r}")


def _walk(element, path, parent_start, parent_length, out, parent_id=None):
    subs = element.find("subcomponents")
    if subs is None:
        return
    cursor = parent_start
    counters = {}
    for child in subs:
        counters[child.tag] = counters.get(child.tag, 0) + 1
        child_path = f"{path}/subcomponents/{child.tag}[{counters[child.tag]}]"
        fields = _fields(child, child_path)
        length = _component_length(child.tag, fields)
        if child.tag == "stage":
            entry = {"kind": "stage", "path": child_path, "fields": fields, "parent": parent_id,
                     "id": _num(fields, "id")}
            out.append(entry)
            before = len(out)
            _walk(child, child_path, cursor, 0.0, out, entry["id"])
            body = [c for c in out[before:] if c["kind"] in BODY and c["parent"] == entry["id"]]
            end = max((c["x_end_m"] for c in body), default=cursor)
            entry["x_start_m"], entry["x_end_m"] = cursor, end
            cursor = end
            continue
        if child.tag in BODY:
            method, offset = "after", 0.0
            start = cursor
            cursor = start + length
        elif child.tag in ATTACHED:
            method, offset = _axial(child)
            start = _place(method, offset, length, parent_start, parent_length)
        else:
            continue
        entry = {"kind": child.tag, "path": child_path, "fields": fields, "parent": parent_id,
                 "id": _num(fields, "id"), "axial_method": method, "axial_offset_m": offset,
                 "x_start_m": round(start, 9), "x_end_m": round(start + length, 9)}
        if child.tag == "bodytube":
            mount = child.find("motormount")
            if mount is not None:
                motor = mount.find("motor")
                overhang = float(mount.findtext("overhang", "0") or 0)
                if motor is not None:
                    mpath = f"{child_path}/motormount/motor"
                    mfields = _fields(motor, mpath)
                    mlen = _num(mfields, "length", 0.0)
                    end = start + length + overhang
                    entry["motor"] = {"fields": mfields, "path": mpath, "overhang_m": overhang,
                                      "x_start_m": round(end - mlen, 9), "x_end_m": round(end, 9)}
        out.append(entry)
        _walk(child, child_path, start, length, out, entry["id"])


def parse_ork(xml_bytes, label):
    root = ET.fromstring(xml_bytes)
    rocket = root.find("rocket")
    components = []
    _walk(rocket, "openrocket/rocket", 0.0, 0.0, components, _num(_fields(rocket, ""), "id"))
    body = [c for c in components if c["kind"] in BODY]
    return {
        "label": label,
        "creator": root.get("creator"),
        "format_version": root.get("version"),
        "rocket_name": rocket.findtext("name"),
        "units": {"length": "m", "mass": "kg", "angle": "deg"},
        "overall_length_m": round(max(c["x_end_m"] for c in body), 9),
        "reference_diameter_m": round(2 * max(_num(c["fields"], "radius", 0.0) or
                                              _num(c["fields"], "aftradius", 0.0) for c in body), 9),
        "components": components,
    }


def openrocket_view(root):
    raw = (root / ORK_CURRENT).read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = [n for n in archive.namelist() if n.endswith(".ork")] or archive.namelist()
        inner = archive.read(names[0])
    prior = (root / ORK_PRE_RETUNE).read_bytes()
    stability = json.loads((root / "docs/EVIDENCE/C5_static_margin_inputs.json").read_text(encoding="utf-8"))
    current = parse_ork(inner, "current")
    current["source"] = {"path": ORK_CURRENT, "sha256": sha256(raw), "inner_file": names[0],
                         "inner_sha256": sha256(inner)}
    previous = parse_ork(prior, "pre_retune")
    previous["source"] = {"path": ORK_PRE_RETUNE, "sha256": sha256(prior)}
    aft = [c for c in current["components"] if c["kind"] == "trapezoidfinset"]
    largest = max(aft, key=lambda c: _num(c["fields"], "height", 0.0))
    script_xf = stability["geometry"]["X_f"]
    observations = [{
        "id": "LAB-OBS-1",
        "status": "candidate for human review; not entered in the discrepancy register",
        "title": "Fin root leading-edge station: static-margin parser versus OpenRocket axial semantics",
        "detail": ("The largest-span fin set is positioned with method "
                   f"'{largest['axial_method']}' and offset {largest['axial_offset_m']} m in its parent tube. "
                   "OpenRocket places a 'bottom'-referenced component so that its aft end aligns with the "
                   "parent's aft end, which puts the root leading edge at "
                   f"{largest['x_start_m']:.3f} m from the nose tip. Simulation/static_margin.py reads the "
                   "<position> value without its type attribute and records X_f = "
                   f"{script_xf} m in docs/EVIDENCE/C5_static_margin_inputs.json."),
        "values_m": {"ork_semantics": largest["x_start_m"], "static_margin_inputs_X_f": script_xf,
                     "difference": round(largest["x_start_m"] - script_xf, 9)},
        "not_computed": "The effect on either centre-of-pressure formulation is not computed here; "
                        "doing so would be a third model. It needs a reviewed model change.",
        "sources": [ORK_CURRENT, "Simulation/static_margin.py", "docs/EVIDENCE/C5_static_margin_inputs.json"],
        "related": ["C5", "D-006", "D-008"],
    }]
    return {"current": current, "pre_retune": previous, "lab_observations": observations,
            "semantics_note": ("Stations are distances from the nose tip. Body components stack in document "
                               "order; attached components use their axial method (top, middle, bottom, "
                               "absolute) relative to the parent, as OpenRocket defines them. Override masses "
                               "and materials are simulation inputs, not measurements.")}, \
        [ORK_CURRENT, ORK_PRE_RETUNE, "docs/EVIDENCE/C5_static_margin_inputs.json"]


# ---------------------------------------------------------------------------
# NACA 0012 profile from the repository's tested generator (C3).
# ---------------------------------------------------------------------------

def naca_view(root):
    spec = importlib.util.spec_from_file_location("naca_fin_generator", root / NACA_SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    m, p, t, chord = 0.0, 0.0, 0.12, 0.060
    upper, lower = module.naca_4digit_coordinates(m, p, t, chord)
    thickness = max(u[1] - l[1] for u, l in zip(upper, lower))
    return {
        "generator": NACA_SOURCE,
        "function": "naca_4digit_coordinates(m=0.0, p=0.0, t=0.12, c=0.060, num_points=50)",
        "units": {"x": "mm", "y": "mm"},
        "designation": "NACA 0012",
        "chord_mm": chord * 1000,
        "max_thickness_mm_sampled": round(thickness, 6),
        "upper": [[round(x, 6), round(y, 6)] for x, y, _ in upper],
        "lower": [[round(x, 6), round(y, 6)] for x, y, _ in lower],
        "span": "NOT SPECIFIED — the generator draws a 2D profile; export_step's span=60.0 is a function "
                "default, not a recorded design value.",
        "claim": "C3",
        "limitation": "Geometry says nothing about aerodynamic performance or where the profile is used.",
    }, [NACA_SOURCE]


# ---------------------------------------------------------------------------
# The repository's intentionally flawed synthetic telemetry fixture and its audit.
# ---------------------------------------------------------------------------

def telemetry_view(root):
    sys.path.insert(0, str(root))
    try:
        from evidence.__main__ import demo
    finally:
        sys.path.pop(0)
    with tempfile.TemporaryDirectory() as tmp:
        audit = demo(Path(tmp) / "demo")
        csv_text = (Path(tmp) / "demo" / "synthetic-telemetry.csv").read_text(encoding="utf-8")
    return {
        "origin": "SYNTHETIC SOFTWARE FIXTURE — NO HARDWARE DATA",
        "generator": "evidence/__main__.py demo() via python -m evidence demo",
        "purpose": "An intentionally flawed capture that exercises the telemetry audit.",
        "csv": csv_text,
        "audit": audit,
    }, ["evidence/__main__.py", "evidence/telemetry.py", "evidence/bundle.py"]


VIEWS = {
    "evidence.json": evidence_view,
    "openrocket.json": openrocket_view,
    "naca0012.json": naca_view,
    "telemetry_fixture.json": telemetry_view,
}


def build(root):
    outputs, inputs_by_view = {}, {}
    for name, maker in VIEWS.items():
        value, inputs = maker(root)
        digests = {}
        for rel in sorted(set(inputs)):
            path = root / rel
            if path.is_file():
                digests[rel] = sha256(path.read_bytes())
        value = {"schema": f"{SCHEMA}.{name[:-5]}/1", "generated_by": "tools/export_lab_data.py",
                 "inputs": digests, **value}
        outputs[name] = dump(value)
        inputs_by_view[name] = digests
    return outputs


def cad_entries(root):
    """Verify the CAD manifest written by tools/cad_to_web.py using digests only."""
    path = root / CAD_MANIFEST
    if not path.exists():
        return [f"{CAD_MANIFEST} is missing; run tools/cad_to_web.py"], None
    manifest = json.loads(path.read_text(encoding="utf-8"))
    problems = []
    for item in manifest["outputs"]:
        for rel, digest in item["inputs"].items():
            source = root / rel
            if not source.exists():
                problems.append(f"{item['path']}: input {rel} is missing")
            elif sha256(source.read_bytes()) != digest:
                problems.append(f"{item['path']}: input {rel} changed; rerun tools/cad_to_web.py")
        target = root / item["path"]
        if not target.exists():
            problems.append(f"{item['path']} is missing")
        elif sha256(target.read_bytes()) != item["sha256"]:
            problems.append(f"{item['path']} does not match its recorded digest")
    return problems, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true", help="Compare instead of writing")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    outputs = build(root)
    problems, _ = cad_entries(root)
    if args.check:
        for name, data in outputs.items():
            path = root / OUT / name
            if not path.exists() or path.read_bytes() != data:
                problems.append(f"{OUT / name} is stale; run python tools/export_lab_data.py")
        if problems:
            print("\n".join(problems))
            return 1
        print(f"lab data current: {len(outputs)} derived views and CAD manifest verified")
        return 0
    (root / OUT).mkdir(parents=True, exist_ok=True)
    for name, data in outputs.items():
        (root / OUT / name).write_bytes(data)
    for problem in problems:
        print("warning:", problem)
    print(f"wrote {len(outputs)} lab data views to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
