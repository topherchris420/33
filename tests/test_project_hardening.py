import re
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_local_markdown_image_links_point_to_existing_files():
    image_pattern = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
    failures = []

    for markdown_path in sorted(ROOT.rglob("*.md")):
        if ".git" in markdown_path.parts:
            continue
        text = markdown_path.read_text(encoding="utf-8")
        for match in image_pattern.finditer(text):
            target = match.group(1).split("#", 1)[0].split("?", 1)[0]
            if target.startswith(("http://", "https://")):
                continue

            target = unquote(target)
            if target.startswith("/33/"):
                resolved = ROOT / target.removeprefix("/33/")
            elif target.startswith("/"):
                resolved = ROOT / target.lstrip("/")
            else:
                resolved = (markdown_path.parent / target).resolve()

            if not resolved.exists():
                failures.append(f"{markdown_path.relative_to(ROOT)} -> {target}")

    assert failures == []


def test_platformio_projects_pin_esp32_platform_version():
    for path in ["Firmware/Rocket/platformio.ini", "Firmware/Launcher/platformio.ini"]:
        config = _read(path)
        assert "platform = espressif32@7.0.1" in config


def test_ci_uses_pinned_python_and_platformio_requirements():
    workflow = _read(".github/workflows/ci.yml")
    assert "Firmware/requirements-test.txt" in workflow
    assert "Firmware/requirements-platformio.txt" in workflow
    assert "actions/cache@v4" in workflow

    assert "pytest==" in _read("Firmware/requirements-test.txt")
    assert "platformio==" in _read("Firmware/requirements-platformio.txt")


def test_launcher_dashboard_launch_is_disabled_by_default():
    launcher = _read("Firmware/Launcher/src/main.cpp")
    protocol = _read("protocol/project33_protocol.json")

    assert "ENABLE_DASHBOARD_LAUNCH = false" in launcher
    assert "CMD_REJECT_DASHBOARD_LAUNCH_DISABLED" in protocol
    assert "Project33Protocol::CMD_REJECT_DASHBOARD_LAUNCH_DISABLED" in launcher


def test_launcher_rejects_invalid_or_unknown_dashboard_commands():
    launcher = _read("Firmware/Launcher/src/main.cpp")
    protocol = _read("protocol/project33_protocol.json")

    assert "CMD_REJECT_PID_INVALID" in protocol
    assert "CMD_REJECT_UNKNOWN_COMMAND" in protocol
    assert "isValidPidCommand" in launcher
    assert "Project33Protocol::CMD_REJECT_PID_INVALID" in launcher
    assert "Project33Protocol::CMD_REJECT_UNKNOWN_COMMAND" in launcher


def test_launcher_udp_requires_shared_secret_dashboard_hello():
    launcher = _read("Firmware/Launcher/src/main.cpp")
    dashboard = _read("Firmware/dashboard.py")

    assert "DASHBOARD_AUTH_TOKEN" in launcher
    assert "DASHBOARD_AUTH_TOKEN" in dashboard
    assert "HELLO," in launcher
    assert 'f"HELLO,{DASHBOARD_AUTH_TOKEN}"' in dashboard
    assert "isAuthenticatedDashboard(remote)" in launcher
    assert "if (!isAuthenticatedDashboard(remote))" in launcher
    assert 'msg == "HELLO"' not in launcher
    assert "ENABLE_DASHBOARD_LAUNCH = false" in launcher


def test_firmware_fails_closed_when_sensors_are_missing():
    rocket = _read("Firmware/Rocket/src/main.cpp")
    launcher = _read("Firmware/Launcher/src/main.cpp")

    assert "bool mpuHealthy = false;" in rocket
    assert 'sysState == "IDLE" && mpuHealthy' in rocket
    assert 'cmdBuffer == Project33Protocol::CMD_ARM && sysState == "IDLE" && mpuHealthy' in rocket
    assert "bool bmpHealthy = false;" in launcher
    assert "if (bmpHealthy)" in launcher


def test_rocket_serial_command_buffer_is_bounded():
    rocket = _read("Firmware/Rocket/src/main.cpp")

    assert "MAX_SERIAL_COMMAND_LENGTH = 64" in rocket
    assert "cmdBuffer.length() >= MAX_SERIAL_COMMAND_LENGTH" in rocket
    assert "Serial.println(\"WARNING: Serial command buffer exceeded; dropping partial command.\")" in rocket
    assert "cmdBuffer = \"\";" in rocket


