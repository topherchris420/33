// Render the opening film to MP4 by seeking the deterministic timeline frame by frame.
//   python tools/serve_lab.py 8000 &
//   node tools/render_lab_film.mjs [out.mp4] [fps=24] [width=1280] [from=0] [to=80] [baseURL]
// The film is a pure function of time, so every frame is exact regardless of render speed.
// Each frame captures the whole stage: 3D view, captions, overlays, letterbox, grain, vignette.
// The soundtrack is the same Web Audio cue sheet the page plays, rendered with an
// OfflineAudioContext. The narration uses the viewer's speech voice live and is not recorded;
// the captions carry it instead.
//   FILM_AUDIO=none  renders video only;  FILM_AUDIO=only  writes the soundtrack to <out> as WAV.
// Long renders can be split into ranges, concatenated, then muxed with the full soundtrack.
import { createRequire } from "node:module";
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
const { chromium } = createRequire(import.meta.url)("playwright");

const [out = "build/project33-living-lab.mp4", fpsArg = "24", widthArg = "1280", fromArg = "0", toArg = "80", base = "http://localhost:8000"] = process.argv.slice(2);
const fps = Number(fpsArg), width = Number(widthArg), height = Math.round((width * 9) / 16);
const from = Number(fromArg), to = Number(toArg);
const audioMode = process.env.FILM_AUDIO || "mux";
mkdirSync(dirname(out) || ".", { recursive: true });

const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--autoplay-policy=no-user-gesture-required"] });
const page = await browser.newPage({ viewport: { width, height } });
page.setDefaultTimeout(600000);
page.on("pageerror", (e) => console.error("page error:", e.message));
page.on("console", (m) => { if (/soundtrack/.test(m.text())) console.log(m.text()); });
await page.goto(`${base}/lab/cinematic.html?t=${from}`, { waitUntil: "networkidle" });
await page.waitForFunction(() => window.__film, null, { timeout: 600000 });
// Film-only presentation: no site header, no controls or start card, the stage fills the frame.
await page.addStyleTag({ content: `
  #shell-header, .lab-header, .skip, #start, .cine-controls { display: none !important; }
  body.cine { --header-h: 0px; }
  .cine-stage { height: 100vh !important; }
  *, *::before, *::after { animation: none !important; transition: none !important; caret-color: transparent !important; }
` });
await page.evaluate(() => window.dispatchEvent(new Event("resize")));
await page.waitForTimeout(500);
const box = await page.locator("#main").boundingBox();
if (Math.round(box.width) !== width || Math.round(box.height) !== height) throw new Error(`stage is ${box.width}×${box.height}, expected ${width}×${height}`);

// Soundtrack: render the cue sheet offline, trimmed to [from, to].
const SR = 48000;
const wavB64 = audioMode === "none" ? null : await page.evaluate(async ({ from, to, SR }) => {
  const { FilmAudio } = await import(new URL("js/cinematic/audio.js", location.href).href);
  const a = new FilmAudio();
  const lead = 0.05; // FilmAudio.seek schedules cues 50 ms after "now"
  const ctx = new OfflineAudioContext(2, Math.ceil(SR * (to - from + lead + 0.1)), SR);
  a.ctx = ctx;
  a.master = ctx.createGain();
  a.master.gain.value = 0.8;
  const comp = ctx.createDynamicsCompressor();
  a.master.connect(comp).connect(ctx.destination);
  const len = SR * 2;
  a.noise = ctx.createBuffer(1, len, SR);
  const d = a.noise.getChannelData(0);
  let seed = 33; // deterministic noise so renders are repeatable
  for (let i = 0; i < len; i++) { seed = (seed * 1664525 + 1013904223) >>> 0; d[i] = (seed / 4294967296) * 2 - 1; }
  a.enabled = true;
  a.seek(from, true);
  const buf = await ctx.startRendering();
  const start = Math.round(lead * SR), frames = Math.round((to - from) * SR);
  const L = buf.getChannelData(0), R = buf.getChannelData(1);
  const bytes = new ArrayBuffer(44 + frames * 4), v = new DataView(bytes);
  const str = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  str(0, "RIFF"); v.setUint32(4, 36 + frames * 4, true); str(8, "WAVE"); str(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 2, true); v.setUint32(24, SR, true);
  v.setUint32(28, SR * 4, true); v.setUint16(32, 4, true); v.setUint16(34, 16, true); str(36, "data"); v.setUint32(40, frames * 4, true);
  let peak = 0;
  for (let i = 0; i < frames; i++) {
    const l = L[start + i] || 0, r = R[start + i] || 0;
    peak = Math.max(peak, Math.abs(l), Math.abs(r));
    v.setInt16(44 + i * 4, Math.max(-1, Math.min(1, l)) * 32767, true);
    v.setInt16(46 + i * 4, Math.max(-1, Math.min(1, r)) * 32767, true);
  }
  console.log(`soundtrack peak ${peak.toFixed(3)}`);
  let bin = "";
  const u8 = new Uint8Array(bytes);
  for (let i = 0; i < u8.length; i += 0x8000) bin += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000));
  return btoa(bin);
}, { from, to, SR });
if (audioMode === "only") {
  writeFileSync(out, Buffer.from(wavB64, "base64"));
  await browser.close();
  console.log(`wrote ${out}`);
  process.exit(0);
}
const wav = wavB64 && join(dirname(out) || ".", `.soundtrack-${process.pid}.wav`);
if (wav) writeFileSync(wav, Buffer.from(wavB64, "base64"));

const audioArgs = wav ? ["-i", wav, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest"] : [];
const ffmpeg = spawn("ffmpeg", ["-y", "-loglevel", "error",
  "-f", "image2pipe", "-framerate", String(fps), "-i", "-", ...audioArgs,
  "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], { stdio: ["pipe", "inherit", "inherit"] });
const total = Math.round((to - from) * fps);
const started = Date.now();
for (let i = 0; i < total; i++) {
  const t = from + i / fps;
  await page.evaluate((x) => window.__film.seek(x), t);
  const png = await page.locator("#main").screenshot({ type: "png" });
  if (!ffmpeg.stdin.write(png)) await new Promise((r) => ffmpeg.stdin.once("drain", r));
  if (i % fps === 0) {
    const rate = (i + 1) / ((Date.now() - started) / 1000);
    process.stdout.write(`${t.toFixed(1)} s / ${to} s  (${rate.toFixed(2)} frames/s)\n`);
  }
}
ffmpeg.stdin.end();
const code = await new Promise((r) => ffmpeg.on("close", r));
if (wav) rmSync(wav, { force: true });
await browser.close();
if (code !== 0) { console.error(`ffmpeg exited with ${code}`); process.exit(1); }
console.log(`wrote ${out}`);
