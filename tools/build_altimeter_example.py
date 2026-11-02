"""Generate the explicitly synthetic pressure-log and laboratory review example."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Firmware'))
import altimeter_review


def build():
    log = altimeter_review.demo()
    raw = json.dumps(log, indent=2, allow_nan=False) + '\n'
    report = altimeter_review.analyze(log)
    report['input_sha256'] = hashlib.sha256(raw.encode()).hexdigest()
    return {'altimeter_example_log.json': raw, 'altimeter_example_review.json': json.dumps(report, indent=2, allow_nan=False) + '\n'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for name, data in build().items():
        path = ROOT / 'lab/data' / name
        if args.check:
            if not path.exists() or path.read_text(encoding='utf-8') != data:
                print(f'{name} is stale: run python tools/build_altimeter_example.py')
                return 1
        else:
            path.write_text(data, encoding='utf-8', newline='\n')
    print('Synthetic altimeter example is current.' if args.check else 'Wrote synthetic altimeter examples.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
