"""Render chosen moments of the tutorial film to JPEG stills for review.

    python tools/tutorial/frames.py main 3.0 16.3 24.5   ->  build/tutorial/frames/main-0003.00.jpg ...
"""
import base64, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build" / "tutorial" / "frames"


def main():
    cut, times = sys.argv[1], [float(x) for x in sys.argv[2:]]
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--allow-file-access-from-files"])
        page = b.new_page(viewport={"width": 1920, "height": 1080})
        logs = []
        page.on("console", lambda m: logs.append(m.text))
        page.goto((ROOT / "build" / "tutorial" / "harness.html").as_uri() + f"?cut={cut}")
        page.wait_for_function("!!window.ready")
        page.evaluate("window.ready")
        for t in times:
            ms = page.evaluate(f"window.renderAt({t})")
            data = page.evaluate("window.grab()")
            path = OUT / f"{cut}-{t:07.2f}.jpg"
            path.write_bytes(base64.b64decode(data.split(",")[1]))
            print(f"{path.name}  {ms:.0f} ms")
        errs = page.evaluate("window.errors")
        for e in errs + [l for l in logs if "missing" in l or "rror" in l][:20]:
            print("JS:", e)
        b.close()


if __name__ == "__main__":
    main()
