"""Translate committed CAD sources into web views for the laboratory, with provenance.

    python tools/cad_to_web.py

Writes ``lab/data/cad/`` and ``lab/data/cad/manifest.json``. Every output records
the SHA-256 of the exact source bytes it came from, so
``python tools/export_lab_data.py --check`` can detect a stale view with the
standard library alone.

Sources and what is (and is not) produced:

* ``CAD Files/Four Bar Linkage.step`` (OpenCascade STEP AP214). Tessellated per
  solid with OCP (installed with cadquery, already a model dependency), keeping
  the STEP's own part names and colours, its B-rep edges for blueprint mode, and
  cylindrical-face axes so pin spacing is measured from the geometry itself.
* ``CAD Files/*.f3z`` (Fusion 360 archives). Fusion stores bodies as Autodesk
  ShapeManager B-rep (``.smb``/``.smbh``) inside zstd-compressed members. No
  open-source translator for that format is used here, so the archives are
  inventoried, not converted: component names, design versions, embedded preview
  images, and B-rep statistics read with ``tools/sab_inventory.py``. Converting
  them needs a STEP export from Fusion 360 (File > Export > STEP) placed in
  ``CAD Files/exports/``; this tool translates any STEP found there the same way
  as the four-bar file.

Needs: cadquery (for OCP) and zstandard. Neither is required by the lab itself.
"""

