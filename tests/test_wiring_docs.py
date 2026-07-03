from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _int_constant(source: str, name: str) -> int:
    match = re.search(rf"const\s+int\s+{name}\s*=\s*(\d+)\s*;", source)
    assert match, f"Missing integer constant {name}"
    return int(match.group(1))


def _string_constant(source: str, name: str) -> str:
    match = re.search(rf'const\s+char\*\s+{name}\s*=\s*"([^"]+)"\s*;', source)
    assert match, f"Missing string constant {name}"
    return match.group(1)


def test_wiring_reference_matches_launcher_source():
    launcher = _read("Firmware/Launcher/src/main.cpp")
    wiring = _read("docs/WIRING.md")

    expected_rows = {
        "Arm Switch": _int_constant(launcher, "SWITCH_PIN"),
        "Launch Button": _int_constant(launcher, "BUTTON_PIN"),
        "Status LED": _int_constant(launcher, "LED_PIN"),
        "Buzzer": _int_constant(launcher, "BUZZER_PIN"),
        "Ignition Servo": _int_constant(launcher, "LAUNCHER_SERVO_PIN"),
        "RX1": _int_constant(launcher, "GPS_RX_PIN"),
    }

    for label, pin in expected_rows.items():
        assert re.search(rf"\|\s*{re.escape(label)}\s*\|\s*{pin}\s*\|", wiring), (
            f"{label} should document GPIO {pin}"
        )

    assert f"| Password   | `{_string_constant(launcher, 'password')}`" in wiring


def test_wiring_reference_matches_rocket_source():
    rocket = _read("Firmware/Rocket/src/main.cpp")
    wiring = _read("docs/WIRING.md")

    expected_rows = {
        "Left Canard": _int_constant(rocket, "LEFT_SERVO_PIN"),
        "Right Canard": _int_constant(rocket, "RIGHT_SERVO_PIN"),
        "Up Canard": _int_constant(rocket, "UP_SERVO_PIN"),
        "Down Canard": _int_constant(rocket, "DOWN_SERVO_PIN"),
        "Ignition Servo": _int_constant(rocket, "IGNITE_SERVO_PIN"),
    }

    for label, pin in expected_rows.items():
        assert re.search(rf"\|\s*{re.escape(label)}\s*\|\s*{pin}\s*\|", wiring), (
            f"{label} should document GPIO {pin}"
        )

    assert f"±{_int_constant(rocket, 'MAX_DEFLECTION')}°" in wiring
