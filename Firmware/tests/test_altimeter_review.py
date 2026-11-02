import configparser
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Firmware'))
import altimeter_review as review
import bench_monitor


def log_for(heights, *, times=None, mount='rocket'):
    log = review.demo()
    log['sensor']['mount'] = mount
    log['observations'] = []
    log['samples'] = [dict(time_s=t, valid=h is not None, origin='synthetic',
                           pressure_pa=None if h is None else review.pressure_for_height(h, log['reference']))
                      for t, h in zip(times if times is not None else [i / 5 for i in range(len(heights))], heights)]
    return log


def test_pressure_model_has_reference_and_independent_known_ratio():
    ref = review.demo()['reference']
    assert review.relative_height(ref['pressure_pa'], ref) == 0
    # Half the reference pressure in the chosen NASA-style model is about 5.48 km.
    assert review.relative_height(ref['pressure_pa'] / 2, ref) == pytest.approx(5484, abs=1)


def test_synthetic_rise_peak_and_descent_are_separate_from_observer_declarations():
    result = review.analyze(review.demo())
    assert [e['kind'] for e in result['events']] == ['ASCENT_REVIEW', 'SIMULATED_RELEASE_MARKER']
    release = result['events'][1]
    assert release['sampled_peak_time_s'] == 11
    assert release['sampled_peak_height_m'] == pytest.approx(120)
    assert release['time_s'] > release['sampled_peak_time_s']
    assert result['summary']['rocket_altitude_available'] is True
    assert result['origins'] == ['synthetic']
    assert result['observations'][0]['operator'] == 'SYNTHETIC observer'
    assert not any('land' in e['kind'].lower() for e in result['events'])


@pytest.mark.parametrize('mount', ['launcher', 'stationary_bench'])
def test_ground_sources_never_acquire_rocket_markers(mount):
    log = review.demo(); log['sensor']['mount'] = mount
    result = review.analyze(log)
    assert result['events'] == []
    assert result['summary']['rocket_altitude_available'] is False


def test_stationary_noise_and_single_spike_do_not_emit_release_markers():
    result = review.analyze(log_for([0, .1, -.1] * 20 + [30] + [0] * 20))
    assert result['events'] == []


@pytest.mark.parametrize('boundary', ['gap', 'invalid'])
def test_lost_data_prevents_an_ascent_descent_inference_across_the_boundary(boundary):
    heights = [i * 2 for i in range(20)] + ([None] if boundary == 'invalid' else []) + [38 - i * 2 for i in range(20)]
    times = [i / 5 for i in range(len(heights))]
    if boundary == 'gap':
        times = [t + (2 if i >= 20 else 0) for i, t in enumerate(times)]
    result = review.analyze(log_for(heights, times=times))
    assert [e['kind'] for e in result['events']] == ['ASCENT_REVIEW']
    assert result['summary']['segments'] == 2
    assert result['samples'][21 if boundary == 'invalid' else 20]['vertical_rate_m_s'] is None


def test_irregular_sample_clock_estimates_a_known_linear_rate():
    times = [0, .12, .31, .49, .70, .9, 1.11]
    result = review.analyze(log_for([3 * t for t in times], times=times))
    assert result['samples'][-1]['vertical_rate_m_s'] == pytest.approx(3, abs=1e-8)
    assert result['samples'][0]['status'] == 'WARMUP'


def test_model_domain_invalidates_height_without_fabricating_zero():
    result = review.analyze(log_for([12000, None, 0, 0, 0]))
    assert result['samples'][0]['height_m'] is None
    assert result['samples'][0]['pressure_pa'] > 0
    assert result['summary']['invalid'] == 2
    assert result['samples'][2]['break_before'] is True


@pytest.mark.parametrize('change', [
    lambda x: x['samples'][0].update(time_s=True),
    lambda x: x['samples'][1].update(time_s=0),
    lambda x: x['samples'][1].update(time_s=1e-300),
    lambda x: x['samples'][0].update(pressure_pa=float('nan')),
    lambda x: x['samples'][0].update(valid=False),
    lambda x: x['samples'][0].update(origin='measured'),
    lambda x: x['reference'].update(pressure_pa=0),
    lambda x: x['reference'].update(temperature_k=None),
    lambda x: x['sensor'].update(mount='unknown'),
    lambda x: x.update(observations=[dict(kind='parachute_observed', time_s=1000, operator='A', note='B')]),
])
def test_invalid_or_ambiguous_inputs_are_rejected(change):
    log = review.demo(); change(log)
    with pytest.raises(ValueError):
        review.analyze(log)


