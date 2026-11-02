// Browser tests for the Historical Aerospace Instrumentation Lab (lab/instruments.html).
// Run: node --test tests/lab_browser/instruments.mjs   (SHOTS=dir to save screenshots)
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFileSync, statSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, extname, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const require = createRequire(import.meta.url);
const SHOTS = process.env.SHOTS || "";
const TIMEOUT = Number(process.env.LAB_TIMEOUT || 300000);
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".woff2": "font/woff2" };
let server, base, browser;

before(async () => {
  base = await new Promise((resolve) => {
    server = createServer((req, res) => {
      const path = normalize(join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname)));
      if (!path.startsWith(ROOT)) { res.writeHead(403).end(); return; }
      try {
        const file = statSync(path).isDirectory() ? join(path, "index.html") : path;
        res.writeHead(200, { "content-type": TYPES[extname(file)] || "application/octet-stream" });
        res.end(readFileSync(file));
      } catch { res.writeHead(404).end(); }
    }).listen(0, "127.0.0.1", () => resolve(`http://127.0.0.1:${server.address().port}`));
  });
  const { chromium } = require("playwright");
  browser = await chromium.launch({ channel: process.env.LAB_BROWSER_CHANNEL || undefined, args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
});
after(async () => { await browser?.close(); server?.close(); });

async function open(viewport = { width: 1440, height: 900 }, opts = {}) {
  const page = await browser.newPage({ viewport, ...opts });
  page.setDefaultTimeout(TIMEOUT);
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("requestfailed", (r) => errors.push(`request failed: ${r.url()}`));
  await page.goto(`${base}/lab/instruments.html`);
  await page.waitForFunction(() => document.body.dataset.ready === "true", null, { timeout: TIMEOUT, polling: 500 });
  return { page, errors };
}

test("historical exhibits reproduce nothing from the restricted manual and say so", () => {
  const html = readFileSync(join(ROOT, "lab/instruments.html"), "utf8");
  assert.match(html, /reproduction for non-military use is not permitted/);
  assert.match(html, /not an F-117A display format/);
  const js = ["symbology.js", "cockpit.js", "infoarch.js", "dependency.js", "main.js"].map((f) => readFileSync(join(ROOT, "lab/js/instruments", f), "utf8")).join("\n");
  // No identifiers of that aircraft's systems appear in the exhibit code.
  for (const term of ["OCIP", "CMDI", "PAARS", "FAAD", "SMS ", "WSC", "TO 1F-117A"]) assert.ok(!js.includes(term), `exhibit code mentions ${term}`);
});

