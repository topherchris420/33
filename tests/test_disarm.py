"""MIL-DEV-011 / D-025: DISARM command tests."""


from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_rocket_disarm_safes_an_armed_round():
    rocket = _read("Firmware/Rocket/src/main.cpp")
    assert 'cmdBuffer == Project33Protocol::CMD_DISARM' in rocket
    # Only ARMED is disarmed; a round in FLIGHT is never remotely safed.
    assert 'sysState == "ARMED"' in rocket
    assert "Project33Protocol::CMD_REJECT_DISARM_NOT_ARMED" in rocket
    # Disarming clears the launch detect, drops the ignition servo, resets the
    # fins latch, and acknowledges.
    assert "launchDetectActive = false;" in rocket
    assert "igniteServo.write(IGNITE_SERVO_OFF);" in rocket
    assert "reset_fins_deployed();" in rocket
    assert "Serial2.println(Project33Protocol::DISARMED);" in rocket


def test_launcher_relays_the_disarm_command():
    launcher = _read("Firmware/Launcher/src/main.cpp")
    assert 'msg == Project33Protocol::DASHBOARD_DISARM' in launcher
    assert "Serial2.println(Project33Protocol::CMD_DISARM);" in launcher


def test_dashboard_has_a_disarm_button():
    dashboard = _read("Firmware/dashboard.py")
    assert "text=\"DISARM\"" in dashboard
    assert "def send_disarm_command" in dashboard
    assert 'self._send_udp_command("disarm")' in dashboard


def test_disarm_is_in_the_protocol():
    import json
    protocol = json.loads(_read("protocol/project33_protocol.json"))
    constants = protocol["firmware_constants"]
    assert constants["CMD_DISARM"] == "DISARM"
    assert constants["DISARMED"] == "DISARMED"
    assert constants["CMD_REJECT_DISARM_NOT_ARMED"] == "CMD_REJECT:disarm_not_armed"
    assert constants["DASHBOARD_DISARM"] == "disarm"
    messages = [m["format"] for m in protocol["messages"]]
    assert "DISARM" in messages and "DISARMED" in messages


def test_disarm_is_in_the_safety_gate_registry():
    import json
    gates = json.loads(_read("evidence/safety_gates.json"))["gates"]
    g20 = next(g for g in gates if g["id"] == "G-20")
    assert "DISARM" in g20["gate"]
    assert "never in FLIGHT" in g20["behavior"]
