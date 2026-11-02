import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Firmware'))
import bench_monitor as monitor

BOOT = '0123456789abcdef'


def packet(kind, seq, ms, suffix, role='rocket', boot=BOOT):
    return f'{kind},1,{role},{boot},{seq},{ms},{suffix}'


def record(raw, at=0):
    return dict(raw=raw, elapsed_s=at, origin='synthetic')


def test_valid_frames_preserve_units_and_raw_sample_meaning():
    raw = packet('P33S', 1, 500, 'mpu6050,1,0,0,9.80665,0,0,0,23')
    parsed = monitor.parse_line(raw)
    assert parsed['values']['az'] == 9.80665
    result = monitor.analyze([record(raw)])
    source = result['boots'][0]['sensors']['mpu6050']
    assert source['status'] == 'REPORTED'
    assert source['units']['gx'] == 'rad/s'
    assert result['boots'][0]['identity_comparison'] == 'UNKNOWN'


@pytest.mark.parametrize('suffix', ['mpu6050,1,nan,0,0,0,0,0,23', 'mpu6050,0,0,0,0,0,0,0,0', 'gps,1,100,20', 'unknown,1,0'])
def test_invalid_payloads_cannot_become_valid_readings(suffix):
    with pytest.raises(ValueError):
        monitor.parse_line(packet('P33S', 0, 0, suffix))


def test_gps_coordinate_bounds_and_sensor_role_are_checked():
    with pytest.raises(ValueError):
        monitor.parse_line(packet('P33S', 0, 0, 'gps,1,91,20', role='launcher'))
    assert monitor.parse_line(packet('P33S', 0, 0, 'gps,1,40,-74', role='launcher'))['valid']


def test_invalid_sensor_data_and_stale_data_are_not_zero_or_current():
    raw = packet('P33S', 0, 0, 'mpu6050,0,nan,nan,nan,nan,nan,nan,nan')
    report = monitor.analyze([record(raw)])
    assert report['boots'][0]['sensors']['mpu6050']['status'] == 'INVALID'
    assert report['boots'][0]['sensors']['mpu6050']['values']['ax'] is None
    report = monitor.analyze([record(raw)], now=2.001)
    assert report['boots'][0]['sensors']['mpu6050']['status'] == 'STALE'


def test_sequence_and_clock_rollover_are_distinct_from_regression_and_duplicates():
    a = packet('P33SYS', 4294967295, 4294967295, '1,200000,190000')
    b = packet('P33SYS', 0, 20, '1,200000,190000')
    c = packet('P33SYS', 2, 30, '1,200000,190000')
    d = packet('P33SYS', 1, 10, '1,200000,190000')
    result = monitor.analyze([record(v, i) for i, v in enumerate([a,b,c,c,d])])
    assert result['counts']['sequence_gaps'] == 1
    assert result['counts']['duplicates'] == 1
    assert result['counts']['regressions'] == 1
    assert result['boots'][0]['uptime_ms'] == 30


def test_identity_matches_only_against_explicit_manifest_and_conflicts_persist():
    a = packet('P33ID', 0, 0, 'a' * 64)
    b = packet('P33ID', 1, 500, 'b' * 64)
    manifest = dict(schema='project33.monitor_build/1', role='rocket', elf_sha256='a' * 64)
    assert monitor.analyze([record(a)], manifests=[manifest])['boots'][0]['identity_comparison'] == 'REPORTED MATCH'
    report = monitor.analyze([record(a), record(b, 1)], manifests=[manifest])
    assert report['boots'][0]['identity_comparison'] == 'CONFLICT'
    other = dict(manifest, elf_sha256='b' * 64)
    assert monitor.analyze([record(a)], manifests=[other])['boots'][0]['identity_comparison'] == 'MISMATCH'


def test_conflicting_duplicates_cannot_keep_a_matching_identity_result():
    a = packet('P33ID', 0, 0, 'a' * 64)
    b = packet('P33ID', 0, 0, 'b' * 64)
    result = monitor.analyze([record(a), record(b, 1)])
    assert result['counts']['conflicting_duplicates'] == 1
    assert result['boots'][0]['identity_comparison'] == 'CONFLICT'


def test_restarts_are_separate_records_and_malformed_input_does_not_create_health():
    a = packet('P33SYS', 0, 0, '1,200000,190000')
    b = packet('P33SYS', 0, 0, '1,200000,190000', boot='fedcba9876543210')
    report = monitor.analyze([record(a), record(b, 1), record('P33S,broken', 2), record('boot text', 3)])
    assert len(report['boots']) == 2
    assert report['counts']['malformed'] == 1
    assert report['counts']['ignored'] == 1
    assert report['boots'][0]['sensors']['mpu6050']['status'] == 'NOT OBSERVED'


def test_raw_capture_retains_bytes_and_never_overwrites(tmp_path):
    out = tmp_path / 'capture'
    report = monitor.write_capture(out, [(0, b'boot\xff\n')], origin='synthetic')
    assert report['counts']['malformed'] == 1
    row = json.loads((out / 'usb.jsonl').read_text())
    assert row['raw_b64'] == 'Ym9vdP8K'
    assert json.loads((out / 'session.json').read_text())['origin'] == 'synthetic'
    with pytest.raises(FileExistsError):
        monitor.write_capture(out, [], origin='synthetic')


def test_manifest_identifies_exact_build_artifacts(tmp_path):
    elf = tmp_path / 'test.elf'; binary = tmp_path / 'test.bin'
    elf.write_bytes(b'ELF'); binary.write_bytes(b'BIN')
    manifest = monitor.build_manifest('rocket', elf, binary)
    assert manifest['elf_sha256'] == monitor.sha(elf)
    assert manifest['binary_sha256'] != manifest['elf_sha256']


def test_monitor_builds_exclude_control_sources_and_have_no_control_interfaces():
    import configparser
    for role in ('rocket', 'launcher'):
        config = configparser.ConfigParser()
        config.read(ROOT / f'Firmware/{role.title()}/platformio.ini')
        assert config['platformio']['default_envs'] == role
        assert config[f'env:{role}_monitor']['build_src_filter'] == '-<*> +<bench_monitor.cpp>'
        assert 'BENCH_MODE' not in config[f'env:{role}_monitor']['build_flags']
    source = (ROOT / 'Firmware/shared/BenchMonitor.h').read_text()
    for forbidden in ('ESP32Servo', 'Serial2', 'WiFi', 'trigger_deployment', 'igniteServo', 'digitalWrite', 'pinMode'):
        assert forbidden not in source
    python = (ROOT / 'Firmware/bench_monitor.py').read_text()
    assert 'device.write(' not in python and 'socket' not in python
