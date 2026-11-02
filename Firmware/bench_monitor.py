"""Capture and inspect standalone USB monitor firmware; no device command path."""
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import re
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = json.loads((ROOT / 'protocol/bench_monitor.json').read_text(encoding='utf-8'))
SENSORS = PROTOCOL['sensors']
HEX64 = re.compile(r'[0-9a-f]{64}')
HEX16 = re.compile(r'[0-9a-f]{16}')
UINT32 = 2 ** 32


def uint(text, maximum=UINT32 - 1):
    if not re.fullmatch(r'0|[1-9][0-9]{0,9}', text):
        raise ValueError('Invalid unsigned integer')
    value = int(text)
    if value > maximum:
        raise ValueError('Integer outside the protocol range')
    return value


def parse_line(raw):
    """Return a validated frame or None for unrelated USB startup/log text."""
    if not isinstance(raw, str) or len(raw) > PROTOCOL['maximum_line_bytes'] or not raw.isascii():
        raise ValueError('Invalid or oversized diagnostic line')
    parts = raw.strip().split(',')
    if parts[0] not in PROTOCOL['messages']:
        return None
    if len(parts) < 7 or parts[1] != '1' or parts[2] not in {'rocket', 'launcher'} or not HEX16.fullmatch(parts[3]):
        raise ValueError('Invalid diagnostic header')
    frame = dict(kind=parts[0], role=parts[2], boot=parts[3], sequence=uint(parts[4]), uptime_ms=uint(parts[5]))
    if frame['kind'] == 'P33ID':
        if len(parts) != 7 or not HEX64.fullmatch(parts[6]):
            raise ValueError('Invalid ELF identity')
        frame['elf_sha256'] = parts[6]
    elif frame['kind'] == 'P33SYS':
        if len(parts) != 9:
            raise ValueError('Invalid system diagnostic length')
        frame.update(reset_code=uint(parts[6], 255), free_heap=uint(parts[7]), min_heap=uint(parts[8]))
        if frame['min_heap'] > frame['free_heap']:
            raise ValueError('Minimum heap exceeds current free heap')
    else:
        sensor = SENSORS.get(parts[6])
        if not sensor or sensor['role'] != frame['role'] or len(parts) != 8 + len(sensor['fields']) or parts[7] not in {'0', '1'}:
            raise ValueError('Invalid sensor frame')
        valid = parts[7] == '1'
        if not valid:
            if any(v != 'nan' for v in parts[8:]):
                raise ValueError('Invalid readings must use nan, not a numeric placeholder')
            values = {name: None for name in sensor['fields']}
        else:
            readings = [float(v) for v in parts[8:]]
            if not all(math.isfinite(v) for v in readings):
                raise ValueError('Nonfinite reading marked valid')
            if parts[6] == 'gps' and not (-90 <= readings[0] <= 90 and -180 <= readings[1] <= 180):
                raise ValueError('Invalid geographical coordinate')
            if parts[6] == 'bmp180' and readings[1] <= 0:
                raise ValueError('Nonpositive pressure marked valid')
            values = dict(zip(sensor['fields'], readings))
        frame.update(sensor=parts[6], valid=valid, values=values)
    return frame


