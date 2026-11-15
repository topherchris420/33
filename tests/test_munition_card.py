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


def test_blueprint_is_current_and_deterministic():
    result = subprocess.run(
        [sys.executable, 'tools/render_munition_blueprint.py', '--check'],
        cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_blueprint_draws_the_verified_linkage_and_labels():
    svg = (ROOT / 'docs/assets/munition_blueprint.svg').read_text(encoding='utf-8')
    assert 'MODELED' in svg
    for token in ('WARHEAD BAY', 'MIL-33 MOTOR', 'CANARD RING', 'FOUR-BAR DETAIL',
                  'over-center', 'static margin 1.66'):
        assert token in svg, token
    # the four-bar detail carries the verified pin-centre dimensions
    assert 'ground 25' in svg and 'coupler 15.5' in svg
    # no timestamps
    assert 'dc:date' not in svg.lower()


def test_workbench_narratives_reflect_the_resolved_record():
    specimens = (ROOT / 'lab/js/workbench/specimens.js').read_text(encoding='utf-8')
    # the old 'neither CP is declared correct' legend is gone...
    assert 'neither CP is declared correct' not in specimens
    # ...replaced by the resolved agreement statement.
    assert 'D-006 resolved' in specimens
    # the coupler intro no longer claims 60 mm for the current STEP.
    assert 'At 60 mm it is too long' not in specimens
    comparison = (ROOT / 'lab/js/mechanism/comparison.js').read_text(encoding='utf-8')
    assert 'MODELS DISAGREE' not in comparison
    assert 'D-006 is resolved' in comparison

