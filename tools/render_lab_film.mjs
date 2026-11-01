// Render the opening film to MP4 by seeking the deterministic timeline frame by frame.
//   python tools/serve_lab.py 8000 &
//   node tools/render_lab_film.mjs [out.mp4] [fps=24] [width=1280] [from=0] [to=80] [baseURL]
// The film is a pure function of time, so every frame is exact regardless of render speed.
// Audio is synthesized live in the browser and is not captured; add a soundtrack separately.
import { createRequire } from "node:module";
import { spawn } from "node:child_process";
const { chromium } = createRequire(import.meta.url)("playwright");

const [out = "build/project33-living-lab.mp4", fpsArg = "24", widthArg = "1280", fromArg = "0", toArg = "80", base = "http://localhost:8000"] = process.argv.slice(2);
const fps = Number(fpsArg), width = Number(widthArg), height = Math.round((width * 9) / 16);
const from = Number(fromArg), to = Number(toArg);
const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const page = await browser.newPage({ viewport: { width, height: height + 56 } });
page.setDefaultTimeout(600000);
await page.goto(`${base}/lab/cinematic.html?t=${from}`, { waitUntil: "networkidle" });
await page.waitForFunction(() => window.__film, null, { timeout: 600000 });
await page.evaluate(() => {
  document.querySelector("#start").hidden = true;
  for (const sel of [".cine-controls", ".cine-grain"]) document.querySelectorAll(sel).forEach((el) => { el.style.display = "none"; });
});
const ffmpeg = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(fps), "-i", "-",
  "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], { stdio: ["pipe", "inherit", "inherit"] });
const total = Math.round((to - from) * fps);
for (let i = 0; i <= total; i++) {
  const t = from + i / fps;
  await page.evaluate((x) => window.__film.seek(x), t);
  const png = await page.locator("#stage").screenshot({ type: "png" });
  if (!ffmpeg.stdin.write(png)) await new Promise((r) => ffmpeg.stdin.once("drain", r));
  if (i % fps === 0) process.stdout.write(`\r${t.toFixed(1)} s / ${to} s`);
}
ffmpeg.stdin.end();
await new Promise((r) => ffmpeg.on("close", r));
await browser.close();
console.log(`\nwrote ${out}`);
