// Browser tests for the Telemetry Theater (lab/telemetry.html).
// Run: node --test tests/lab_browser/telemetry.mjs
// Starts its own static server over the repository root and drives Chromium via Playwright.
// Every control on the page is exercised; console errors and page errors fail the run.
// SHOTS=dir also writes desktop (1440×900) and mobile (390×844) screenshots.
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFileSync, readdirSync, statSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, extname, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const require = createRequire(import.meta.url);
const SHOTS = process.env.SHOTS || "";
const TIMEOUT = Number(process.env.LAB_TIMEOUT || 300000);
const GL_ARGS = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"];
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".woff2": "font/woff2", ".csv": "text/csv" };

let server, base, browser;

function serve() {
  return new Promise((resolve) => {
    server = createServer((req, res) => {
      const url = decodeURIComponent(new URL(req.url, "http://x").pathname);
      const path = normalize(join(ROOT, url));
      if (!path.startsWith(ROOT)) { res.writeHead(403).end(); return; }
      try {
        const file = statSync(path).isDirectory() ? join(path, "index.html") : path;
        res.writeHead(200, { "content-type": TYPES[extname(file)] || "application/octet-stream" });
        res.end(readFileSync(file));
      } catch { res.writeHead(404).end(); }
    }).listen(0, "127.0.0.1", () => resolve(`http://127.0.0.1:${server.address().port}`));
  });
}

function listSources(dir) {
  return readdirSync(join(ROOT, dir)).filter((f) => f.endsWith(".js")).map((f) => join(dir, f));
}