def test_rocket_ignition_transition_documents_bench_semantics():
    rocket = _read("Firmware/Rocket/src/main.cpp")

    assert "FLIGHT state reflects actuation commanded, not confirmed ignition" in rocket
    assert "live propulsion" in rocket


def test_bench_evidence_template_is_checked_in():
    template = ROOT / "docs" / "BENCH_EVIDENCE_TEMPLATE.md"
    assert template.exists()
    text = template.read_text(encoding="utf-8")
    assert "Inert hardware configuration" in text
    assert "Dashboard command rejection" in text
    assert "Do not fabricate" in text


def test_public_docs_present_professional_status_and_boundaries():
    readme = _read("README.md")
    index = _read("index.md")
    status = _read("docs/PROJECT_STATUS.md")
    roadmap = _read("docs/ROADMAP.md")

    assert "bench-validation prototype" in readme
    assert "[Project Status](docs/PROJECT_STATUS.md)" in readme
    assert "[Roadmap](docs/ROADMAP.md)" in readme
    assert "not a flight-tested system" in index
    assert "No flight-test claim" in status
    assert "Do not fabricate or imply flight" in status
    assert "Stage 2: Inert Bench Evidence" in roadmap


def test_paper_alignment_keeps_research_claims_inside_safety_boundary():
    readme = _read("README.md")
    index = _read("index.md")
    paper_alignment = _read("docs/PAPER_ALIGNMENT.md")

    assert "[Paper Alignment](docs/PAPER_ALIGNMENT.md)" in readme
    assert "[Paper integration and evidence traceability](docs/PAPER_ALIGNMENT.md)" in index
    assert "inert bench-validation prototype" in paper_alignment
    assert "does not create a flight-readiness or live-propulsion claim" in paper_alignment
    assert "enable dashboard launch by default" in paper_alignment
    assert "NACA 4-digit fin profile generation" in paper_alignment


def test_docs_explain_fusion_script_install_path():
    readme = _read("README.md")
    cad_docs = _read("docs/CAD_ASSEMBLIES.md")

    assert "tools/install_fusion_script.py" in readme
    assert "Project33NacaFin" in cad_docs
    assert "Scripts and Add-Ins" in cad_docs


def test_github_templates_collect_safety_and_evidence_context():
    pr_template = _read(".github/PULL_REQUEST_TEMPLATE.md")
    assert "Safety Impact" in pr_template
    assert "Evidence Added or Updated" in pr_template
    assert "Not Tested" in pr_template

    expected_templates = [
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/bench_evidence.yml",
        ".github/ISSUE_TEMPLATE/engineering_proposal.yml",
        ".github/ISSUE_TEMPLATE/safety_review.yml",
    ]
    for path in expected_templates:
        assert (ROOT / path).exists(), f"Missing issue form: {path}"

    config = _read(".github/ISSUE_TEMPLATE/config.yml")
    bench = _read(".github/ISSUE_TEMPLATE/bench_evidence.yml")
    safety = _read(".github/ISSUE_TEMPLATE/safety_review.yml")

    assert "blank_issues_enabled: false" in config
    assert "Inert hardware configuration" in bench
    assert "Raw-file provenance" in bench
    assert "safety-critical behavior" in safety
    assert "Dashboard launch remains disabled by default" in safety


def test_security_policy_routes_sensitive_safety_reports():
    security = _read("SECURITY.md")

    assert "Responsible Disclosure and Safety Reports" in security
    assert "bypass arming, launch, ignition, actuator, or interlock gates" in security
    assert "does not authorize live propulsion or flight activity" in security


def test_front_facing_docs_avoid_informal_placeholder_language():
    public_paths = [
        "README.md",
        "index.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "docs/CAD_ASSEMBLIES.md",
        "docs/PROJECT_STATUS.md",
        "docs/ROADMAP.md",
    ]
    informal_terms = ["billion-dollar", "knockoff", " lol", "-_-", "one-off demo"]
    failures = []

    for path in public_paths:
        text = _read(path).lower()
        for term in informal_terms:
            if term in text:
                failures.append(f"{path}: {term}")

    assert failures == []