def analyze(records, *, now=None, manifests=()):
    """Interpret declared raw records. No assertion of authentic physical origin."""
    boots = {}
    counts = dict(records=0, frames=0, ignored=0, malformed=0, duplicates=0, conflicting_duplicates=0, sequence_gaps=0, regressions=0)
    last_received = 0.0
    origins = set()
    for record in records:
        counts['records'] += 1
        received = record.get('elapsed_s')
        if not isinstance(received, (int, float)) or isinstance(received, bool) or not math.isfinite(received) or received < last_received:
            raise ValueError('Capture times must be finite, nonnegative and ordered')
        last_received = received
        origin = record.get('origin', 'undeclared')
        origins.add(origin if isinstance(origin, str) and origin in {'synthetic', 'undeclared'} else 'other declaration')
        try:
            frame = parse_line(record.get('raw'))
        except (ValueError, TypeError):
            counts['malformed'] += 1
            continue
        if frame is None:
            counts['ignored'] += 1
            continue
        key = f"{frame['role']}:{frame['boot']}"
        if key not in boots:
            if len(boots) >= 1024:
                raise ValueError('Too many boot identities in one report')
            boots[key] = dict(role=frame['role'], boot=frame['boot'], elf_sha256=None, identity_conflict=False,
                              sequence=None, uptime_ms=None, system=None, sensors={}, last_frame=None)
        state = boots[key]
        if state['sequence'] is not None:
            step = (frame['sequence'] - state['sequence']) % UINT32
            clock_step = (frame['uptime_ms'] - state['uptime_ms']) % UINT32
            if step == 0:
                counts['duplicates'] += 1
                if frame != state['last_frame']:
                    counts['conflicting_duplicates'] += 1
                    state['identity_conflict'] = True
                continue
            if step >= UINT32 // 2 or clock_step >= UINT32 // 2:
                counts['regressions'] += 1
                continue
            counts['sequence_gaps'] += step - 1
        counts['frames'] += 1
        state.update(sequence=frame['sequence'], uptime_ms=frame['uptime_ms'], last_frame=frame)
        if frame['kind'] == 'P33ID':
            if state['elf_sha256'] not in {None, frame['elf_sha256']}:
                state['identity_conflict'] = True
            else:
                state['elf_sha256'] = frame['elf_sha256']
        elif frame['kind'] == 'P33SYS':
            state['system'] = dict(reset_code=frame['reset_code'], free_heap=frame['free_heap'], min_heap=frame['min_heap'], received_s=received)
        else:
            state['sensors'][frame['sensor']] = dict(valid=frame['valid'], values=frame['values'], received_s=received,
                                                     units=dict(zip(SENSORS[frame['sensor']]['fields'], SENSORS[frame['sensor']]['units'])))
    end = last_received if now is None else now
    if not isinstance(end, (float, int)) or not math.isfinite(end) or end < last_received:
        raise ValueError('Report end time precedes the capture')
    expected = {}
    for manifest in manifests:
        if manifest.get('schema') != 'project33.monitor_build/1' or manifest.get('role') not in {'rocket', 'launcher'} or not HEX64.fullmatch(manifest.get('elf_sha256', '')):
            raise ValueError('Invalid build manifest')
        if manifest['role'] in expected:
            raise ValueError('Duplicate manifest role')
        expected[manifest['role']] = manifest['elf_sha256']
    for state in boots.values():
        del state['last_frame']
        if state['system']:
            state['system']['age_s'] = end - state['system']['received_s']
            state['system']['status'] = 'STALE' if state['system']['age_s'] * 1000 > PROTOCOL['validity_ms'] else 'REPORTED'
        identity = state['elf_sha256']
        state['identity_comparison'] = ('CONFLICT' if state['identity_conflict'] else 'UNKNOWN' if identity is None or identity == '0' * 64 or state['role'] not in expected
                                        else 'REPORTED MATCH' if identity == expected[state['role']] else 'MISMATCH')
        for name, sensor in SENSORS.items():
            if sensor['role'] != state['role']:
                continue
            if name not in state['sensors']:
                state['sensors'][name] = dict(status='NOT OBSERVED', values=None)
                continue
            reading = state['sensors'][name]
            reading['age_s'] = end - reading['received_s']
            reading['status'] = ('STALE' if reading['age_s'] * 1000 > PROTOCOL['validity_ms'] else 'REPORTED' if reading['valid'] else 'INVALID')
    return dict(schema='project33.monitor_report/1', meaning='Raw diagnostic interpretation, not accepted evidence or readiness.',
                elapsed_s=end, origins=sorted(origins), counts=counts, boots=list(boots.values()))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def build_manifest(role, elf, binary):
    return dict(schema='project33.monitor_build/1', role=role, elf_sha256=sha(elf), binary_sha256=sha(binary),
                elf_path=str(elf), binary_path=str(binary), meaning='Build artifact identity; installed hardware not verified.')


def read_records(path):
    with Path(path).open(encoding='utf-8') as stream:
        for index in range(1000001):
            line = stream.readline(8193)
            if not line:
                return
            if index >= 1000000 or len(line) > 8192:
                raise ValueError('Capture exceeds report limits')
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError('Capture record must be an object')
            yield record


