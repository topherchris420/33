// Mechanism Lab interaction test. Usage: node tests/lab_browser/mechanism.mjs [baseURL]
// Exercises every control (drive slider, sweep, attempt assembly, variants, depth tabs,
// sandbox), checks the closure residual against the C1 model, fails on console errors.
import { createRequire } from "node:module";
const { chromium } = createRequire(import.meta.url)("playwright");
import assert from "node:assert/strict";

const base = process.argv[2] || "http://localhost:8101";
const shots = process.env.SHOTS || "/tmp/claude-0/shots";
const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const errors = [];

async function open(viewport, opts = {}) {
  const context = await browser.newContext({ viewport, ...opts });
  const page = await context.newPage();
  page.setDefaultTimeout(240000); // software WebGL on a shared CI box can be slow
  page.on("console", (m) => { if (m.type() === "error") errors.push(`console: ${m.text()}`); });
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  await page.goto(`${base}/lab/mechanism.html`, { waitUntil: "networkidle" });
  await page.waitForSelector("#live dd", { timeout: 180000 });
  await page.waitForSelector("#cmp-c5", { timeout: 180000 });
  await page.waitForSelector("#linkage-vp canvas", { timeout: 180000 });
  await page.waitForTimeout(1200);
  return page;
}

async function setRange(page, sel, value) {
  await page.$eval(sel, (el, v) => { el.value = String(v); el.dispatchEvent(new Event("input", { bubbles: true })); el.dispatchEvent(new Event("change", { bubbles: true })); }, value);
  await page.waitForTimeout(80);
}

const page = await open({ width: 1440, height: 900 });

// Record-derived verdict
const verdict = await page.textContent("#mx-verdict");
assert.match(verdict, /CONTRADICTED/);
assert.match(verdict, /0 \/ 47/);
assert.match(verdict, /0 \/ 81/);

// Residual readout against the C1 model: 35.00 mm at 0°, 15.40 mm at 92°
await setRange(page, "#theta", 0);
assert.equal((await page.textContent("#gap-value")).trim(), "35.00 mm");
await setRange(page, "#theta", 92);
const g92 = parseFloat(await page.textContent("#gap-value"));
assert.ok(Math.abs(g92 - 15.4) < 0.01, `gap at 92 deg: ${g92}`);
assert.match(await page.textContent("#live"), /0 \/ 47 \(JSON\)/);
await page.screenshot({ path: `${shots}/mechanism-desktop-stage.png` });

// Chart reflects the cursor
assert.match(await page.textContent("#residual-chart"), /ε = 15\.40 mm/);
assert.match(await page.textContent("#residual-chart"), /max in range 29\.6 mm/);
assert.match(await page.textContent("#residual-chart"), /40\.0 mm/);

// Sweep plays and pauses
await setRange(page, "#theta", 0);
await page.click("#play");
await page.waitForTimeout(900);
const moved = parseFloat(await page.textContent("#theta-out"));
assert.ok(moved > 0, `sweep should advance theta, got ${moved}`);
assert.equal(await page.getAttribute("#play", "aria-pressed"), "true");
await page.click("#play");
assert.equal(await page.getAttribute("#play", "aria-pressed"), "false");

// Labels toggle
await page.click("#labels");
assert.equal(await page.getAttribute("#labels", "aria-pressed"), "false");
await page.click("#labels");

// View tools
await page.click("#vp-tools button:nth-child(2)");
await page.waitForTimeout(800);
await page.click("#vp-tools button:nth-child(1)");
await page.waitForTimeout(300);

// Attempt assembly: technical panel opens, scene pauses, the gap remains
await setRange(page, "#theta", 46);
const before = (await page.textContent("#gap-value")).trim();
await page.click("#attempt");
await page.waitForSelector("#tech:not([hidden])", { timeout: 60000 });
assert.equal(await page.isVisible("#paused"), true);
const techText = await page.textContent("#tech");
for (const id of ["C1", "R-C1-CLOSURE", "D-002", "D-004", "D-005"]) assert.ok(techText.includes(id), `tech panel should link ${id}`);
assert.equal((await page.textContent("#gap-value")).trim(), before, "the scene must not repair itself");
await page.waitForTimeout(600);
await page.screenshot({ path: `${shots}/mechanism-desktop-attempt.png` });
await page.click("#tech button");
assert.equal(await page.isHidden("#tech"), true);
assert.equal(await page.isHidden("#paused"), true);