const FORBIDDEN = [
  [/new\s+WebSocket\b/, "WebSocket"], [/navigator\s*\.\s*serial/, "WebSerial"], [/navigator\s*\.\s*usb/, "WebUSB"],
  [/navigator\s*\.\s*bluetooth/, "WebBluetooth"], [/\bEventSource\b/, "EventSource"], [/RTCPeerConnection/, "WebRTC"],
  [/WebTransport/, "WebTransport"], [/sendBeacon/, "sendBeacon"], [/fetch\s*\(\s*["'`]https?:/, "absolute fetch"],
  [/XMLHttpRequest/, "XMLHttpRequest"],
];

test("telemetry and instrument sources contain no transmit or hardware APIs", () => {
  for (const file of [...listSources("lab/js/telemetry"), ...listSources("lab/js/instruments")]) {
    const src = readFileSync(join(ROOT, file), "utf8");
    for (const [re, name] of FORBIDDEN) assert.ok(!re.test(src), `${file} uses ${name}`);
  }
});

before(async () => {
  base = await serve();
  const { chromium } = require("playwright");
  browser = await chromium.launch({ args: GL_ARGS });
});
after(async () => { await browser?.close(); server?.close(); });

async function open(viewport = { width: 1440, height: 900 }, opts = {}) {
  const page = await browser.newPage({ viewport, ...opts });
  page.setDefaultTimeout(TIMEOUT);
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("requestfailed", (r) => errors.push(`request failed: ${r.url()}`));
  await page.goto(`${base}/lab/telemetry.html`);
  await page.waitForFunction(() => document.body.dataset.ready === "true", null, { timeout: TIMEOUT, polling: 500 });
  return { page, errors };
}

const pressed = (page, sel) => page.locator(sel).first().getAttribute("aria-pressed");

test("theater: fixture audit, plot controls, processing, replay, generator, architecture", { timeout: TIMEOUT * 3 }, async () => {
  const fixture = JSON.parse(readFileSync(join(ROOT, "lab/data/telemetry_fixture.json"), "utf8"));
  const { page, errors } = await open();

  // Dataset A: one annotation per audit detail, carrying the audit's own line numbers.
  const lines = await page.$$eval(".audit-anno[data-line]", (els) => els.map((e) => Number(e.dataset.line)));
  assert.deepEqual(lines, fixture.audit.details.map((d) => d.line));
  assert.equal(await page.locator("#tt-limitations li").count(), fixture.audit.limitations.length);
  assert.ok((await page.textContent("#kinds")).includes("accepted inert measurements"));

  // Annotation focus zooms the plot to the flagged row.
  const span = () => page.evaluate(() => { const v = window.__p33telemetry.plot.view; return v[1] - v[0]; });
  const full = await span();
  await page.locator(".audit-anno[data-line='6']").click();
  assert.match(await page.textContent("#tt-readout"), /line 6/);
  assert.ok((await span()) < full);

  // Zoom buttons, wheel, keyboard, reset.
  await page.click("#zoom-reset");
  const s0 = await span();
  await page.click("#zoom-in");
  assert.ok((await span()) < s0);
  await page.click("#zoom-out");
  await page.locator("#plot").hover();
  await page.mouse.wheel(0, -300);
  await page.locator("#plot").focus();
  await page.keyboard.press("0");
  assert.ok(Math.abs((await span()) - s0) < 1e-9);
  await page.locator("#plot").dblclick();

  // Streams and clock domains.
  await page.click("[data-stream='LOG']");
  assert.equal(await pressed(page, "[data-stream='LOG']"), "true");
  await page.click("[data-xaxis='device']");
  assert.equal(await page.evaluate(() => window.__p33telemetry.state.xAxis), "device");
  await page.click("[data-stream='both']");
  assert.equal(await page.evaluate(() => window.__p33telemetry.state.xAxis), "received");
  assert.equal(await page.locator("[data-xaxis='device']").isDisabled(), true);
  await page.click("[data-stream='T']");

  // Lanes.
  for (const ch of ["roll", "rate", "servo", "dt"]) {
    await page.click(`[data-channel='${ch}']`);
    assert.equal(await pressed(page, `[data-channel='${ch}']`), "false");
    await page.click(`[data-channel='${ch}']`);
  }

  // Processing: moving average, EMA α (time constant readout), raw only, raw toggle.
  await page.click("[data-filter='ma']");
  assert.equal(await page.locator("#window-field").isVisible(), true);
  await page.locator("#window").fill("9");
  assert.match(await page.textContent("#window-out"), /9 samples/);
  await page.click("[data-filter='ema']");
  await page.locator("#alpha").fill("0.5");
  assert.match(await page.textContent("#tau-out"), /τ = 72 ms/);
  await page.click("[data-filter='none']");
  await page.click("#opt-raw");
  assert.equal(await pressed(page, "#opt-raw"), "false");
  await page.click("#opt-raw");
  await page.click("[data-filter='ema']");

  // Replay (read-only): play, pause, scrub, speed, show all.
  await page.selectOption("#replay-speed", "4");
  await page.click("#replay-play");
  await page.waitForFunction(() => window.__p33telemetry.state.replay.t > 0, null, { timeout: 30000 });
  await page.click("#replay-play");
  await page.locator("#replay-scrub").fill("0.12");
  assert.match(await page.textContent("#replay-count"), /^3 of 9 rows/);
  await page.click("#replay-end");
  assert.match(await page.textContent("#replay-count"), /^9 of 9 rows/);

  // Dataset B: declared generator with seed, uncertainty band, truth, spectrum.
  await page.click("[data-dataset='B']");
  assert.equal(await page.evaluate(() => window.__p33telemetry.state.dataset), "B");
  const first = await page.evaluate(() => window.__p33telemetry.B.rows.slice(0, 5).map((r) => r.raw).join("|"));
  await page.locator("#gen-seed").fill("7");
  await page.locator("#gen-seed").dispatchEvent("change");
  const second = await page.evaluate(() => window.__p33telemetry.B.rows.slice(0, 5).map((r) => r.raw).join("|"));
  assert.notEqual(first, second);
  assert.equal(await page.evaluate(() => window.__p33telemetry.B.params.seed), 7);
  await page.locator("#gen-dropProb").fill("0.1");
  assert.ok(await page.evaluate(() => window.__p33telemetry.B.stats.dropped > 5));
  await page.click("#opt-band");
  assert.equal(await pressed(page, "#opt-band"), "false");
  await page.click("#opt-band");
  await page.click("#opt-truth");
  assert.equal(await pressed(page, "#opt-truth"), "true");
  assert.match(await page.textContent("#fft-note"), /Hann-windowed/);
  assert.equal(await page.locator("#tt-fft").getAttribute("data-disabled"), "false");
  if (SHOTS) { mkdirSync(SHOTS, { recursive: true }); await page.locator(".tt-grid").evaluate((e) => e.scrollIntoView()); await page.screenshot({ path: join(SHOTS, "telemetry-desktop-theater-B.png") }); }
  await page.click("[data-dataset='A']");

  // Architecture: inspection only.
  await page.locator("#arch-viewport").evaluate((e) => e.scrollIntoView({ block: "center" }));
  await page.waitForFunction(() => document.querySelector("#arch-viewport").dataset.compiled === "true", null, { timeout: TIMEOUT, polling: 500 });
  await page.click("[data-node='imu']");
  assert.equal(await page.locator(".arch-inspect").getAttribute("data-selected"), "imu");
  const inspector = await page.textContent("#arch-inspector");
  assert.match(inspector, /G-08/);
  assert.match(inspector, /Rocket telemetry/);
  await page.click("[data-node='launcher']");
  assert.match(await page.textContent("#arch-inspector"), /does not have/);
  await page.click("#arch-pulses");
  assert.equal(await pressed(page, "#arch-pulses"), "false");
  await page.click("#arch-commands");
  assert.equal(await pressed(page, "#arch-commands"), "false");
  await page.click("#arch-commands");
  await page.click("#arch-reset");
  assert.match(await page.textContent(".arch-banner"), /no transmit path/);

  // No control resembles a command: any button naming a command verb must be an inspection entry.
  const labels = await page.$$eval("button", (bs) => bs.map((b) => b.textContent.trim()));
  for (const text of labels) {
    if (/\b(arm|disarm|launch|ignite|ignition|fire|abort)\b/i.test(text)) assert.match(text, /^Inspect · /, `button "${text}"`);
  }

  if (SHOTS) {
    await page.locator(".arch-grid").evaluate((e) => e.scrollIntoView({ block: "start" }));
    await page.evaluate(() => window.scrollBy(0, -70));
    await page.waitForTimeout(2500);
    await page.screenshot({ path: join(SHOTS, "telemetry-desktop-architecture.png") });
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(400);
    await page.screenshot({ path: join(SHOTS, "telemetry-desktop-top.png") });
    await page.locator(".tt-grid").evaluate((e) => e.scrollIntoView());
    await page.waitForTimeout(400);
    await page.screenshot({ path: join(SHOTS, "telemetry-desktop-theater-A.png") });
  }
  assert.deepEqual(errors, []);
  await page.close();
});

test("theater: mobile layout has no horizontal scroll", { timeout: TIMEOUT * 2 }, async () => {
  const { page, errors } = await open({ width: 390, height: 844 }, { isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  const overflow = await page.evaluate(() => [...document.querySelectorAll("main *")].filter((e) => e.getBoundingClientRect().right > document.documentElement.clientWidth + 1 && !e.closest(".ia-grid, .dep-host, .viewport")).map((e) => e.className || e.tagName).slice(0, 5));
  assert.deepEqual(overflow, [], "elements wider than the viewport in main");
  if (SHOTS) {
    mkdirSync(SHOTS, { recursive: true });
    await page.screenshot({ path: join(SHOTS, "telemetry-mobile-top.png") });
    await page.locator(".tt-grid").evaluate((e) => e.scrollIntoView());
    await page.waitForTimeout(400);
    await page.screenshot({ path: join(SHOTS, "telemetry-mobile-theater.png") });
  }
  assert.deepEqual(errors, []);
  await page.close();
});
