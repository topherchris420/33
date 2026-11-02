"""The ground status model must keep matching firmware, and the board must stay read-only."""

import ast
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "Firmware"))

from generate_degraded_modes import OUTPUT, render
from ground_status import load_model
from preflight_audit import STEPS


def _read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def _pin_failures(owner, pins):
    failures = []
    for pin in pins:
        text = _read(pin["path"])
        if "contains" in pin and pin["contains"] not in text:
            failures.append(f"{owner}: missing in {pin['path']}: {pin['contains']}")
        if "absent" in pin and pin["absent"] in text:
            failures.append(f"{owner}: must not appear in {pin['path']}: {pin['absent']}")
        if "count" in pin and text.count(pin["count"]) != pin["equals"]:
            failures.append(f"{owner}: expected {pin['equals']} of {pin['count']} in {pin['path']}")
    return failures


def test_every_model_dependency_is_pinned_to_firmware_source():
    model = load_model()
    failures = []
    for section in ("channels", "capabilities", "absent_capabilities"):
        for item in model[section]:
            assert item["source"], f"{item['id']} has no source pin"
            failures += _pin_failures(item["id"], item["source"])
    failures += _pin_failures("firmware_limits", model["firmware_limits"]["source"])
    assert failures == []


def test_model_references_only_known_units_and_channels():
    model = load_model()
    units = {unit["id"] for unit in model["units"]}
    channels = {channel["id"] for channel in model["channels"]}
    for item in model["channels"] + model["capabilities"]:
        assert set(item["requires"]) <= units, item["id"]
    for channel in model["channels"]:
        assert channel.get("gated_by", "environment") in channels
        assert set(model["channels"][0]["requires"])  # non-empty


def test_rocket_states_in_the_model_are_the_ones_firmware_assigns():
    rocket = _read("Firmware/Rocket/src/main.cpp")
    assigned = set(re.findall(r'sysState = "([A-Z_]+)"', rocket))
    assert assigned == set(load_model()["firmware_limits"]["rocket_states"])


def test_launcher_abort_does_not_signal_the_rocket():
    """D-025. If abort starts disarming the rocket, W-ARMED-AFTER-ABORT and the docs must change."""
    launcher = _read("Firmware/Launcher/src/main.cpp")
    start = launcher.index("void abortSequence(String reason) {")
    end = launcher.index("void waitForSwitchReset() {")
    assert "Serial2" not in launcher[start:end]


def test_rocket_ready_is_only_sent_from_idle():
    """D-025. This is why the launcher cannot re-arm a rocket left ARMED by an abort."""
    rocket = _read("Firmware/Rocket/src/main.cpp")
    assert rocket.count("Serial2.println(Project33Protocol::READY);") == 1
    assert 'if (sysState == "IDLE" && mpuHealthy && (current_time - lastReadySent >= 1000)) {' in rocket


def test_discrepancy_for_the_missing_disarm_path_is_on_record():
    items = json.loads(_read("evidence/discrepancies.json"))["discrepancies"]
    record = next(item for item in items if item["id"] == "D-025")
    assert record["status"] == "open"
    assert {side["artifact"] for side in record["sides"]} == {"rocket_firmware", "launcher_firmware"}


def test_degraded_modes_document_is_current():
    assert OUTPUT.read_text(encoding="utf-8") == render(load_model())


def _imports(path):
    tree = ast.parse(_read(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add((node.module or "").split(".")[0])
    return names


def test_status_modules_have_no_transport_or_process_access():
    forbidden = {"socket", "socketserver", "ssl", "http", "urllib", "requests", "serial", "subprocess", "multiprocessing", "asyncio"}
    for path in ("Firmware/ground_status.py", "Firmware/status_panel.py", "Firmware/preflight_audit.py",
                 "tools/generate_degraded_modes.py"):
        assert _imports(path) & forbidden == set(), path


def test_status_panel_has_no_controls_that_can_act():
    source = _read("Firmware/status_panel.py")
    tree = ast.parse(source)
    called = {node.func.attr for node in ast.walk(tree)
              if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
    for widget in ("Button", "Checkbutton", "Radiobutton", "Entry", "Spinbox", "Scale"):
        assert widget not in called, widget
    assert "_send_udp_command" not in source
    assert "sendto" not in source


def test_preflight_audit_steps_match_the_checklist_word_for_word():
    safety = _read("docs/SAFETY.md")
    section = safety[safety.index("## Preflight Checklist for Inert Demonstrations"):]
    numbered = re.findall(r"^(\d+)\. (.+)$", section, flags=re.MULTILINE)
    assert [int(number) for number, _ in numbered] == list(range(1, len(STEPS) + 1))
    assert tuple(text for _, text in numbered) == STEPS


def test_checklist_warns_that_the_rocket_stays_armed_before_the_steps_that_do_it():
    """D-025. If abort starts disarming the rocket, this warning and the audit must change."""
    safety = _read("docs/SAFETY.md")
    section = safety[safety.index("## Preflight Checklist for Inert Demonstrations"):]
    assert "D-025" in section[:section.index("1. Verify wiring")]


def test_discrepancies_for_the_roll_estimator_are_on_record():
    items = {item["id"]: item for item in json.loads(_read("evidence/discrepancies.json"))["discrepancies"]}
    for key in ("D-026", "D-027"):
        assert items[key]["status"] == "open"
        assert "rocket_firmware" in {side.get("artifact") for side in items[key]["sides"]}


def test_ground_status_only_reads_command_strings():
    """The word dumplog appears as data for matching and advice; nothing here can send it."""
    for path in ("Firmware/ground_status.py", "Firmware/preflight_audit.py"):
        source = _read(path)
        assert ".send" not in source, path
        assert "sendto" not in source, path


def test_dashboard_feeds_the_board_without_a_new_command_path():
    dashboard = _read("Firmware/dashboard.py")
    assert "self.status.observe(message)" in dashboard
    assert "self.status.command_sent(cmd)" in dashboard
    # Every send still goes through one method, plus the existing HELLO watchdog.
    assert dashboard.count(".sendto(") == 2
    assert "sock.sendto(cmd.encode('utf-8'), (target_ip, UDP_PORT))" in dashboard
    assert 'sock.sendto(f"HELLO,{DASHBOARD_AUTH_TOKEN}".encode(\'utf-8\'), (LAUNCHER_GATEWAY, UDP_PORT))' in dashboard
