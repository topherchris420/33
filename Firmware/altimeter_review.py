"""Offline model-rocket pressure-log review. Emits data and simulated markers only."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / 'protocol/altimeter_review.json'
SPEC = json.loads(MODEL_PATH.read_text(encoding='utf-8'))


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def text(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise ValueError(f'{name} must be a nonempty string of at most 200 characters')


def validate(log):
    if not isinstance(log, dict) or log.get('schema') != 'project33.altimeter_log/1':
        raise ValueError('Expected project33.altimeter_log/1')
    sensor = log.get('sensor', {})
    if not isinstance(sensor, dict) or sensor.get('mount') not in {'rocket', 'launcher', 'stationary_bench'}:
        raise ValueError('Declare the pressure sensor mount: rocket, launcher or stationary_bench')
    text(sensor.get('id'), 'Sensor identity')
    reference = log.get('reference', {})
    if not isinstance(reference, dict) or not number(reference.get('pressure_pa')) or not 0 < reference['pressure_pa'] <= 120000:
        raise ValueError('Declare a positive reference pressure in Pa, at most 120000')
    if not number(reference.get('temperature_k')) or not 200 <= reference['temperature_k'] <= 330:
        raise ValueError('Declare a reference air temperature in kelvin, from 200 to 330')
    text(reference.get('description'), 'Reference description')
    samples = log.get('samples')
    if not isinstance(samples, list) or not 1 <= len(samples) <= SPEC['maximum_samples']:
        raise ValueError('Expected 1 to 20000 pressure samples')
    previous = -1
    for sample in samples:
        if not isinstance(sample, dict) or not number(sample.get('time_s')) or not 0 <= sample['time_s'] <= 1e9 or (previous >= 0 and sample['time_s'] - previous < 1e-6):
            raise ValueError('Sample times must increase by at least 1 microsecond and be within 0 to 1e9 seconds')
        previous = sample['time_s']
        if sample.get('origin') not in {'synthetic', 'undeclared'} or type(sample.get('valid')) is not bool:
            raise ValueError('Each sample needs an origin and a boolean validity declaration')
        pressure = sample.get('pressure_pa')
        if sample['valid'] and (not number(pressure) or not 0 < pressure <= 120000):
            raise ValueError('A valid pressure must be finite, positive and at most 120000 Pa')
        if not sample['valid'] and pressure is not None:
            raise ValueError('Invalid pressure must be null')
    provenance = log.get('provenance', {})
    if not isinstance(provenance, dict) or any(k not in {'raw_sha256', 'reported_elf_sha256'} or not isinstance(v, str) or not re.fullmatch('[0-9a-f]{64}', v) for k, v in provenance.items()):
        raise ValueError('Invalid source provenance')
    observations = log.get('observations', [])
    if not isinstance(observations, list) or len(observations) > 100:
        raise ValueError('At most 100 operator observations are supported')
    for item in observations:
        if not isinstance(item, dict) or item.get('kind') not in {'parachute_observed', 'ground_contact_observed'}:
            raise ValueError('Unknown recovery observation')
        if not number(item.get('time_s')) or not samples[0]['time_s'] <= item['time_s'] <= samples[-1]['time_s']:
            raise ValueError('Observation time must be within the log')
        text(item.get('operator'), 'Observer')
        text(item.get('note'), 'Observation note')
    return log


def relative_height(pressure, reference):
    """Local linear-lapse atmosphere estimate; not geometric height or ground clearance."""
    model = SPEC['model']
    return reference['temperature_k'] / model['lapse_k_per_m'] * (
        1 - (pressure / reference['pressure_pa']) ** (1 / model['pressure_exponent']))


def pressure_for_height(height, reference):
    return reference['pressure_pa'] * (1 - SPEC['model']['lapse_k_per_m'] * height /
                                      reference['temperature_k']) ** SPEC['model']['pressure_exponent']


def analyze(log):
    validate(log)
    rules, model = SPEC['review'], SPEC['model']
    points, events, window = [], [], []
    previous_time, previous_valid = None, False
    phase, rising_since, falling_since, peak = 'REFERENCE', None, None, None
    segment, gaps, invalid = 0, 0, 0
    rocket = log['sensor']['mount'] == 'rocket'
    for sample in log['samples']:
        t = sample['time_s']
        gap = previous_time is not None and t - previous_time > rules['maximum_gap_s']
        gaps += int(gap)
        height = relative_height(sample['pressure_pa'], log['reference']) if sample['valid'] else None
        valid = height is not None and model['minimum_height_m'] <= height <= model['maximum_height_m']
        broken = gap or not previous_valid
        if not valid or broken:
            window = []
            phase, rising_since, falling_since, peak = 'REFERENCE', None, None, None
        if valid and broken:
            segment += 1
        rate = None
        if valid:
            window.append((t, height))
            window = [(at, h) for at, h in window if t - at <= rules['slope_window_s'] + 1e-9]
            if len(window) >= rules['minimum_slope_samples']:
                # Subtract the first time to preserve precision for large absolute timestamps.
                times = [at - window[0][0] for at, _ in window]
                mean_t = sum(times) / len(times)
                mean_h = sum(h for _, h in window) / len(window)
                denominator = sum((at - mean_t) ** 2 for at in times)
                rate = sum((at - mean_t) * (h - mean_h) for at, (_, h) in zip(times, window)) / denominator
            if peak is None or height > peak[1]:
                peak = (t, height)
            if phase == 'REFERENCE':
                rising = rate is not None and rate >= rules['rise_rate_m_s'] and height >= rules['rise_height_m']
                rising_since = t if rising and rising_since is None else rising_since if rising else None
                if rising_since is not None and t - rising_since + 1e-9 >= rules['sustain_s']:
                    phase = 'RISING'
                    if rocket:
                        events.append(dict(kind='ASCENT_REVIEW', time_s=t, segment=segment))
            elif phase == 'RISING':
                falling = rate is not None and rate <= rules['fall_rate_m_s'] and peak[1] - height >= rules['peak_drop_m']
                falling_since = t if falling and falling_since is None else falling_since if falling else None
                if falling_since is not None and t - falling_since + 1e-9 >= rules['sustain_s']:
                    phase = 'FALLING'
                    if rocket:
                        events.append(dict(kind='SIMULATED_RELEASE_MARKER', time_s=t, segment=segment,
                                           sampled_peak_time_s=peak[0], sampled_peak_height_m=peak[1]))
        else:
            invalid += 1
        points.append(dict(time_s=t, origin=sample['origin'], pressure_pa=sample['pressure_pa'],
                           height_m=height if valid else None, vertical_rate_m_s=rate, segment=segment,
                           break_before=broken, status='INVALID' if not valid else 'WARMUP' if rate is None else 'ESTIMATED',
                           phase=phase if valid else 'UNKNOWN'))
        previous_time, previous_valid = t, valid
    heights = [p['height_m'] for p in points if p['height_m'] is not None]
    return dict(schema='project33.altimeter_review/1', meaning='Offline estimates and simulated release markers; no command output or accepted evidence.',
                model_sha256=hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest(),
                implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), settings=copy.deepcopy(SPEC),
                sensor=copy.deepcopy(log['sensor']), reference=copy.deepcopy(log['reference']), provenance=copy.deepcopy(log.get('provenance', {})),
                origins=sorted({s['origin'] for s in log['samples']}),
                summary=dict(samples=len(points), invalid=invalid, gaps=gaps, segments=segment,
                             maximum_relative_height_m=max(heights) if heights else None,
                             rocket_altitude_available=rocket and bool(heights)),
                samples=points, events=events, observations=copy.deepcopy(log.get('observations', [])))


def demo():
    reference = dict(pressure_pa=101325, temperature_k=288.08, description='Synthetic stationary reference')
    samples = []
    for index in range(251):
        t = round(index / 5, 3)
        height = 0 if t < 3 else 15 * (t - 3) if t < 11 else max(0, 120 - 4 * (t - 11))
        samples.append(dict(time_s=t, valid=True, pressure_pa=pressure_for_height(height, reference), origin='synthetic'))
    return dict(schema='project33.altimeter_log/1', sensor=dict(id='SYNTHETIC pressure source', mount='rocket'),
                reference=reference, samples=samples, observations=[
                    dict(time_s=12, kind='parachute_observed', operator='SYNTHETIC observer', note='Invented illustration, not detected from pressure.'),
                    dict(time_s=41, kind='ground_contact_observed', operator='SYNTHETIC observer', note='Invented illustration, not detected from pressure.')])


def import_capture(path, *, boot, reference):
    """Import raw frames saved by bench_monitor.py. Verify the raw capture digest first."""
    import bench_monitor
    path = Path(path)
    metadata = json.loads((path / 'session.json').read_text(encoding='utf-8'))
    if not isinstance(metadata, dict) or metadata.get('schema') != 'project33.monitor_capture/1' or metadata.get('raw_sha256') != bench_monitor.sha(path / 'usb.jsonl'):
        raise ValueError('Raw capture digest or metadata does not match')
    groups, frame_count = {}, 0
    for record in bench_monitor.read_records(path / 'usb.jsonl'):
        raw = record.get('raw', '')
        if not isinstance(raw, str) or not raw.startswith('P33BARO,'):
            continue
        frame_count += 1
        if frame_count > SPEC['maximum_samples'] or len(raw) > 512:
            raise ValueError('Altimeter capture exceeds import limits')
        parts = raw.split(',')
        if len(parts) != 8 or parts[1] != '1' or not re.fullmatch('[0-9a-f]{16}', parts[2]) or not re.fullmatch('[0-9a-f]{64}', parts[7]):
            raise ValueError('Malformed altimeter frame')
        sequence, uptime = bench_monitor.uint(parts[3]), bench_monitor.uint(parts[4])
        if parts[5] not in {'0', '1'} or (parts[5] == '0' and parts[6] != 'nan'):
            raise ValueError('Malformed pressure validity')
        pressure = float(parts[6]) if parts[5] == '1' else None
        if pressure is not None and (not number(pressure) or not 0 < pressure <= 120000):
            raise ValueError('Invalid pressure marked valid')
        group = groups.setdefault(parts[2], dict(sequence=None, uptime=None, time_ms=0, samples=[], elf=parts[7]))
        if group['elf'] != parts[7]:
            raise ValueError('Conflicting firmware identity within a boot')
        if group['sequence'] is not None:
            step = (sequence - group['sequence']) % bench_monitor.UINT32
            elapsed = (uptime - group['uptime']) % bench_monitor.UINT32
            if step == 0 or step >= bench_monitor.UINT32 // 2 or elapsed == 0 or elapsed >= bench_monitor.UINT32 // 2:
                raise ValueError('Duplicate or regressing altimeter clock/sequence')
            if step != 1:
                # Insert an invalid boundary so a short capture loss cannot join slopes/events.
                group['samples'].append(dict(time_s=(group['time_ms'] + elapsed / 2) / 1000, valid=False, pressure_pa=None,
                                             origin='synthetic' if record.get('origin') == 'synthetic' else 'undeclared'))
            group['time_ms'] += elapsed
        group['sequence'], group['uptime'] = sequence, uptime
        group['samples'].append(dict(time_s=group['time_ms'] / 1000, valid=parts[5] == '1', pressure_pa=pressure,
                                     origin='synthetic' if record.get('origin') == 'synthetic' else 'undeclared'))
        if len(group['samples']) > SPEC['maximum_samples'] or len(groups) > 100:
            raise ValueError('Altimeter capture exceeds import limits')
    if boot is None and len(groups) != 1:
        raise ValueError('Select --boot when the capture has zero or multiple altimeter boots')
    selected = boot or next(iter(groups))
    if selected not in groups:
        raise ValueError('Requested boot not found')
    return dict(schema='project33.altimeter_log/1', sensor=dict(id=f'ESP32/BMP180 boot {selected}', mount='stationary_bench'),
                reference=reference, samples=groups[selected]['samples'], observations=[],
                provenance=dict(raw_sha256=metadata['raw_sha256'], reported_elf_sha256=groups[selected]['elf']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    example = commands.add_parser('demo'); example.add_argument('--output', required=True)
    review = commands.add_parser('review'); review.add_argument('log'); review.add_argument('--output', required=True)
    usb = commands.add_parser('import-usb'); usb.add_argument('capture'); usb.add_argument('--boot')
    usb.add_argument('--pressure-pa', type=float, required=True); usb.add_argument('--temperature-k', type=float, required=True)
    usb.add_argument('--reference-note', required=True); usb.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        parser.error('Output already exists; choose a new path')
    try:
        if args.command == 'demo':
            result = demo()
        elif args.command == 'import-usb':
            if output.resolve().is_relative_to(Path(args.capture).resolve()):
                raise ValueError('Write derived files outside the preserved raw capture')
            result = import_capture(args.capture, boot=args.boot, reference=dict(pressure_pa=args.pressure_pa,
                                    temperature_k=args.temperature_k, description=args.reference_note))
            validate(result)
        else:
            source = Path(args.log)
            if source.stat().st_size > 8 * 1024 * 1024:
                raise ValueError('Input log exceeds 8 MB')
            raw = source.read_bytes()
            result = analyze(json.loads(raw))
            result['input_sha256'] = hashlib.sha256(raw).hexdigest()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(result, indent=2, allow_nan=False) + '\n')
    except (ValueError, OSError, TypeError) as error:
        parser.error(str(error))
    print(f'Wrote {output}')


if __name__ == '__main__':
    main()
