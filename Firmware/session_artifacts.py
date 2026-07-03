from datetime import datetime
from pathlib import Path


class TestSessionArtifacts:
    __test__ = False
    """Owns the files produced by one bench-test session."""

    def __init__(self, root=None, session_id=None):
        self.root = Path(root) if root is not None else Path(__file__).resolve().parent / "TestSessions"
        self.session_id = session_id or datetime.now().strftime("bench_%Y%m%d_%H%M%S")
        self.session_dir = self.root / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.telemetry_csv = self.session_dir / "telemetry.csv"
        self.graph_png = self.session_dir / "graph.png"
        self.summary_md = self.session_dir / "session-summary.md"
        self.pid_markdown = self.session_dir / "pid-comparison.md"

    def write_summary(self, packet_count=0, notes=""):
        lines = [
            f"# Bench Session {self.session_id}",
            "",
            "## Artifacts",
            "",
            f"- Telemetry CSV: `{self.telemetry_csv.name}`",
            f"- Saved graph: `{self.graph_png.name}`",
            f"- PID comparison: `{self.pid_markdown.name}`",
            "",
            "## Run Summary",
            "",
            f"- Packets captured: {packet_count}",
        ]
        if notes:
            lines.extend(["", "## Notes", "", notes])
        self.summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return self.summary_md
