"""Inventory Autodesk ShapeManager / ACIS binary (SAB) B-rep blobs without translating them.

Fusion 360 archives store bodies as ``ASM BinaryFile4`` records. This reader
tokenizes the tagged record stream and counts entities in the *current* state
(records before the history section), which is enough to say how much geometry
an archive holds and which surface families a translator would have to support.
It does not build or tessellate geometry, and its counts are not dimensions.
"""

import struct
from collections import Counter

# Tag codes of the binary record stream.
CHAR, SHORT, LONG, FLOAT, DOUBLE, STR8, STR16, STR32A = 2, 3, 4, 5, 6, 7, 8, 9
TRUE, FALSE, REF, IDENT, SUBIDENT, OPEN, CLOSE, TERM = 10, 11, 12, 13, 14, 15, 16, 17
STR32B, POSITION, VECTOR, ENUM, VECTOR2, INT64 = 18, 19, 20, 21, 22, 23


def tokens(data):
    """Yield (tag, value) pairs after the fixed header."""
    magic = data[:15]
    if magic not in (b"ASM BinaryFile4", b"ACIS BinaryFile"):
        raise ValueError("not a SAB stream")
    p = 15 + 16  # magic + version, record count, entity count, flags
    end = len(data)
    while p < end:
        tag = data[p]
        p += 1
        if tag == CHAR:
            value = data[p]; p += 1
        elif tag == SHORT:
            value = struct.unpack_from("<h", data, p)[0]; p += 2
        elif tag in (LONG, REF, ENUM):
            value = struct.unpack_from("<i", data, p)[0]; p += 4
        elif tag == FLOAT:
            value = struct.unpack_from("<f", data, p)[0]; p += 4
        elif tag == DOUBLE:
            value = struct.unpack_from("<d", data, p)[0]; p += 8
        elif tag in (STR8, IDENT, SUBIDENT):
            n = data[p]; p += 1
            value = data[p:p + n].decode("utf-8", "replace"); p += n
        elif tag == STR16:
            n = struct.unpack_from("<H", data, p)[0]; p += 2
            value = data[p:p + n].decode("utf-8", "replace"); p += n
        elif tag in (STR32A, STR32B):
            n = struct.unpack_from("<I", data, p)[0]; p += 4
            value = data[p:p + n].decode("utf-8", "replace"); p += n
        elif tag in (TRUE, FALSE, OPEN, CLOSE, TERM):
            value = None
        elif tag in (POSITION, VECTOR):
            value = struct.unpack_from("<3d", data, p); p += 24
        elif tag == VECTOR2:
            value = struct.unpack_from("<2d", data, p); p += 16
        elif tag == INT64:
            value = struct.unpack_from("<q", data, p)[0]; p += 8
        else:
            raise ValueError(f"unknown SAB tag {tag} at byte {p - 1}")
        yield tag, value


def records(data):
    """Group tokens into records; each record is a list of (tag, value)."""
    current, out, started = [], [], False
    for tag, value in tokens(data):
        if not started:
            if tag != IDENT:
                continue  # header strings and unit doubles
            started = True
        current.append((tag, value))
        if tag == TERM:
            out.append(current)
            current = []
    if current:
        out.append(current)
    return out


def record_name(record):
    parts = []
    for tag, value in record:
        if tag in (IDENT, SUBIDENT):
            parts.append(value)
        else:
            break
    return "-".join(parts)


def summarize(data):
    counts = Counter()
    surfaces = Counter()
    for record in records(data):
        name = record_name(record)
        if name.startswith(("Begin-of-ASM-History", "Begin-of-ACIS-History", "End-of-ASM", "End-of-ACIS")):
            break
        counts[name] += 1
        if name.endswith("-surface"):
            family = name[:-len("-surface")]
            if family == "spline":
                for i, (tag, value) in enumerate(record):
                    if tag == OPEN and i + 1 < len(record) and record[i + 1][0] == IDENT:
                        family = f"spline/{record[i + 1][1]}"
                        break
            surfaces[family] += 1
    return {"bodies": counts["body"], "faces": counts["face"], "edges": counts["edge"],
            "surface_types": dict(surfaces)}
