"""Strict, bounded file handling shared by the evidence tools."""

from contextlib import contextmanager
import csv
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import tempfile


MAX_BYTES = 64 * 1024 * 1024
MAX_ROWS = 250_000


class EvidenceError(ValueError):
    """An input cannot support a reproducible evidence review."""


def canonical_json(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_bytes(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise EvidenceError(f"Expected a regular file: {path.name}")
    with path.open("rb") as handle:
        data = handle.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise EvidenceError(f"File exceeds {MAX_BYTES} bytes: {Path(path).name}")
    return data


def load_json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise EvidenceError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid(value):
        raise EvidenceError(f"Non-finite JSON number: {value}")

    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            invalid(value)
        return number

    try:
        return json.loads(data, object_pairs_hook=unique, parse_constant=invalid, parse_float=finite)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise EvidenceError(f"Invalid JSON: {exc}") from exc


def safe_path(root, name):
    """Accept a canonical relative POSIX path and reject every symlink component."""
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise EvidenceError(f"Invalid relative path: {name!r}")
    if any(ord(char) < 32 for char in name):
        raise EvidenceError("Control character in path")
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != name:
        raise EvidenceError(f"Non-canonical relative path: {name!r}")
    if name == ".":
        raise EvidenceError("Expected a file path")
    current = Path(root).resolve()
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise EvidenceError(f"Symlinks are not evidence files: {name}")
    return current


def csv_rows(data):
    """Yield (line, row); malformed structure is an error, never repaired."""
    try:
        reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""), strict=True)
        fields = reader.fieldnames
        if not fields or any(not field for field in fields) or len(set(fields)) != len(fields):
            raise EvidenceError("CSV requires nonempty, unique column names")
        yield fields
        for count, row in enumerate(reader, 1):
            if count > MAX_ROWS:
                raise EvidenceError(f"CSV exceeds {MAX_ROWS} rows")
            if None in row or any(value is None for value in row.values()):
                raise EvidenceError(f"CSV line {reader.line_num}: column count mismatch")
            yield reader.line_num, row
    except (csv.Error, UnicodeError) as exc:
        raise EvidenceError(f"Invalid CSV: {exc}") from exc


@contextmanager
def new_directory(output):
    """Publish a complete directory only after all work succeeds; never overwrite."""
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise EvidenceError(f"Output already exists; choose a new directory: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".evidence-", dir=output.parent) as temporary:
        stage = Path(temporary) / "bundle"
        stage.mkdir()
        yield stage
        if output.exists() or output.is_symlink():
            raise EvidenceError(f"Output appeared during build: {output}")
        stage.rename(output)
