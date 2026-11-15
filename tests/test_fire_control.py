"""Phase 6 fire-control technology adopted from the F-117 OC-IP supplement:
BIT self-test, MARK designation, range/bearing, out-of-envelope warning, TTG."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Firmware'))
import dashboard  # noqa: E402


def test_one_degree_of_latitude_is_111_km():
    r = dashboard.great_circle_range_m(0.0, 0.0, 1.0, 0.0)
    assert r == pytest.approx(111195.0, abs=300.0)


def test_bearing_east_is_ninety():
    b = dashboard.bearing_deg(0.0, 0.0, 0.0, 1.0)
    assert b == pytest.approx(90.0, abs=0.5)


def test_out_of_envelope_warning_fires_before_the_shot():
    ok, adv = dashboard.envelope_check(1000.0)
    assert ok and "OUT OF ENVELOPE" not in adv
    ok, adv = dashboard.envelope_check(4000.0)
    assert not ok and "OUT OF ENVELOPE" in adv and "DO NOT FIRE" in adv


def test_envelope_uses_the_militarized_motor_sizing():
    # The advisory limit is the MIL-33 ballistic envelope with margin
    # (Simulation/motor_sizing.py), not an arbitrary number.
    assert dashboard.TACTICAL_ENVELOPE_M == 3300.0


def test_ttg_requires_a_usable_speed():
    assert dashboard.time_to_go_s(2000.0, 200.0) == pytest.approx(10.0)
    assert dashboard.time_to_go_s(2000.0, 0.5) is None
    assert dashboard.time_to_go_s(None, 200.0) is None


def test_rocket_has_a_bit_self_test():
    rocket = (ROOT / 'Firmware/Rocket/src/main.cpp').read_text(encoding='utf-8')
    assert 'cmdBuffer == "BIT"' in rocket
    # The reply must carry the state the pre-fire checklist checks: IMU, GPS,
    # fuze, fins, mode, target, state.
    for token in ('mpuHealthy', 'rocketGpsFix', 'fuzeState', 'is_fins_deployed()',
                  'engageMode', 'guidanceTarget.valid'):
        assert token in rocket


def test_launcher_mark_designates_from_its_own_gps():
    launcher = (ROOT / 'Firmware/Launcher/src/main.cpp').read_text(encoding='utf-8')
    assert 'msg == "MARK"' in launcher
    assert 'gps.location.isValid()' in launcher
    # The launcher must refuse MARK without a fix and echo what was stored.
    assert 'CMD_REJECT:mark_no_gps_fix' in launcher
    assert '"MARK," + String(gps.location.lat(), 6)' in launcher


def test_dashboard_parses_bit_and_mark_replies():
    dash = (ROOT / 'Firmware/dashboard.py').read_text(encoding='utf-8')
    assert 'message.startswith("BIT,")' in dash
    assert 'message.startswith("MARK,")' in dash
    # MARK loads the echoed point back into the target fields (verify-what-
    # was-stored discipline).
    assert 'self.target_lat_var.set(parts[1])' in dash