def capture(tmp_path, frames):
    folder = tmp_path / 'raw'
    bench_monitor.write_capture(folder, [(i / 5, line.encode()) for i, line in enumerate(frames)], origin='synthetic')
    return folder


def frame(sequence, uptime, *, boot='0123456789abcdef', elf='a' * 64, pressure='101325', valid='1'):
    return f'P33BARO,1,{boot},{sequence},{uptime},{valid},{pressure},{elf}'


def test_usb_import_preserves_origins_identity_and_clock_wrap(tmp_path):
    path = capture(tmp_path, [frame(4294967295, 4294967200), frame(0, 104)])
    log = review.import_capture(path, boot=None, reference=review.demo()['reference'])
    assert log['sensor']['mount'] == 'stationary_bench'
    assert [s['time_s'] for s in log['samples']] == [0, .2]
    assert all(s['origin'] == 'synthetic' for s in log['samples'])
    assert log['provenance']['reported_elf_sha256'] == 'a' * 64
    assert review.analyze(log)['provenance'] == log['provenance']


def test_sequence_loss_inserts_a_model_break_even_when_clock_gap_is_short(tmp_path):
    path = capture(tmp_path, [frame(0, 0), frame(2, 400)])
    log = review.import_capture(path, boot=None, reference=review.demo()['reference'])
    assert log['samples'][1] == dict(time_s=.2, valid=False, pressure_pa=None, origin='synthetic')
    assert review.analyze(log)['samples'][2]['break_before'] is True


@pytest.mark.parametrize('second', [frame(0, 200), frame(1, 0), frame(1, 200, elf='b' * 64), frame(1, 200, pressure='nan'), frame(1, 200, valid='0')])
def test_corrupt_duplicate_or_conflicting_frames_are_rejected(tmp_path, second):
    path = capture(tmp_path, [frame(0, 0), second])
    with pytest.raises(ValueError):
        review.import_capture(path, boot=None, reference=review.demo()['reference'])


def test_reboots_are_never_stitched_and_changed_raw_files_are_rejected(tmp_path):
    path = capture(tmp_path, [frame(0, 0), frame(0, 0, boot='fedcba9876543210')])
    with pytest.raises(ValueError, match='multiple'):
        review.import_capture(path, boot=None, reference=review.demo()['reference'])
    assert len(review.import_capture(path, boot='0123456789abcdef', reference=review.demo()['reference'])['samples']) == 1
    with (path / 'usb.jsonl').open('a') as stream:
        stream.write('{}\n')
    with pytest.raises(ValueError, match='digest'):
        review.import_capture(path, boot=None, reference=review.demo()['reference'])


def test_cli_roundtrip_preserves_source_and_refuses_overwriting(tmp_path):
    log, report = tmp_path / 'input.json', tmp_path / 'report.json'
    command = [sys.executable, str(ROOT / 'Firmware/altimeter_review.py')]
    subprocess.run(command + ['demo', '--output', str(log)], check=True, capture_output=True)
    original = log.read_bytes()
    subprocess.run(command + ['review', str(log), '--output', str(report)], check=True, capture_output=True)
    data = json.loads(report.read_text())
    assert data['input_sha256'] == hashlib.sha256(original).hexdigest()
    assert log.read_bytes() == original
    assert subprocess.run(command + ['demo', '--output', str(log)], capture_output=True).returncode != 0


def test_firmware_build_is_isolated_from_control_sources_and_actuator_libraries():
    config = configparser.ConfigParser()
    config.read(ROOT / 'Firmware/Rocket/platformio.ini')
    assert config['platformio']['default_envs'] == 'rocket'
    env = config['env:altimeter_bench']
    assert env['build_src_filter'] == '-<*> +<altimeter_bench.cpp>'
    assert 'Servo' not in env['lib_deps']
    code = (ROOT / 'Firmware/Rocket/src/altimeter_bench.cpp').read_text()
    for token in ['Serial2', 'Servo', 'digitalWrite', 'pinMode', 'WiFi', 'IGNITE', 'ARM']:
        assert token not in code


def test_committed_synthetic_example_matches_current_analyzer():
    result = subprocess.run([sys.executable, 'tools/build_altimeter_example.py', '--check'], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
