/** Export the same deterministic renderer used on the page. No screen recording. */
import { createRequire } from "node:module";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { spawn } from "node:child_process";
import { once } from "node:events";
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const [
  url = "http://127.0.0.1:4000/33/film.html",
  output = "build/project33-blueprint.mp4",
] = process.argv.slice(2);
const width = 1920,
  height = 1080,
  fps = 24,
  duration = 32;
await mkdir(path.dirname(path.resolve(output)), { recursive: true });
const browser = await chromium.launch({
  headless: true,
  ...(process.env.CHROME_PATH
    ? { executablePath: process.env.CHROME_PATH }
    : {}),
});
let encoder;
try {
  const page = await browser.newPage({
    viewport: { width, height },
    deviceScaleFactor: 1,
    reducedMotion: "reduce",
  });
  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForFunction(() => !!globalThis.project33Film);
  await page.addStyleTag({
    content:
      "body{margin:0!important}body>*{display:none!important}main{display:block!important}.film-player{margin:0!important;width:100vw!important;border:0!important}#rocket{display:block!important;width:100vw!important;height:100vh!important}.player,.film-description{display:none!important}",
  });
  await page.evaluate(() => globalThis.project33Film.film.resize());
  encoder = spawn(
    process.env.FFMPEG_PATH || "ffmpeg",
    [
      "-y",
      "-f",
      "image2pipe",
      "-vcodec",
      "png",
      "-r",
      String(fps),
      "-i",
      "-",
      "-an",
      "-c:v",
      "libx264",
      "-preset",
      "medium",
      "-crf",
      "18",
      "-pix_fmt",
      "yuv420p",
      "-movflags",
      "+faststart",
      output,
    ],
    { stdio: ["pipe", "ignore", "pipe"], windowsHide: true },
  );
  let encoderError = "";
  encoder.on("error", (error) => {
    encoderError = error.message;
  });
  encoder.stderr.on("data", (data) => {
    encoderError = (encoderError + data.toString()).slice(-4000);
  });
  // Register before streaming so early failure cannot leave an unresolved wait.
  const completed = once(encoder, "close");
  encoder.stdin.on("error", () => {});
  for (let i = 0; i < fps * duration; i++) {
    if (encoder.exitCode !== null)
      throw new Error(`Encoder stopped: ${encoderError}`);
    await page.evaluate((t) => globalThis.project33Film.seek(t), i / fps);
    const frame = await page
      .locator("#rocket")
      .screenshot({ animations: "disabled" });
    if (!encoder.stdin.write(frame)) await once(encoder.stdin, "drain");
    if (i % (fps * 4) === 0) console.log(`Rendered ${i / fps}s / ${duration}s`);
  }
  encoder.stdin.end();
  const [code] = await completed;
  if (code !== 0) throw new Error(encoderError);
  console.log(
    `Exported ${path.resolve(output)} (${width}×${height}, ${fps} fps, ${duration}s, silent)`,
  );
} finally {
  encoder?.stdin.destroy();
  if (encoder && encoder.exitCode === null) encoder.kill();
  await browser.close();
}
