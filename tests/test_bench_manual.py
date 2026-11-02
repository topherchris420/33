"""Source freshness and identity for the project reading companion."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_manual_is_reproducible_and_sources_are_current():
    run = subprocess.run([sys.executable, 'tools/build_bench_manual.py', '--check'], cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    data = json.loads((ROOT / 'lab/data/bench_manual.json').read_text(encoding='utf-8'))
    sources = {s['path']: s['sha256'] for s in data['sources']}
    assert len({c['id'] for c in data['chapters']}) == len(data['chapters']) == 9
    for chapter in data['chapters']:
        assert chapter['sources'] and chapter['paragraphs'] and chapter['notice'] and chapter['checklist']
        assert chapter['notice_level'] in {'WARNING', 'CAUTION', 'NOTE'}
        for path in chapter['sources']:
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sources[path]
        for item in chapter.get('troubleshooting', []):
            assert item['source'] in sources
            assert item['symptom'] and item['interpretation'] and item['review']

def test_edition_covers_content_and_source_identity():
    data = json.loads((ROOT / 'lab/data/bench_manual.json').read_text(encoding='utf-8'))
    revision = data.pop('revision')
    assert hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest() == revision
