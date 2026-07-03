from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from generate_protocol import load_protocol, render_header, render_markdown


def test_protocol_generates_firmware_header_and_markdown():
    protocol = load_protocol(ROOT / "protocol" / "project33_protocol.json")

    header = render_header(protocol)
    markdown = render_markdown(protocol)

    assert "namespace Project33Protocol" in header
    assert 'static constexpr const char* CMD_DUMPLOG = "DUMPLOG";' in header
    assert 'static constexpr const char* DASHBOARD_DUMPLOG = "dumplog";' in header
    assert "LOG,<ms>,<roll>,<rate>,<output>,<state>,<Kp>,<Kd>,<skew>" in markdown
    assert "CMD_REJECT:launch_not_ready" in markdown