test("instrumentation lab: cockpit, declutter, information chain, dependencies", { timeout: TIMEOUT * 3 }, async () => {
  const model = JSON.parse(readFileSync(join(ROOT, "protocol/ground_status_model.json"), "utf8"));
  const { page, errors } = await open();
  assert.match(await page.textContent(".in-rights"), /nothing from it is reproduced/i);

  // Cockpit exhibit: fly to each display and back.
  await page.locator("#ck-viewport").evaluate((e) => e.scrollIntoView({ block: "center" }));
  await page.waitForFunction(() => document.querySelector("#ck-viewport").dataset.compiled === "true", null, { timeout: TIMEOUT, polling: 500 });
  for (const [id, title] of [["hud", /Head-up display concepts/], ["map", /Navigation display/], ["status", /Status and advisory/]]) {
    await page.click(`[data-display='${id}']`);
    assert.equal(await page.locator(`[data-display='${id}']`).getAttribute("aria-pressed"), "true");
    assert.match(await page.textContent("#ck-explain"), title);
  }
  await page.locator("#ck-explain [role='tab']", { hasText: "Engineering" }).click();
  await page.waitForFunction(() => document.querySelector("#ck-explain .katex, #ck-explain code"));
  if (SHOTS) { mkdirSync(SHOTS, { recursive: true }); await page.waitForTimeout(1500); await page.screenshot({ path: join(SHOTS, "instruments-desktop-status-display.png") }); }
  await page.click("#ck-back");
  assert.equal(await page.locator("#ck-back").isDisabled(), true);

  // Declutter changes what the displays draw.
  await page.locator("#declutter").fill("1");
  assert.match(await page.textContent("#declutter-out"), /level 1/);
  assert.match(await page.textContent("#ck-explain"), /Declutter level 1 · 5 elements/);
  await page.locator("#declutter").fill("5");
  assert.match(await page.textContent("#ck-explain"), /23 elements drawn of 23/);
  await page.locator("#declutter").fill("3");

  // Information chain: every source × state renders every stage.
  for (const src of ["airdata", "inertial", "gnss"]) {
    for (const st of ["missing", "stale", "inconsistent", "unavailable", "nominal"]) {
      await page.click(`button[data-source='${src}'][data-state='${st}']`);
      assert.equal(await page.locator(`.ia-row[data-source='${src}']`).getAttribute("data-state"), st);
    }
  }
  await page.click("button[data-source='inertial'][data-state='unavailable']");
  const msgs = await page.evaluate(() => window.__p33instruments.store.get().messages.map((m) => m.text));
  assert.ok(msgs.includes("WARNING IRS FAIL"), msgs.join(","));
  assert.match(await page.textContent(".ia-row[data-source='inertial'] .ia-cell[data-stage='3']"), /symbol removed/);
  await page.click("button[data-source='gnss'][data-state='stale']");
  const age0 = await page.evaluate(() => window.__p33instruments.store.get().sources.gnss.age);
  await page.waitForTimeout(800);
  assert.ok((await page.evaluate(() => window.__p33instruments.store.get().sources.gnss.age)) > age0, "stale age grows");
  const held = await page.evaluate(() => {
    const s = window.__p33instruments.store;
    s.setSource('inertial', 'stale');
    const before = s.get(); s.tick(1);
    return { before: before.displayState.roll, after: s.get().displayState.roll };
  });
  assert.equal(held.after, held.before, 'aged attitude holds the last valid sample');
  for (const tab of ["Engineering", "Terms", "Introduction"]) await page.locator("#ia-depth [role='tab']", { hasText: tab }).click();
  if (SHOTS) { await page.locator(".ia-panel").evaluate((e) => e.scrollIntoView()); await page.waitForTimeout(500); await page.screenshot({ path: join(SHOTS, "instruments-desktop-chain.png") }); }
  await page.click("button[data-source='inertial'][data-state='nominal']");
  await page.click("button[data-source='gnss'][data-state='nominal']");

  // Generic dependency graph: fail bus A.
  await page.click(".dep-node[data-node='busA']");
  assert.equal(await page.locator(".dep-node[data-node='busA']").getAttribute("aria-pressed"), "true");
  assert.equal(await page.locator(".dep-node[data-node='fAir']").getAttribute("data-status"), "lost");
  assert.equal(await page.locator(".dep-node[data-node='fAtt']").getAttribute("data-status"), "degraded");
  await page.locator(".dep-node[data-node='busB']").focus();
  await page.keyboard.press("Enter");
  assert.equal(await page.locator(".dep-node[data-node='fAtt']").getAttribute("data-status"), "lost");
  await page.click("#dep-generic-reset");
  assert.equal(await page.locator(".dep-node[data-node='fAtt']").getAttribute("data-status"), "ok");

  // Project 33 ground status: fail the IMU — telemetry is lost, the physical switch abort survives.
  await page.click(".gs-unit[data-unit='IMU']");
  const lost = new Set(model.channels.filter((c) => c.requires.includes("IMU")).map((c) => c.id));
  for (const c of model.channels) {
    assert.equal(await page.locator(`.gs-item[data-id='${c.id}']`).getAttribute("data-available"), String(!lost.has(c.id)), c.id);
  }
  assert.equal(await page.locator(".gs-item[data-id='switch_abort']").getAttribute("data-available"), "true");

  await page.click('#config-example');
  assert.match(await page.textContent('#config-result'), /SYNTHETIC EXAMPLE/);
  assert.match(await page.textContent('#config-result'), /1 changed/);
  assert.equal(await page.locator('#config-result [data-config-state="unknown"]').count(), 1);
  if (SHOTS) { mkdirSync(SHOTS, { recursive: true }); await page.locator('#config-title').scrollIntoViewIfNeeded(); await page.screenshot({ path: join(SHOTS, 'configuration-desktop.png') }); }
  const plan = { schema: 'project33.bench_plan/1', scope: 'stationary_inert_demonstrator', hardware_revision: 'test', specimen: { id: 'test' }, source_snapshot: [{ path: 'test.py', sha256: 'a'.repeat(64) }], installed_firmware: [{ id: 'rocket', sha256: null }] };
  await page.setInputFiles('#config-left', { name: 'left.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(plan)) });
  await page.setInputFiles('#config-right', { name: 'right.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(plan)) });
  await page.click('#config-compare');
  await page.waitForFunction(() => document.querySelector('#config-result').textContent.includes('LOCAL DECLARATIONS'));
  assert.match(await page.textContent('#config-result'), /3 matched/);
  await page.setInputFiles('#config-right', { name: 'invalid.json', mimeType: 'application/json', buffer: Buffer.from('{}') });
  await page.click('#config-compare');
  await page.waitForSelector('#config-result [role="alert"]');
  const usb = { schema: 'project33.monitor_report/1', elapsed_s: 1, origins: ['synthetic'], boots: [{ role: 'rocket', boot: '0123456789abcdef', identity_comparison: 'UNKNOWN', system: null, sensors: { mpu6050: { status: 'INVALID', valid: false, age_s: 0.5, values: { ax: null }, units: { ax: 'm/s^2' } } } }] };
  await page.setInputFiles('#usb-report-file', { name: 'report.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(usb)) });
  await page.waitForSelector('[data-usb-status="INVALID"]');
  assert.match(await page.textContent('#usb-report-result'), /synthetic/);
  assert.match(await page.textContent('#usb-report-result'), /NOT REPORTED/);
  if (SHOTS) { await page.locator('[data-usb-status="INVALID"]').scrollIntoViewIfNeeded(); await page.screenshot({ path: join(SHOTS, 'usb-monitor-desktop.png') }); }
  await page.setInputFiles('#usb-report-file', { name: 'invalid.json', mimeType: 'application/json', buffer: Buffer.from('{}') });
  await page.waitForSelector('#usb-report-result [role="alert"]');
  await page.click(".gs-unit[data-unit='LAUNCHER']");
  assert.equal(await page.locator(".gs-item[data-id='switch_abort']").getAttribute("data-available"), "false");
  await page.locator(".gs-item[data-id='switch_abort'] summary").click();
  assert.match(await page.textContent(".gs-item[data-id='switch_abort']"), /Firmware\/Launcher\/src\/main\.cpp/);
  if (SHOTS) { await page.locator(".dep-grid").evaluate((e) => e.scrollIntoView()); await page.waitForTimeout(500); await page.screenshot({ path: join(SHOTS, "instruments-desktop-dependencies.png") }); }
  await page.click("#gs-reset");
  assert.equal(await page.locator(".gs-item[data-id='switch_abort']").getAttribute("data-available"), "true");

  if (SHOTS) {
    await page.evaluate(() => window.scrollTo(0, 0)); await page.waitForTimeout(400);
    await page.screenshot({ path: join(SHOTS, "instruments-desktop-top.png") });
    await page.locator(".ck-grid").evaluate((e) => e.scrollIntoView({ block: "start" })); await page.evaluate(() => window.scrollBy(0, -70)); await page.waitForTimeout(2500);
    await page.screenshot({ path: join(SHOTS, "instruments-desktop-cockpit.png") });
  }
  assert.deepEqual(errors, []);
  await page.close();
});

test("instrumentation lab: mobile layout has no horizontal page scroll", { timeout: TIMEOUT * 2 }, async () => {
  const { page, errors } = await open({ width: 390, height: 844 }, { isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  await page.click('#config-example');
  if (SHOTS) { mkdirSync(SHOTS, { recursive: true }); await page.locator('#config-title').scrollIntoViewIfNeeded(); await page.screenshot({ path: join(SHOTS, 'configuration-mobile.png') }); }
  const overflow = await page.evaluate(() => [...document.querySelectorAll("main *")].filter((e) => e.getBoundingClientRect().right > document.documentElement.clientWidth + 1 && !e.closest(".ia-grid, .dep-host, .viewport")).map((e) => e.className || e.tagName).slice(0, 5));
  assert.deepEqual(overflow, []);
  if (SHOTS) {
    mkdirSync(SHOTS, { recursive: true });
    await page.screenshot({ path: join(SHOTS, "instruments-mobile-top.png") });
    await page.locator("#ck-viewport").evaluate((e) => e.scrollIntoView({ block: "start" })); await page.waitForTimeout(2500);
    await page.screenshot({ path: join(SHOTS, "instruments-mobile-cockpit.png") });
    await page.locator(".dep-grid").evaluate((e) => e.scrollIntoView()); await page.waitForTimeout(400);
    await page.screenshot({ path: join(SHOTS, "instruments-mobile-dependencies.png") });
  }
  assert.deepEqual(errors, []);
  await page.close();
});
