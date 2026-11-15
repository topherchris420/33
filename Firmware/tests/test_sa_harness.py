"""Phase 6.1 fuze S&A software-in-the-loop tests (logic level, not hardware).

Two jobs:
1. Fidelity: the harness constants and rules must match the firmware source
   text in Firmware/Rocket/src/main.cpp — if the firmware changes, this
   fails until the harness is re-ported.
2. The 6.1 matrix: every scenario from docs/MILITARY/LIVE_FIRE_PROGRAM.md
   Phase 6.1, items 1.1-1.4, at the logic level.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Firmware'))
import sa_harness  # noqa: E402


def _firmware():
    return (ROOT / 'Firmware/Rocket/src/main.cpp').read_text(encoding='utf-8')


def _isr():
    return (ROOT / 'Firmware/Rocket/src/deploy_isr.cpp').read_text(encoding='utf-8')


# --- fidelity to the firmware source ---------------------------------------

def test_harness_thresholds_match_the_firmware():
    isr = _isr()
    fw = _firmware()
    assert 'DEPLOY_ACCEL_THRESHOLD_G = 2.0' in isr
    assert sa_harness.DEPLOY_ACCEL_THRESHOLD_MS2 == pytest.approx(2.0 * 9.80665)
    assert 'DEPLOY_ACCEL_SUSTAIN_MS = 150' in isr
    assert sa_harness.DEPLOY_ACCEL_SUSTAIN_MS == 150
    assert 'FUZE_IMPACT_THRESHOLD_MS2 = -8.0 * 9.80665' in fw
    assert sa_harness.FUZE_IMPACT_THRESHOLD_MS2 == pytest.approx(-8.0 * 9.80665)
    assert 'FUZE_FLIGHT_TIME_GATE_MS = 2600' in fw
    assert sa_harness.FUZE_FLIGHT_TIME_GATE_MS == 2600


def test_harness_requires_all_three_arming_events_like_the_firmware():
    fw = _firmware()
    # the three conjuncts in the firmware arming condition
    assert 'sysState == "FLIGHT"' in fw
    assert 'is_fins_deployed()' in fw
    assert '(current_time - flightStartMs) >= FUZE_FLIGHT_TIME_GATE_MS' in fw
    # and the harness implements the same conjunction
    h = sa_harness.scenario_arm_in_order()
    assert h.fuze_state == 'ARMED'


# --- 6.1 item 1.1: no-fire checks ------------------------------------------

def test_drop_transient_never_detects_launch():
    h = sa_harness.scenario_drop_test()
    assert h.launch_detected is False
    assert h.fuze_state == 'SAFE'
    assert h.fire_pin is False


def test_static_acceleration_arms_the_detector_but_not_the_fuze():
    h = sa_harness.scenario_static_acceleration()
    # 8 g for 5 s: the launch DETECTOR fires (sustain satisfied)...
    assert h.launch_detected is True
    # ...but without the FLIGHT state the fuze stays SAFE.
    assert h.fuze_state == 'SAFE'
    assert h.fire_pin is False


# --- 6.1 item 1.2: single events never arm ----------------------------------

@pytest.mark.parametrize('name', [
    'single_event_launch_only',
    'single_event_fins_only',
    'single_event_time_only',
])
def test_each_single_event_leaves_the_fuze_safe(name):
    h = sa_harness.SCENARIOS[name]()
    assert h.fuze_state == 'SAFE', sa_harness.SCENARIOS
    assert h.fire_pin is False


# --- 6.1 item 1.3: all three events arm -------------------------------------

def test_all_three_events_in_order_arm_the_fuze():
    h = sa_harness.scenario_arm_in_order()
    assert h.fuze_state == 'ARMED'
    # but the fire pin is still low: arming is not functioning
    assert h.fire_pin is False


def test_order_within_the_gate_does_not_matter_only_all_three_do():
    # fins deployed first, then the launch event, then time: still armed.
    h = sa_harness.SaHarness()
    h.command('ARM')
    h.set_state('FLIGHT')
    h.deploy_fins(True)
    h.accel(3 * 9.80665, duration_ms=400)
    h.time_advance(3000)
    assert h.fuze_state == 'ARMED'


# --- 6.1 item 1.4: impact function and PD delay ------------------------------

def test_impact_functions_an_armed_fuze():
    h = sa_harness.scenario_impact_function(0)
    assert h.fuze_state == 'FUNCTION'
    assert h.fire_pin is True


@pytest.mark.parametrize('delay', [0, 5, 10, 20])
def test_pd_delay_holds_the_fire_pin_for_the_selected_delay(delay):
    h = sa_harness.SaHarness()
    h.command('ARM')
    # the delay is selected BEFORE flight, as the operator card prescribes
    # (the rocket refuses FUZEDELAY once in FLIGHT).
    h.command(f'FUZEDELAY,{delay}')
    assert h.fuze_delay_ms == delay
    h.set_state('FLIGHT')
    h.accel(3 * 9.80665, duration_ms=400)
    h.deploy_fins(True)
    h.time_advance(3000)
    h.impact(-20 * 9.80665)
    if delay == 0:
        # instantaneous fuze: the pin is high on impact
        assert h.fire_pin is True
        return
    # within the delay window the pin is still low
    h.time_advance(max(delay - 1, 0))
    assert h.fire_pin is False
    # past the delay it is high
    h.time_advance(2)
    assert h.fire_pin is True


def test_fuze_delay_is_refused_in_flight():
    h = sa_harness.SaHarness()
    h.command('ARM')
    h.set_state('FLIGHT')
    h.command('FUZEDELAY,10')
    assert h.fuze_delay_ms == 0  # unchanged: refused outside IDLE/ARMED


def test_impact_on_a_safe_fuze_does_not_function():
    h = sa_harness.scenario_single_event_fins_only()
    h.impact(-20 * 9.80665)
    assert h.fuze_state == 'SAFE'
    assert h.fire_pin is False


def test_sub_threshold_deceleration_does_not_function():
    h = sa_harness.scenario_arm_in_order()
    h.impact(-5 * 9.80665)   # above the -8 g threshold
    assert h.fuze_state == 'ARMED'
    assert h.fire_pin is False


# --- MIL-DEV-011: DISARM -----------------------------------------------------

def test_disarm_safes_an_armed_round_with_a_live_launch_detect():
    h, ok = sa_harness.scenario_disarm_after_abort()
    assert ok is True
    assert h.state == 'IDLE'
    assert h.launch_detected is False
    assert h.fuze_state == 'SAFE'


def test_disarm_is_refused_in_flight():
    h = sa_harness.SaHarness()
    h.command('ARM')
    h.set_state('FLIGHT')
    assert h.command('DISARM') is False
    assert h.state == 'FLIGHT'


# --- the full matrix as one record -------------------------------------------

def test_matrix_matches_expectations():
    results = sa_harness.run_matrix()
    assert results['drop_test']['fuze'] == 'SAFE'
    assert results['static_acceleration']['fuze'] == 'SAFE'
    for name in ('single_event_launch_only', 'single_event_fins_only',
                'single_event_time_only'):
        assert results[name]['fuze'] == 'SAFE'
    assert results['arm_in_order']['fuze'] == 'ARMED'
    for delay in (0, 5, 10, 20):
        r = results[f'impact_function_{delay}ms']
        assert r['fuze'] == 'FUNCTION' and r['fire_pin'] is True
    assert results['disarm_after_abort']['state'] == 'IDLE'