// Variant explorer: 81 buttons, each from the JSON; clicking loads geometry
assert.equal(await page.locator(".mx-vbtn").count(), 81);
const labels = await page.$$eval(".mx-vbtn", (bs) => bs.map((b) => b.firstChild.textContent));
assert.ok(labels.every((t) => t === "0/47"), "every committed variant reports 0/47");
await page.locator(".mx-vbtn").nth(0).click();
await page.waitForTimeout(200);
assert.match(await page.textContent("#live"), /a 20 · c 55 · b 12 · d 12 mm/);
await page.locator(".mx-vbtn.baseline").click();

// Depth tabs
const tabs = page.locator("#math-panel [role=tab]");
assert.equal(await tabs.count(), 3);
for (let i = 0; i < 3; i++) {
  await tabs.nth(i).click();
  assert.equal(await tabs.nth(i).getAttribute("aria-selected"), "true");
}
assert.match(await page.textContent("#math-panel"), /sha256/);
await tabs.nth(1).click();
await page.waitForSelector("#math-panel .katex", { timeout: 60000 });

// Sandbox: sliders, presets, heat map
await page.click('[data-preset="fusion"]');
assert.match(await page.textContent("#sb-out"), /47 \/ 47/);
await page.click('[data-preset="baseline"]');
assert.match(await page.textContent("#sb-out"), /0 \/ 47/);
await setRange(page, "#sb-c", 20);
assert.match(await page.textContent("#sb-out"), /47 \/ 47/);
for (const k of ["a", "b", "d", "theta"]) await setRange(page, `#sb-${k}`, await page.$eval(`#sb-${k}`, (el) => el.value));
assert.match(await page.textContent("#sandbox"), /14\.6 mm ≤ c ≤ 25\.0 mm/);
const box = await page.locator(".mx-heat canvas").boundingBox();
await page.mouse.click(box.x + box.width * 0.3, box.y + box.height * 0.5);
await page.waitForTimeout(100);

// Comparison studio content from the record
const cmp = await page.textContent("#compare");
for (const t of ["MODELS DISAGREE", "LAB-OBS-1", "D-006", "D-007", "D-008", "D-009", "D-010", "18.99", "NOT MEASURED"]) assert.ok(cmp.includes(t), `comparison should include ${t}`);
assert.equal(await page.locator(".mx-transcribed.no").count(), 0, "every D-010 transcription matches the record text");

for (const id of ["investigation", "sandbox", "comparison"]) {
  await page.locator(`#${id}`).scrollIntoViewIfNeeded();
  await page.waitForTimeout(250);
  await page.screenshot({ path: `${shots}/mechanism-desktop-${id}.png`, fullPage: false });
}
await page.locator("#cmp-c5").screenshot({ path: `${shots}/mechanism-desktop-c5.png` });
await page.locator("#cmp-d009").screenshot({ path: `${shots}/mechanism-desktop-d009.png` });
await page.screenshot({ path: `${shots}/mechanism-desktop-full.png`, fullPage: true });

// Keyboard: the drive slider responds to arrow keys
await page.focus("#theta");
await setRange(page, "#theta", 10);
await page.keyboard.press("ArrowRight");
assert.equal((await page.textContent("#theta-out")).trim(), "10.5°");

// Mobile: no horizontal scroll, stage renders
const mobile = await open({ width: 390, height: 844 }, { deviceScaleFactor: 2, isMobile: true, hasTouch: true });
const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
assert.ok(overflow <= 0, `horizontal overflow on mobile: ${overflow}px`);
await mobile.screenshot({ path: `${shots}/mechanism-mobile.png` });
await mobile.locator("#investigation").scrollIntoViewIfNeeded();
await mobile.screenshot({ path: `${shots}/mechanism-mobile-stage.png` });
await mobile.locator("#comparison").scrollIntoViewIfNeeded();
await mobile.screenshot({ path: `${shots}/mechanism-mobile-compare.png` });

// Reduced motion: sweep steps discretely, attempt resolves without animation
const rm = await open({ width: 1280, height: 800 }, { reducedMotion: "reduce" });
await rm.click("#attempt");
await rm.waitForSelector("#tech:not([hidden])", { timeout: 30000 });

await browser.close();
if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log("mechanism lab: all interactions passed");
