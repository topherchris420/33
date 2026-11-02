"""Render chosen moments of the tutorial film to JPEG stills for review.

Uses the same page and renderer as the player and the exporter.

    python tools/tutorial/frames.py main 3.0 16.3 24.5
    python tools/tutorial/frames.py preflight60 44.5

Writes build/tutorial/frames/<cut>-<time>.jpg. Needs Python Playwright with
Chromium (or CHROME_PATH pointing at an installed Chrome).
"""
import base64
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build" / "tutorial" / "frames"


def main():
    cut, times = sys.argv[1], [float(x) for x in sys.argv[2:]]
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        chrome = os.environ.get("CHROME_PATH")
        browser = p.chromium.launch(**({"executable_path": chrome} if chrome else {}))
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto((ROOT / "tutorial.html").as_uri() + f"?embed=1&cut={cut}")
        page.wait_for_function("!!window.project33Tutorial")
        page.evaluate("""async () => {
            const T = window.project33Tutorial; await T.ready();
            const c = document.createElement('canvas'); c.width = T.cut.width; c.height = T.cut.height;
            window.__still = (t) => { T.renderAt(t, c); return c.toDataURL('image/jpeg', 0.9); };
        }""")
        for t in times:
            data = page.evaluate("t => window.__still(t)", t)
            path = OUT / f"{cut}-{t:07.2f}.jpg"
            path.write_bytes(base64.b64decode(data.split(",", 1)[1]))
            print(path.relative_to(ROOT))
        for e in errors:
            print("page error:", e)
        browser.close()


if __name__ == "__main__":
    main()
