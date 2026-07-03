from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_rocket_ignition_command_requires_armed_state():
    rocket = _read("Firmware/Rocket/src/main.cpp")

    assert 'cmdBuffer == Project33Protocol::CMD_IGNITE && sysState == "ARMED"' in rocket


def test_launcher_udp_launch_requires_ready_state():
    launcher = _read("Firmware/Launcher/src/main.cpp")

    assert 'if (currentState == READY) {' in launcher
    assert "udpLaunchTriggered = true;" in launcher
    assert 'sendToDashboard(Project33Protocol::CMD_REJECT_LAUNCH_NOT_READY)' in launcher

def test_firmware_exposes_onboard_log_dump_command():
    rocket = _read("Firmware/Rocket/src/main.cpp")
    launcher = _read("Firmware/Launcher/src/main.cpp")

    assert "recordFlightSample(current_time, roll, rate_deg_s, servo_offset);" in rocket
    assert 'cmdBuffer == Project33Protocol::CMD_DUMPLOG' in rocket
    assert "dumpFlightLog();" in rocket
    assert 'msg == Project33Protocol::DASHBOARD_DUMPLOG' in launcher
    assert "Serial2.println(Project33Protocol::CMD_DUMPLOG);" in launcher
    assert 'msg.startsWith(Project33Protocol::LOG_PREFIX)' in launcher
