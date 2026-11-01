"""The laboratory is read-only. It must have no path to hardware, firmware, or a network
command interface: no transmit APIs, no cross-origin requests, no externally hosted scripts."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "lab"
FORBIDDEN = {
    "WebSocket": re.compile(r"\bWebSocket\b"),
    "WebSerial": re.compile(r"navigator\s*\.\s*serial"),
    "WebUSB": re.compile(r"navigator\s*\.\s*usb"),
    "WebBluetooth": re.compile(r"navigator\s*\.\s*bluetooth"),
    "WebHID": re.compile(r"navigator\s*\.\s*hid"),
    "WebRTC": re.compile(r"RTCPeerConnection|RTCDataChannel"),
    "Server-sent events": re.compile(r"\bEventSource\b"),
    "Beacon": re.compile(r"sendBeacon"),
    "XMLHttpRequest": re.compile(r"XMLHttpRequest"),
    "Cross-origin fetch": re.compile(r"fetch\(\s*[`'\"]\s*(?:https?:)?//"),
}


def _sources():
    for path in sorted(LAB.rglob("*")):
        if path.is_file() and path.suffix in {".js", ".mjs", ".html"} and "lib" not in path.relative_to(LAB).parts:
            yield path


def _code(path):
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".html":  # prose may name these APIs; only inline scripts are code
        return "\n".join(re.findall(r"<script\b[^>]*>(.*?)</script>", text, re.S | re.I))
    return text


def test_no_transmit_or_device_apis_in_laboratory_code():
    findings = []
    for path in _sources():
        text = _code(path)
        for name, pattern in FORBIDDEN.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(ROOT)}: {name}")
    assert not findings, "\n".join(findings)


def test_pages_load_only_same_origin_scripts_and_styles():
    external = re.compile(r"<(?:script|link)\b[^>]*(?:src|href)=\"(?:https?:)?//", re.I)
    offenders = [str(p.relative_to(ROOT)) for p in LAB.glob("*.html") if external.search(p.read_text(encoding="utf-8"))]
    assert not offenders, offenders


def test_every_fetch_in_the_lab_resolves_against_its_own_origin():
    for path in _sources():
        for match in re.finditer(r"fetch\(([^,)]*)", _code(path)):
            arg = match.group(1).strip()
            assert arg.startswith(("url", "new URL(")), f"{path.relative_to(ROOT)}: fetch({arg})"


def test_laboratory_does_not_touch_firmware_or_safety_records():
    # The lab reads the safety-gate registry for display; it must not ship a modified copy.
    assert not list(LAB.rglob("safety_gates*.json"))
    assert not list(LAB.rglob("*.cpp")) and not list(LAB.rglob("*.ino"))