def write_capture(output, lines, *, origin, end_time=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    path = output / 'usb.jsonl'
    with path.open('w', encoding='utf-8', newline='\n') as stream:
        for elapsed, raw_bytes in lines:
            record = dict(elapsed_s=elapsed, received_utc=datetime.now(timezone.utc).isoformat(), origin=origin,
                          raw=raw_bytes.decode('ascii', errors='replace').strip(), raw_b64=base64.b64encode(raw_bytes).decode('ascii'))
            stream.write(json.dumps(record, allow_nan=False) + '\n')
    ended = end_time() if end_time else None
    report = analyze(read_records(path), now=ended)
    (output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    metadata = dict(schema='project33.monitor_capture/1', origin=origin, stage='RAW DIAGNOSTICS',
                    raw_sha256=sha(path), elapsed_s=report['elapsed_s'], protocol_sha256=sha(ROOT / 'protocol/bench_monitor.json'))
    (output / 'session.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    demo = commands.add_parser('demo'); demo.add_argument('--output', required=True)
    replay = commands.add_parser('replay'); replay.add_argument('capture'); replay.add_argument('--now', type=float); replay.add_argument('--manifest', action='append', default=[]); replay.add_argument('--output')
    manifest = commands.add_parser('manifest'); manifest.add_argument('--role', choices=['rocket', 'launcher'], required=True); manifest.add_argument('--elf', required=True); manifest.add_argument('--binary', required=True); manifest.add_argument('--output')
    capture = commands.add_parser('capture'); capture.add_argument('--port', required=True); capture.add_argument('--seconds', type=float, default=60); capture.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.command == 'manifest':
        result = build_manifest(args.role, args.elf, args.binary)
    elif args.command == 'replay':
        path = Path(args.capture)
        if path.is_dir():
            metadata = json.loads((path / 'session.json').read_text(encoding='utf-8'))
            if sha(path / 'usb.jsonl') != metadata['raw_sha256']:
                parser.error('Raw capture digest mismatch')
            if metadata.get('protocol_sha256') != sha(ROOT / 'protocol/bench_monitor.json'):
                parser.error('Capture protocol identity differs from this parser')
            if args.now is None:
                args.now = metadata['elapsed_s']
            path = path / 'usb.jsonl'
        manifests = [json.loads(Path(p).read_text(encoding='utf-8')) for p in args.manifest]
        result = analyze(read_records(path), now=args.now, manifests=manifests)
    elif args.command == 'demo':
        boot = '0123456789abcdef'
        raw = [f'P33ID,1,rocket,{boot},0,0,' + 'a' * 64,
               f'P33SYS,1,rocket,{boot},1,500,1,200000,190000',
               f'P33S,1,rocket,{boot},2,500,mpu6050,1,0,0,9.80665,0,0,0,23',
               f'P33S,1,rocket,{boot},3,1000,mpu6050,0,nan,nan,nan,nan,nan,nan,nan']
        result = write_capture(args.output, ((i / 2, (line + '\n').encode()) for i, line in enumerate(raw)), origin='synthetic')
    else:
        if not math.isfinite(args.seconds) or not 0 < args.seconds <= 86400:
            parser.error('Duration must be finite and between 0 and 86400 seconds')
        if Path(args.output).exists():
            parser.error('Choose a new output directory')
        import serial  # Optional; replay, manifest and demo use the standard library only.
        start = time.monotonic()
        def incoming(device):
            while time.monotonic() - start < args.seconds:
                raw = device.readline(PROTOCOL['maximum_line_bytes'] + 1)
                if raw:
                    yield time.monotonic() - start, raw
        device = serial.Serial(port=None, baudrate=115200, timeout=0.2)
        device.dtr = False; device.rts = False; device.port = args.port
        try:
            device.open()
            result = write_capture(args.output, incoming(device), origin='undeclared', end_time=lambda: time.monotonic() - start)
        finally:
            device.close()
    text = json.dumps(result, indent=2, allow_nan=False)
    if getattr(args, 'output', None) and args.command in {'manifest', 'replay'}:
        destination = Path(args.output)
        if args.command == 'replay':
            capture_path = Path(args.capture).resolve()
            capture_root = capture_path if capture_path.is_dir() else capture_path.parent
            if destination.resolve().is_relative_to(capture_root):
                parser.error('Derived output must be outside the raw capture folder')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(text + '\n')
    print(text)


if __name__ == '__main__':
    main()
