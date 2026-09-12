"""Check local Markdown destinations offline, without third-party dependencies.

Supports inline links/images and single-line reference definitions, including
angle-bracket paths, optional titles, and one level of nested parentheses.
Checks file/directory existence, not heading anchors or external URLs. HTML
links, Liquid templates, and unresolved reference labels are outside this check.
"""

import argparse
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".venv", "venv", "node_modules", "TestSessions", "__pycache__", ".pio"}
DESTINATION = r"<[^>\n]+>|(?:[^\s()]|\([^()\n]*\))+"
INLINE = re.compile(r"!?\[[^\]\n]*\]\(\s*(?P<target>" + DESTINATION + r")"
                    r"(?:[ \t]+[\"'][^\n]*?[\"'])?\s*\)")
REFERENCE = re.compile(r"^ {0,3}\[[^\]\n]+\]:[ \t]*(?P<target>" + DESTINATION + r")",
                       re.MULTILINE)


def mask_code(text: str) -> str:
    """Blank code while preserving offsets for source-line diagnostics."""
    lines = []
    fence = None
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line.rstrip("\r\n"))
        in_code = fence is not None
        if marker:
            run, rest = marker.groups()
            if fence is None:
                fence = run
                in_code = True
            elif run[0] == fence[0] and len(run) >= len(fence) and not rest.strip():
                fence = None
        if in_code or line.startswith(("    ", "\t")):
            line = re.sub(r"[^\r\n]", " ", line)
        lines.append(line)
    text = "".join(lines)
    return re.sub(r"(`+)(?!`)(.*?)\1(?!`)",
                  lambda match: re.sub(r"[^\r\n]", " ", match.group()),
                  text, flags=re.DOTALL)


def check_links(root: Path) -> tuple[int, list[str]]:
    failures = []
    count = 0
    for directory, subdirs, files in os.walk(root):
        subdirs[:] = sorted(name for name in subdirs if name not in EXCLUDED)
        for name in sorted(files):
            if not name.lower().endswith(".md"):
                continue
            source = Path(directory) / name
            count += 1
            text = mask_code(source.read_text(encoding="utf-8"))
            matches = sorted([*INLINE.finditer(text), *REFERENCE.finditer(text)],
                             key=lambda match: match.start())
            for match in matches:
                target = match.group("target").strip("<>")
                url = urlsplit(target)
                if url.scheme or url.netloc or not url.path:
                    continue
                path = unquote(url.path)
                if path.startswith("/33/"):
                    resolved = root / path.removeprefix("/33/")
                elif path.startswith("/"):
                    resolved = root / path.lstrip("/")
                else:
                    resolved = source.parent / path
                if not resolved.exists():
                    line = text.count("\n", 0, match.start()) + 1
                    failures.append(
                        f"{source.relative_to(root).as_posix()}:{line}: "
                        f"missing local target: {target}"
                    )
    return count, failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT,
                        help="Repository root (defaults to this script's repository)")
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        parser.error(f"not a directory: {root}")
    count, failures = check_links(root)
    for failure in failures:
        print(failure)
    print(f"Checked {count} Markdown files; {len(failures)} broken local links.")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
