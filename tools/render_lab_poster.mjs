// Render the laboratory poster (lab/assets/poster.jpg) from a frame of the opening film.
//   python tools/serve_lab.py 8000 &   then   node tools/render_lab_poster.mjs [t] [baseURL]
// The frame is the film itself: the rocket is generated from the OpenRocket file.
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
const { chromium } = createRequire(import.meta.url)("playwright");
const t = Number(process.argv[2] || 22.8);
const out = process.argv[4] || "lab/assets/poster.jpg";
const cam = process.argv[5] || "20,96,190,118,24,-50";
const base = process.argv[3] || "http://localhost:8000";
const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const page = await browser.newPage({ viewport: { width: 1600, height: 956 } });
page.setDefaultTimeout(300000);
await page.goto(`${base}/lab/cinematic.html?t=${t}&cam=${cam}`, { waitUntil: "networkidle" });
await page.waitForFunction(() => window.__film, null, { timeout: 300000 });
await page.evaluate((x) => {
  document.querySelector("#start").hidden = true;
  document.body.classList.add("no-bars", "no-cc");
  for (const sel of [".cine-controls", ".cine-tag", ".cine-grain", ".cine-letterbox.top", ".cine-letterbox.bottom"]) document.querySelectorAll(sel).forEach((el) => { el.style.display = "none"; });
  window.__film.seek(x);
}, t);
await page.waitForTimeout(1500);
await page.locator("#stage").screenshot({ path: "build-poster.png" });
await browser.close();
execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", "build-poster.png", "-vf", "scale=1600:-2", "-q:v", "3", out]);
console.log(`wrote ${out}`);
