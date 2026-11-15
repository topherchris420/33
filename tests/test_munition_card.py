"""Munition configuration card: generated, deterministic, current."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_card_is_current_and_deterministic():
    result = subprocess.run(
        [sys.executable, 'tools/render_munition_card.py', '--check'],
        cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_card_carries_the_modeled_label():
    svg = (ROOT / 'docs/assets/munition_overview.svg').read_text(encoding='utf-8')
    assert 'MODELED' in svg
    # No timestamps: the card is byte-reproducible.
    assert 'dc:date' not in svg.lower()
    # Key stations from the design point appear in the rendered text.
    for token in ('MIL-33', 'warhead bay', 'canards', 'folding', 'static margin',
                  'CG (ignition) 323', 'CP 450'):
        assert token in svg, token


def test_readme_and_site_reference_the_card():
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert 'docs/assets/munition_overview.svg' in readme
    assert 'Guided munition configuration' in readme
    index = (ROOT / 'index.md').read_text(encoding='utf-8')
    assert 'docs/assets/munition_overview.svg' in index
