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

    assert 'currentState == READY' in launcher
    assert "udpLaunchTriggered = true;" in launcher
    assert 'sendToDashboard(Project33Protocol::CMD_REJECT_LAUNCH_NOT_READY)' in launcher
    # Phase 5 wartime discipline: READY alone is not enough for a remote fire;
    # it also needs a recent physical fire hold or a two-key OVERRIDE.
    assert 'manualFireRecent(millis())' in launcher
    assert 'LauncherCrypto::overrideValid(millis())' in launcher
    assert 'launch_needs_fire_hold_or_override' in launcher

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
        "FUZE_FIRE_PIN",
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

    # MIL-DEV-010: sustained launch detection. The deploy output may fire only
    # when the rocket is not IDLE, the acceleration is above threshold, and it
    # has held for the sustain time.
    assert 'if (sysState != "IDLE") {' in rocket
    assert "current_time - launchDetectStartMs >= DEPLOY_ACCEL_SUSTAIN_MS" in rocket
    assert "a.acceleration.x > DEPLOY_ACCEL_THRESHOLD_MS2" in rocket
    # A drop below the threshold resets the sustain timer.
    assert "launchDetectActive = false;" in rocket


def test_roll_filter_blends_accel_only_with_valid_gravity_reference():
    rocket = _read("Firmware/Rocket/src/main.cpp")

    # Accel roll is only meaningful near 1g: boost reads thrust+gravity and
    # coast reads near free-fall, where atan2 of near-zero axes is noise.
    assert "fabs(accel_mag - GRAVITY_MS2) <= ACCEL_GRAVITY_BAND_MS2" in rocket
    assert 'sysState != "FLIGHT"' in rocket

    gravity = _const(rocket, "float", "GRAVITY_MS2")
    band = _const(rocket, "float", "ACCEL_GRAVITY_BAND_MS2")
    assert 0 < band < gravity, "gravity validity band should be a strict sub-1g window"


def test_no_rocket_message_can_be_mistaken_for_ready_or_ignited():
    # The launcher matches rocket messages with indexOf("READY") and indexOf("IGNITED"):
    # any other rocket-to-launcher text containing those substrings would be read as a
    # readiness handshake or an ignition acknowledgement.
    import json

    launcher = _read("Firmware/Launcher/src/main.cpp")
    rocket = _read("Firmware/Rocket/src/main.cpp")
    assert "msg.indexOf(Project33Protocol::READY) != -1" in launcher
    assert "msg.indexOf(Project33Protocol::IGNITED) != -1" in launcher
    constants = json.loads(_read("protocol/project33_protocol.json"))["firmware_constants"]
    texts = {name: value for name, value in constants.items() if name not in ("READY", "IGNITED")}
    texts.update({f"state {state}": state for state in re.findall(r'sysState = "([A-Z_]+)"', rocket)})
    texts.update({f"literal {text}": text for text in re.findall(r'Serial2\.println\("([^"]*)"\)', rocket)})
    offenders = {name: text for name, text in texts.items() if "READY" in text or "IGNITED" in text}
    assert offenders == {}, f"Rocket-side text would trigger launcher substring matches: {offenders}"


def test_rocket_refusals_reach_the_telemetry_record():
    rocket = _read("Firmware/Rocket/src/main.cpp")
    launcher = _read("Firmware/Launcher/src/main.cpp")
    for constant in ("CMD_REJECT_IGNITE_FINS_NOT_DEPLOYED", "CMD_REJECT_IGNITE_NOT_ARMED",
                     "CMD_REJECT_ARM_NOT_IDLE", "CMD_REJECT_SENSOR_UNAVAILABLE"):
        assert f"Serial2.println(Project33Protocol::{constant}" in rocket or \
            f"Project33Protocol::{constant}" in rocket, constant
    # The launcher forwards every CMD_REJECT line from the rocket to the dashboard CSV.
    assert 'msg.startsWith("CMD_REJECT:")' in launcher


def test_rejection_logging_does_not_reorder_or_weaken_gates():
    rocket = _read("Firmware/Rocket/src/main.cpp")
    gated_arm = rocket.index('cmdBuffer == Project33Protocol::CMD_ARM && sysState == "IDLE" && mpuHealthy')
    gated_ignite = rocket.index('cmdBuffer == Project33Protocol::CMD_IGNITE && sysState == "ARMED" && mpuHealthy')
    reject_ignite = rocket.index("else if (cmdBuffer == Project33Protocol::CMD_IGNITE) {")
    reject_arm = rocket.index("else if (cmdBuffer == Project33Protocol::CMD_ARM) {")
    # The ungated rejection branches come after the gated branches, so they only run
    # when the gate did not match, and they only print.
    assert gated_arm < gated_ignite < reject_ignite < reject_arm
    for start in (reject_ignite, reject_arm):
        body = rocket[start:rocket.index("}", start)]
        assert "sysState =" not in body and ".write(" not in body


def test_launcher_reports_missing_altitude_as_nan_not_zero():
    launcher = _read("Firmware/Launcher/src/main.cpp")
    assert "float altOut = bmpHealthy ? filteredAlt : NAN;" in launcher


