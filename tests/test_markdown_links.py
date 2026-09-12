"""Behavior checks for the offline documentation link checker."""

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "check_markdown_links.py"


def run_check(root):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        capture_output=True, text=True, check=False,
    )


def test_missing_document_and_image_report_source_lines(tmp_path):
    (tmp_path / "README.md").write_text(
        "# Guide\n[Missing](absent.md)\n![Image](missing.png)\n", encoding="utf-8"
    )
    result = run_check(tmp_path)
    assert result.returncode == 1
    assert "README.md:2: missing local target: absent.md" in result.stdout
    assert "README.md:3: missing local target: missing.png" in result.stdout


def test_supported_local_destinations(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (tmp_path / "image (1).png").touch()
    (docs / "guide.md").write_text(
        '[Root](/33/image%20%281%29.png)\n'
        '[Absolute](/image%20%281%29.png)\n'
        '[Relative](../image%20%281%29.png?raw=1#view)\n'
        '![Spaces](<../image (1).png> "Image title")\n'
        '[Parentheses](../image(2).png)\n'
        '[Reference][asset]\n[asset]: <../image (1).png> "title"\n',
        encoding="utf-8",
    )
    (tmp_path / "image(2).png").touch()
    result = run_check(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_external_urls_anchors_and_code_are_skipped(tmp_path):
    (tmp_path / "README.md").write_text(
        '[Web](https://example.com/missing) [Email](mailto:test@example.com)\n'
        '[CDN](//example.com/image.png) [Section](#section)\n'
        '`[Example](absent.md)`\n```markdown\n[Example](absent.md)\n```\n'
        '~~~markdown\n![Example](missing.png)\n~~~\n', encoding="utf-8",
    )
    assert run_check(tmp_path).returncode == 0


def test_reference_definition_is_checked(tmp_path):
    (tmp_path / "README.md").write_text(
        "[Guide][guide]\n\n[guide]: absent.md\n", encoding="utf-8"
    )
    result = run_check(tmp_path)
    assert result.returncode == 1
    assert "README.md:3: missing local target: absent.md" in result.stdout


def test_ignored_generated_directories_are_not_scanned(tmp_path):
    for name in (".git", ".venv", "node_modules", "TestSessions", "__pycache__"):
        folder = tmp_path / name
        folder.mkdir()
        (folder / "README.md").write_text("[Missing](absent.md)", encoding="utf-8")
    assert run_check(tmp_path).returncode == 0


def test_repository_documentation_links():
    result = run_check(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