import argparse
import hashlib
import json
import math
import struct
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("lab/data/cad")
STEP_SOURCES = [("four_bar", "CAD Files/Four Bar Linkage.step")]
EXPORTS_DIR = Path("CAD Files/exports")
ARCHIVES = ["CAD Files/Folding Rocket.f3z", "CAD Files/Launcher Platform.f3z", "CAD Files/Rocket Nozzle.f3z"]
LINEAR_DEFLECTION_MM = 0.01
ANGULAR_DEFLECTION_RAD = 0.15


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def dump(value):
    return (json.dumps(value, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


# ---------------------------------------------------------------------------
# STEP -> mesh, edges, and measured features (OCP / OpenCascade)
# ---------------------------------------------------------------------------

def step_view(path):
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TDocStd import TDocStd_Document
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorType, XCAFDoc_ColorTool
    from OCP.TDF import TDF_LabelSequence
    from OCP.TDataStd import TDataStd_Name
    from OCP.Quantity import Quantity_Color
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_SOLID, TopAbs_REVERSED
    from OCP.TopoDS import TopoDS
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location
    from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
    from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Line
    from OCP.GCPnts import GCPnts_QuasiUniformDeflection
    from OCP.BRepBndLib import BRepBndLib
    from OCP.Bnd import Bnd_Box
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    from OCP.IFSelect import IFSelect_RetDone

    doc = TDocStd_Document(TCollection_ExtendedString("doc"))
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.SetColorMode(True)
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise RuntimeError(f"could not read {path}")
    reader.Transfer(doc)
    shapes = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    colors = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())

    def label_name(label):
        attr = TDataStd_Name()
        if label.FindAttribute(TDataStd_Name.GetID_s(), attr):
            return attr.Get().ToExtString()
        return None

    def label_color(label, shape):
        color = Quantity_Color()
        for kind in (XCAFDoc_ColorType.XCAFDoc_ColorSurf, XCAFDoc_ColorType.XCAFDoc_ColorGen):
            if XCAFDoc_ColorTool.GetColor_s(label, kind, color) or colors.GetColor(shape, kind, color):
                return [round(color.Red(), 4), round(color.Green(), 4), round(color.Blue(), 4)]
        return None

    parts = []

    def visit(label, location, chain):
        shape = shapes.GetShape_s(label)
        name = label_name(label)
        if shapes.IsReference_s(label):
            ref = TDF_LabelSequence()
            target = type(label)()
            shapes.GetReferredShape_s(label, target)
            loc = location.Multiplied(shapes.GetLocation_s(label))
            visit_children(target, loc, chain + [name or "instance"], name)
            return
        visit_children(label, location, chain, name)

    def visit_children(label, location, chain, instance_name):
        if shapes.IsAssembly_s(label):
            children = TDF_LabelSequence()
            shapes.GetComponents_s(label, children)
            for i in range(1, children.Length() + 1):
                visit(children.Value(i), location, chain)
            return
        shape = shapes.GetShape_s(label)
        explorer = TopExp_Explorer(shape, TopAbs_SOLID)
        while explorer.More():
            solid = explorer.Current().Located(location)
            parts.append({"name": instance_name or label_name(label) or f"solid_{len(parts) + 1}",
                          "shape": solid, "color": label_color(label, shape), "chain": chain})
            explorer.Next()

    roots = TDF_LabelSequence()
    shapes.GetFreeShapes(roots)
    identity = TopLoc_Location()
    for i in range(1, roots.Length() + 1):
        visit(roots.Value(i), identity, [])

    out_parts = []
    for part in parts:
        shape = part["shape"]
        BRepMesh_IncrementalMesh(shape, LINEAR_DEFLECTION_MM, False, ANGULAR_DEFLECTION_RAD, True)
        positions, indices = [], []
        explorer = TopExp_Explorer(shape, TopAbs_FACE)
        while explorer.More():
            face = TopoDS.Face_s(explorer.Current())
            loc = TopLoc_Location()
            tri = BRep_Tool.Triangulation_s(face, loc)
            if tri is not None:
                trsf = loc.Transformation()
                base = len(positions) // 3
                for n in range(1, tri.NbNodes() + 1):
                    p = tri.Node(n).Transformed(trsf)
                    positions += [round(p.X(), 5), round(p.Y(), 5), round(p.Z(), 5)]
                reverse = face.Orientation() == TopAbs_REVERSED
                for t in range(1, tri.NbTriangles() + 1):
                    a, b, c = tri.Triangle(t).Get()
                    if reverse:
                        b, c = c, b
                    indices += [base + a - 1, base + b - 1, base + c - 1]
            explorer.Next()
        edges = []
        explorer = TopExp_Explorer(shape, TopAbs_EDGE)
        seen = set()
        while explorer.More():
            edge = TopoDS.Edge_s(explorer.Current())
            key = edge.HashCode(1 << 30) if hasattr(edge, "HashCode") else id(edge)
            explorer.Next()
            if BRep_Tool.Degenerated_s(edge):
                continue
            curve = BRepAdaptor_Curve(edge)
            sampler = GCPnts_QuasiUniformDeflection(curve, LINEAR_DEFLECTION_MM)
            pts = []
            if sampler.IsDone():
                for k in range(1, sampler.NbPoints() + 1):
                    p = sampler.Value(k)
                    pts += [round(p.X(), 5), round(p.Y(), 5), round(p.Z(), 5)]
            signature = tuple(pts)
            if signature in seen or not pts:
                continue
            seen.add(signature)
            edges.append({"type": "line" if curve.GetType() == GeomAbs_Line else "curve", "points": pts})
        # Cylindrical faces: hole axes and radii, measured from the B-rep.
        holes = []
        explorer = TopExp_Explorer(shape, TopAbs_FACE)
        while explorer.More():
            face = TopoDS.Face_s(explorer.Current())
            surface = BRepAdaptor_Surface(face)
            if surface.GetType() == GeomAbs_Cylinder:
                cyl = surface.Cylinder()
                axis = cyl.Axis()
                loc, d = axis.Location(), axis.Direction()
                holes.append({"axis_point": [round(loc.X(), 5), round(loc.Y(), 5), round(loc.Z(), 5)],
                              "axis_direction": [round(d.X(), 5), round(d.Y(), 5), round(d.Z(), 5)],
                              "radius_mm": round(cyl.Radius(), 6)})
            explorer.Next()
        unique = []
        for h in holes:
            if not any(math.dist(h["axis_point"][:2], u["axis_point"][:2]) < 1e-6 and
                       abs(h["radius_mm"] - u["radius_mm"]) < 1e-9 for u in unique):
                unique.append(h)
        box = Bnd_Box()
        BRepBndLib.Add_s(shape, box)
        xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
        props = GProp_GProps()
        BRepGProp.VolumeProperties_s(shape, props)
        spacing = None
        if len(unique) == 2:
            spacing = round(math.dist(unique[0]["axis_point"], unique[1]["axis_point"]), 6)
        out_parts.append({
            "name": part["name"], "color": part["color"], "chain": part["chain"],
            "bbox_mm": [round(v, 5) for v in (xmin, ymin, zmin, xmax, ymax, zmax)],
            "volume_mm3": round(props.Mass(), 4),
            "cylindrical_features": unique,
            "pin_spacing_mm_measured": spacing,
            "triangles": len(indices) // 3,
            "positions": positions, "indices": indices, "edges": edges,
        })
    return out_parts


# ---------------------------------------------------------------------------
# Fusion 360 archive inventory (no geometry translation)
# ---------------------------------------------------------------------------

def read_member(path_bytes, info):
    """Read one zip member, supporting zstd (method 93) as used by Fusion 360."""
    import zlib
    offset = info.header_offset
    name_len, extra_len = struct.unpack_from("<HH", path_bytes, offset + 26)
    start = offset + 30 + name_len + extra_len
    data = path_bytes[start:start + info.compress_size]
    if info.compress_type == 0:
        return data
    if info.compress_type == 8:
        return zlib.decompress(data, -15)
    if info.compress_type == 93:
        import zstandard
        return zstandard.ZstdDecompressor().decompress(data, max_output_size=info.file_size)
    raise ValueError(f"unsupported compression {info.compress_type}")


def archive_view(root, rel, out_dir):
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        import sab_inventory
    finally:
        sys.path.pop(0)
    raw = (root / rel).read_bytes()
    outer = zipfile.ZipFile(__import__("io").BytesIO(raw))
    description = json.loads(outer.read("DesignDescription.json"))
    manifest = json.loads(outer.read("Manifest.json"))
    designs = []
    previews = []
    stem = Path(rel).stem.lower().replace(" ", "-")
    for graph in description["designDescription"]["designGraphs"]:
        for obj in graph["designObjects"]:
            member = obj["relativePath"]
            inner_bytes = outer.read(member)
            inner = zipfile.ZipFile(__import__("io").BytesIO(inner_bytes))
            blobs = {"smb": 0, "smbh": 0}
            stats = {"bodies": 0, "faces": 0, "edges": 0, "surface_types": {}}
            preview_path = None
            for info in inner.infolist():
                name = info.filename
                if name.endswith("/"):
                    continue
                if "/Breps.BlobParts/" in name and name.startswith("FusionAssetName[Active]/"):
                    kind = name.rsplit(".", 1)[-1]
                    blobs[kind] = blobs.get(kind, 0) + 1
                    if kind == "smbh":
                        summary = sab_inventory.summarize(read_member(inner_bytes, info))
                        stats["bodies"] += summary["bodies"]
                        stats["faces"] += summary["faces"]
                        stats["edges"] += summary["edges"]
                        for key, count in summary["surface_types"].items():
                            stats["surface_types"][key] = stats["surface_types"].get(key, 0) + count
                elif name == "FusionAssetName[Active]/Previews/small.png":
                    png = read_member(inner_bytes, info)
                    preview_path = (out_dir / f"{stem}-{obj['id']}.png")
                    previews.append((preview_path, png, member))
            stats["surface_types"] = dict(sorted(stats["surface_types"].items()))
            designs.append({
                "id": obj["id"], "member": member, "name": obj["friendlyName"],
                "version": obj["version"], "created": obj.get("createdAt"),
                "description": obj["metadata"].get("description"),
                "is_root": member == manifest.get("root"),
                "brep_blobs": blobs, "current_state_statistics": stats,
                "preview": preview_path.as_posix() if preview_path else None,
            })
    designs.sort(key=lambda d: (not d["is_root"], d["name"], d["id"]))
    return {
        "path": rel, "sha256": sha256(raw), "bytes": len(raw), "root_member": manifest.get("root"),
        "designs": designs,
        "translation": {
            "status": "NOT TRANSLATED",
            "reason": ("Bodies are Autodesk ShapeManager B-rep (ASM 231) in zstd-compressed members. "
                       "This repository has no reviewed translator for that format, and the archive's "
                       "occurrence placements live in proprietary design streams. Displaying a partial "
                       "or unplaced translation would imply an assembly the record cannot support."),
            "unblock": "Export STEP from Fusion 360 into CAD Files/exports/ and rerun tools/cad_to_web.py.",
        },
    }, previews


FOUR_BAR_ROLES = {  # colour assignments in Project33FourBar.export_step()
    (0.5271, 0.5271, 0.5271): "ground", (1.0, 0.0, 0.0): "input",
    (0.0, 0.0, 1.0): "coupler", (0.0, 1.0, 0.0): "output",
}


def annotate_four_bar(parts):
    for part in parts:
        role = FOUR_BAR_ROLES.get(tuple(part["color"] or ()))
        part["role"] = role
        part["role_basis"] = ("Inferred from the colour each link receives in "
                              "CAD Files/FusionScripts/Project33FourBar/Project33FourBar.py export_step(); "
                              "the STEP product names are numeric." if role else "No colour match; role unknown.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    out_dir = root / OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = []

    sources = list(STEP_SOURCES)
    exports = root / EXPORTS_DIR
    if exports.is_dir():
        for step in sorted(list(exports.glob("*.step")) + list(exports.glob("*.stp"))):
            sources.append((step.stem.lower().replace(" ", "_"), step.relative_to(root).as_posix()))
    for key, rel in sources:
        data = (root / rel).read_bytes()
        parts = step_view(root / rel)
        if key == "four_bar":
            annotate_four_bar(parts)
        view = {"schema": "project33.lab.step_mesh/1", "generated_by": "tools/cad_to_web.py",
                "source": rel, "source_sha256": sha256(data), "units": "mm",
                "tessellation": {"linear_deflection_mm": LINEAR_DEFLECTION_MM,
                                 "angular_deflection_rad": ANGULAR_DEFLECTION_RAD,
                                 "kernel": "OpenCascade via OCP"},
                "parts": parts}
        target = OUT / f"{key}.json"
        payload = (json.dumps(view, separators=(",", ":")) + "\n").encode()
        (root / target).write_bytes(payload)
        outputs.append({"path": target.as_posix(), "sha256": sha256(payload), "inputs": {rel: sha256(data)}})

    inventory = []
    for rel in ARCHIVES:
        view, previews = archive_view(root, rel, OUT)
        for path, png, member in previews:
            (root / path).write_bytes(png)
            outputs.append({"path": path.as_posix(), "sha256": sha256(png), "inputs": {rel: view["sha256"]},
                            "note": f"Fusion-embedded preview image of {member}; Autodesk-rendered thumbnail, "
                                    "not a measurement"})
        inventory.append(view)
    inv = {"schema": "project33.lab.cad_archive/1", "generated_by": "tools/cad_to_web.py",
           "archives": inventory}
    payload = dump(inv)
    (root / OUT / "archives.json").write_bytes(payload)
    outputs.append({"path": (OUT / "archives.json").as_posix(), "sha256": sha256(payload),
                    "inputs": {rel: sha256((root / rel).read_bytes()) for rel in ARCHIVES}})
    manifest = {"schema": "project33.lab.cad_manifest/1", "generated_by": "tools/cad_to_web.py",
                "outputs": sorted(outputs, key=lambda o: o["path"])}
    (root / OUT / "manifest.json").write_bytes(dump(manifest))
    print(f"wrote {len(outputs)} CAD views to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