def test_dashboard_launch_is_wartime_enabled_with_authentication():
    # MIL-DEV-004: the remote-fire path is enabled, but every weapons command
    # must be authenticated (HMAC + sequence number) and the two-key OVERRIDE
    # discipline replaces the old default-off interlock.
    launcher = _read("Firmware/Launcher/src/main.cpp")
    assert "const bool ENABLE_DASHBOARD_LAUNCH = true;" in launcher
    assert 'msg.startsWith("AUTH,")' in launcher
    assert "LauncherCrypto::authenticate(msg, seq, payload)" in launcher
    assert 'msg.startsWith("OVERRIDE,enabler,")' in launcher
    assert "LauncherCrypto::authorizeOverride" in launcher


def test_command_authentication_has_replay_protection():
    # Monotonic sequence numbers with a sliding replay window: a captured
    # command cannot be re-sent.
    crypto_h = _read("Firmware/Launcher/src/crypto.h")
    assert "REPLAY_WINDOW" in crypto_h
    assert "seq <= lastSeq" in crypto_h
    assert "hmacEqual" in crypto_h  # constant-time compare


def test_telemetry_downlink_is_encrypted_with_aes_ccm():
    launcher = _read("Firmware/Launcher/src/main.cpp")
    crypto_h = _read("Firmware/Launcher/src/crypto.h")
    assert "const bool ENABLE_TELEMETRY_CRYPTO = true;" in launcher
    assert "LauncherCrypto::encryptTelemetry" in launcher
    assert "mbedtls_ccm_encrypt_and_tag" in crypto_h
    # Crypto failure must degrade to plain telemetry, never silence it.
    assert "fall through to plain send" in launcher


def test_fuze_sa_requires_all_three_arming_events():
    # Phase 2 dual-event S&A (docs/MILITARY/FUZE.md): no single event can arm.
    rocket = _read("Firmware/Rocket/src/main.cpp")
    assert 'fuzeState == Project33Protocol::FUZE_STATE_SAFE' in rocket
    assert 'sysState == "FLIGHT"' in rocket
    assert "is_fins_deployed()" in rocket
    assert "(current_time - flightStartMs) >= FUZE_FLIGHT_TIME_GATE_MS" in rocket
    # Function requires an armed fuze plus a real impact deceleration.
    assert "a.acceleration.x < FUZE_IMPACT_THRESHOLD_MS2" in rocket
    # The fire output is safe LOW at boot and only rises after the PD delay.
    assert "digitalWrite(FUZE_FIRE_PIN, LOW);" in rocket
    assert "digitalWrite(FUZE_FIRE_PIN, HIGH);" in rocket
    # The fuze delay set is closed and only settable before flight.
    assert "delayVal == 0 || delayVal == 5 || delayVal == 10 || delayVal == 20" in rocket


def test_fuze_state_is_telemetered():
    rocket = _read("Firmware/Rocket/src/main.cpp")
    assert "Project33Protocol::FUZE_PREFIX" in rocket
    # A fuze that never arms must be visible on the ground station, not at the target.
    assert "lastFuzeSent >= 1000" in rocket


def test_guidance_uses_correct_pn_cross_order():
    # The independent Python CEP model caught a sign error in the first cut
    # (V x omega steers away from the target). The firmware must use omega x V.
    guidance = _read("Firmware/Rocket/src/guidance.h")
    assert "PN_GAIN * (w_n * nav.vel_u - w_u * nav.vel_n)" in guidance
    assert "a_cmd = N * (omega x V)" in guidance or "omega x V" in guidance


def test_engagement_mode_is_an_explicit_prelaunch_selection():
    rocket = _read("Firmware/Rocket/src/main.cpp")
    # AUTO (fire-and-forget) is accepted only before flight.
    assert 'cmdBuffer == "MODE,MITL" || cmdBuffer == "MODE,AUTO"' in rocket
    assert 'engageMode = cmdBuffer.substring(5)' in rocket
    # MITL is the default.
    assert 'String engageMode = "MITL";' in rocket
    # Targets are only accepted before flight.
    assert 'cmdBuffer.startsWith("TARGET,")' in rocket


def test_guidance_starts_after_the_flight_time_gate():
    rocket = _read("Firmware/Rocket/src/main.cpp")
    assert "(current_time - flightStartMs) >= GUIDANCE_FLIGHT_TIME_GATE_MS" in rocket
    # Rocket-side GPS is fed and the origin latched from the rocket's own fix.
    assert "rocketGps.encode(SerialGPS.read())" in rocket
    assert "Guidance::setTargetFromGeo" in rocket
    # Navigation state is telemetered so the ground station sees the guidance.
    assert '"NAV,"' in rocket


def test_safety_gate_registry_matches_firmware_source():
    import json

    gates = json.loads(_read("evidence/safety_gates.json"))["gates"]
    assert len({g["id"] for g in gates}) == len(gates)
    failures = []
    for gate in gates:
        for check in gate["source"]:
            text = _read(check["path"])
            if "contains" in check and check["contains"] not in text:
                failures.append(f"{gate['id']}: missing in {check['path']}: {check['contains']}")
            if "absent" in check and check["absent"] in text:
                failures.append(f"{gate['id']}: must not appear in {check['path']}: {check['absent']}")
    assert failures == []
