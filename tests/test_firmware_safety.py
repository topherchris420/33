from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_rocket_ignition_command_requires_armed_state():
    rocket = _read("Firmware/Rocket/src/main.cpp")

    assert 'cmdBuffer == "IGNITE" && sysState == "ARMED"' in rocket


def test_launcher_udp_launch_requires_ready_state():
    launcher = _read("Firmware/Launcher/src/main.cpp")

    assert 'if (currentState == READY) {' in launcher
    assert "udpLaunchTriggered = true;" in launcher
    assert 'sendToDashboard("CMD_REJECT:launch_not_ready")' in launcher
