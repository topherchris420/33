from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _const(source: str, ctype: str, name: str) -> float:
    match = re.search(rf"const\s+{ctype}\s+{name}\s*=\s*([\d.]+)", source)
    assert match, f"Missing {ctype} constant {name}"
    return float(match.group(1))


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

def test_deploy_isr_integration():
    rocket = _read("Firmware/Rocket/src/main.cpp")
    isr_cpp = _read("Firmware/Rocket/src/deploy_isr.cpp")

    assert '#include "deploy_isr.h"' in rocket
    assert 'init_project_33_deploy_system();' in rocket
    assert 'IRAM_ATTR' in isr_cpp
    assert 'fins_deployed' in isr_cpp


def test_rocket_gpio_assignments_are_unique():
    rocket = _read("Firmware/Rocket/src/main.cpp")
    isr_cpp = _read("Firmware/Rocket/src/deploy_isr.cpp")

    pins = {}
    for name in (
        "RX2_PIN",
        "TX2_PIN",
        "IGNITE_SERVO_PIN",
        "LEFT_SERVO_PIN",
        "RIGHT_SERVO_PIN",
        "UP_SERVO_PIN",
        "DOWN_SERVO_PIN",
    ):
        pins[name] = int(_const(rocket, "int", name))
    pins["DEPLOY_OUTPUT_PIN"] = int(_const(isr_cpp, "int", "DEPLOY_OUTPUT_PIN"))

    i2c = re.search(r"Wire\.begin\((\d+),\s*(\d+)\)", rocket)
    assert i2c, "Rocket firmware should configure the I2C bus explicitly"
    pins["I2C_SDA"] = int(i2c.group(1))
    pins["I2C_SCL"] = int(i2c.group(2))

    duplicates = {
        pin: [name for name, assigned in pins.items() if assigned == pin]
        for pin in pins.values()
        if list(pins.values()).count(pin) > 1
    }
    assert not duplicates, f"GPIO pins assigned to multiple functions: {duplicates}"


def test_deploy_trigger_uses_consistent_units_and_reachable_threshold():
    rocket = _read("Firmware/Rocket/src/main.cpp")
    isr_cpp = _read("Firmware/Rocket/src/deploy_isr.cpp")

    # The Adafruit MPU6050 driver reports acceleration in m/s², so the loop
    # comparison must use the m/s² constant, never the raw g value.
    assert "a.acceleration.x > DEPLOY_ACCEL_THRESHOLD_MS2" in rocket
    assert "a.acceleration.x > DEPLOY_ACCEL_THRESHOLD_G" not in rocket
    assert re.search(
        r"DEPLOY_ACCEL_THRESHOLD_MS2\s*=\s*DEPLOY_ACCEL_THRESHOLD_G\s*\*\s*9\.80665",
        isr_cpp,
    ), "m/s² threshold should be derived from the g threshold"

    # The configured accelerometer range must be able to observe the
    # threshold, otherwise deployment can never trigger.
    threshold_g = _const(isr_cpp, "float", "DEPLOY_ACCEL_THRESHOLD_G")
    range_match = re.search(r"MPU6050_RANGE_(\d+)_G", rocket)
    assert range_match, "Rocket firmware should configure the accelerometer range"
    assert threshold_g < int(range_match.group(1)), (
        f"Deploy threshold {threshold_g}g exceeds the ±{range_match.group(1)}g "
        "accelerometer range and could never fire"
    )


def test_deploy_trigger_requires_armed_state():
    rocket = _read("Firmware/Rocket/src/main.cpp")

    assert 'sysState != "IDLE" && a.acceleration.x > DEPLOY_ACCEL_THRESHOLD_MS2' in rocket


def test_roll_filter_blends_accel_only_with_valid_gravity_reference():
    rocket = _read("Firmware/Rocket/src/main.cpp")

    # Accel roll is only meaningful near 1g: boost reads thrust+gravity and
    # coast reads near free-fall, where atan2 of near-zero axes is noise.
    assert "fabs(accel_mag - GRAVITY_MS2) <= ACCEL_GRAVITY_BAND_MS2" in rocket
    assert 'sysState != "FLIGHT"' in rocket

    gravity = _const(rocket, "float", "GRAVITY_MS2")
    band = _const(rocket, "float", "ACCEL_GRAVITY_BAND_MS2")
    assert 0 < band < gravity, "gravity validity band should be a strict sub-1g window"
