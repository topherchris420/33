/** Export the claymation tutorial from the same deterministic renderer the
 * page uses. Every frame is drawn at exactly frame / 24 seconds; nothing is
 * screen-recorded. Each scene is encoded to its own file (so an interrupted
 * export resumes), the files are joined without re-encoding, and the
 * soundtrack is added without touching the picture.
 *
 *   node tools/export_tutorial_film.mjs [main|preflight60] [output.mp4] [page-url]
 *
 * Env: PLAYWRIGHT_MODULE (path to playwright), CHROME_PATH, FFMPEG_PATH,
 *      TUTORIAL_CRF (default 18), TUTORIAL_WORK (default build/tutorial/export).
 * The page defaults to the local tutorial.html, opened from disk. */
import { createRequire } from "node:module";
import { mkdir, rename, rm, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { spawn } from "node:child_process";
import { once } from "node:events";

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const [cutName = "main", outArg, urlArg] = process.argv.slice(2);
const output = path.resolve(outArg || `build/tutorial/${cutName === "main" ? "project33-bench-manual" : "project33-preflight60"}.mp4`);
const url = (urlArg || pathToFileURL(path.resolve("tutorial.html")).href) + `?embed=1&cut=${cutName}`;
const audio = path.resolve(`assets/tutorial/${cutName === "main" ? "tutorial-mix" : "preflight60-mix"}.m4a`);
const work = path.resolve(process.env.TUTORIAL_WORK || "build/tutorial/export", cutName);
const ffmpeg = process.env.FFMPEG_PATH || "ffmpeg";
const crf = process.env.TUTORIAL_CRF || "18";
const fps = 24;

async function exists(p) { try { await stat(p); return true; } catch { return false; } }
function run(args) {
  return new Promise((resolve, reject) => {
    const p = spawn(ffmpeg, args, { stdio: ["ignore", "ignore", "pipe"], windowsHide: true });
    let err = ""; p.stderr.on("data", (d) => { err = (err + d).slice(-3000); });
    p.on("close", (code) => (code === 0 ? resolve() : reject(new Error(err))));
  });
}

await mkdir(work, { recursive: true });
await mkdir(path.dirname(output), { recursive: true });
const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}) });
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 });
  await page.goto(url, { waitUntil: "load" });
  await page.waitForFunction(() => !!globalThis.project33Tutorial);
  const cut = await page.evaluate(async () => {
    const T = globalThis.project33Tutorial;
    await T.ready();
    const c = document.createElement("canvas");
    c.width = T.cut.width; c.height = T.cut.height;
    globalThis.__capture = (t) => { T.renderAt(t, c); return c.toDataURL("image/jpeg", 0.95); };
    return { width: T.cut.width, height: T.cut.height, duration: T.cut.duration, scenes: T.cut.scenes };
  });
  const total = Math.round(cut.duration * fps);
  const parts = [];
  for (const [i, sc] of cut.scenes.entries()) {
    const f0 = Math.round(sc.start * fps), f1 = i === cut.scenes.length - 1 ? total : Math.round(sc.end * fps);
    const file = path.join(work, `${String(i).padStart(2, "0")}-${sc.id}.mp4`);
    parts.push(file);
    if (await exists(file)) { console.log(`scene ${sc.id}: already encoded`); continue; }
    const tmp = file.replace(/\.mp4$/, ".part.mp4");
    const enc = spawn(ffmpeg, ["-y", "-f", "image2pipe", "-c:v", "mjpeg", "-framerate", String(fps), "-i", "-",
      "-c:v", "libx264", "-preset", "medium", "-crf", crf, "-tune", "film", "-pix_fmt", "yuv420p",
      "-r", String(fps), "-g", "48", "-video_track_timescale", "24000", tmp], { stdio: ["pipe", "ignore", "pipe"], windowsHide: true });
    let encErr = ""; enc.stderr.on("data", (d) => { encErr = (encErr + d).slice(-3000); });
    enc.stdin.on("error", () => {});
    const done = once(enc, "close");
    let last = -1, jpeg = null;
    for (let f = f0; f < f1; f++) {
      const t = f / fps, drawing = Math.floor(t * 12 + 1e-6);
      // Animation is on twos: frames that share a drawing are identical by construction.
      if (drawing !== last) {
        const data = await page.evaluate((tt) => globalThis.__capture(tt), t);
        jpeg = Buffer.from(data.slice(data.indexOf(",") + 1), "base64");
        last = drawing;
      }
      if (!enc.stdin.write(jpeg)) await once(enc.stdin, "drain");
    }
    enc.stdin.end();
    const [code] = await done;
    if (code !== 0) throw new Error(`encoder failed on ${sc.id}: ${encErr}`);
    await rename(tmp, file);
    console.log(`scene ${sc.id}: ${f1 - f0} frames`);
  }
  const list = path.join(work, "concat.txt");
  await writeFile(list, parts.map((p) => `file '${p.replace(/'/g, "'\\''")}'`).join("\n") + "\n");
  const video = path.join(work, "picture.mp4");
  await run(["-y", "-f", "concat", "-safe", "0", "-i", list, "-c", "copy", video]);
  if (await exists(audio)) {
    await run(["-y", "-i", video, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "copy", "-movflags", "+faststart", "-shortest", output]);
  } else {
    console.warn(`no soundtrack at ${audio}; exporting picture only`);
    await run(["-y", "-i", video, "-c", "copy", "-movflags", "+faststart", output]);
  }
  console.log(`Exported ${output} (${cut.width}×${cut.height}, ${fps} fps, ${cut.duration.toFixed(2)} s)`);
} finally {
  await browser.close();
}
