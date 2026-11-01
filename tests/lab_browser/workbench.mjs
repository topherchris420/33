// Workbench interaction test. Usage: node tests/lab_browser/workbench.mjs [baseURL]
// Exercises every toolbar control and asserts real scene changes; fails on console errors.
import { createRequire } from "node:module";
const { chromium } = createRequire(import.meta.url)("playwright");
import assert from "node:assert/strict";

const base = process.argv[2] || "http://localhost:8100";
const shots = process.env.SHOTS || "/tmp/claude-0/shots";
const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const errors = [];
async function open(viewport, url) {
  const page = await browser.newPage({ viewport });
  page.setDefaultTimeout(120000);
  page.on("console", (m) => { if (m.type() === "error") errors.push(`${url}: ${m.text()}`); });
  page.on("pageerror", (e) => errors.push(`${url}: ${e.message}`));
  await page.goto(`${base}${url}`, { waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__workbench?.current, null, { timeout: 90000 });
  await page.waitForTimeout(800);
  return page;
}
const page = await open({ width: 1440, height: 900 }, "/lab/workbench.html");
const wb = (fn) => page.evaluate(fn);
assert.equal(await wb(() => window.__workbench.current.id), "rocket");
assert.equal(await wb(() => window.__workbench.current.parts.length), 6);
await page.screenshot({ path: `${shots}/workbench-rocket-solid.png` });

// Explode slider moves parts deterministically and reversibly
await page.locator("#explode").fill("100");
await page.waitForTimeout(150);
const noseX = await wb(() => window.__workbench.current.parts.find((p) => p.id === "nose").group.position.x);
assert.ok(noseX < -100, `nose should move forward, got ${noseX}`);
await page.locator("#explode").fill("0");
assert.ok(Math.abs(await wb(() => window.__workbench.current.parts.find((p) => p.id === "nose").group.position.x)) < 1e-9);

// Sequential disassembly animation runs to completion
await page.click("#btn-sequence");
await page.waitForFunction(() => window.__workbench.state.explode > 0.999, null, { timeout: 60000 });
await page.screenshot({ path: `${shots}/workbench-rocket-exploded.png` });
await page.click("#btn-reverse");
await page.waitForFunction(() => window.__workbench.state.explode < 0.001, null, { timeout: 60000 });

// Rendering modes
for (const mode of ["clay", "wireframe", "blueprint", "xray", "solid"]) {
  await page.click(`#modes [data-mode="${mode}"]`);
  assert.equal(await wb(() => window.__workbench.state.mode), mode);
  if (mode !== "solid") await page.screenshot({ path: `${shots}/workbench-rocket-${mode}.png` });
}
// Section plane: toggling enables clipping on materials
await page.click("#btn-section");
assert.equal(await wb(() => window.__workbench.state.section.on), true);
assert.ok(await wb(() => { let n = 0; window.__workbench.current.root.traverse((o) => { if (o.isMesh && o.visible && o.material?.clippingPlanes?.length) n++; }); return n; }) > 0);
await page.click('#section-axis [data-axis="z"]');
await page.locator("#section").fill("500");
await page.click('#modes [data-mode="blueprint"]');
await page.screenshot({ path: `${shots}/workbench-rocket-section.png` });
await page.click("#btn-section");
await page.click('#modes [data-mode="solid"]');

// Ortho, views, dims, labels
await page.click("#btn-ortho");
assert.equal(await wb(() => window.__workbench.state.ortho), true);
for (const v of ["front", "top", "right", "iso"]) await page.click(`#views [data-view="${v}"]`);
await page.click("#btn-ortho");
await page.click("#btn-dims"); assert.equal(await wb(() => window.__workbench.state.dims), false);
await page.click("#btn-dims"); assert.equal(await wb(() => window.__workbench.state.dims), true);
await page.click("#btn-labels"); assert.equal(await wb(() => window.__workbench.state.labels), true); await page.click("#btn-labels");

// Overlays
await page.click('[data-overlay="stability"]');
await page.click('[data-overlay="pre-retune"]');
await page.click('#views [data-view="front"]');
await page.waitForTimeout(800);
await page.screenshot({ path: `${shots}/workbench-rocket-stability.png` });
await page.click('[data-overlay="pre-retune"]');

// Tree: select, hide, isolate
await page.click('.tree-row[data-id="fins2"] .name');
assert.equal(await wb(() => window.__workbench.state.selected), "fins2");
assert.match(await page.locator("#inspector").innerText(), /Root chord/);
assert.match(await page.locator("#inspector").innerText(), /D-009/);
await page.click('.tree-row[data-id="fins2"] .iso');
assert.equal(await wb(() => window.__workbench.state.isolated), "fins2");
await page.click('.tree-row[data-id="fins2"] .iso');
await page.click('.tree-row[data-id="motor2"] .eye');
assert.equal(await wb(() => window.__workbench.current.parts.find((p) => p.id === "motor2").group.visible), false);
await page.click('.tree-row[data-id="motor2"] .eye');

// Depth tabs in inspector
await page.click('#inspector [role="tab"]:has-text("Engineering")');
await page.click('#inspector [role="tab"]:has-text("Research")');

// Viewport click selection
await page.click('#views [data-view="iso"]');
await page.waitForTimeout(800);
const box = await page.locator("#viewport canvas").first().boundingBox();
await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
await page.waitForTimeout(200);

// Measure tool
await page.click('#views [data-view="front"]');
await page.waitForTimeout(2500);
await page.click("#btn-measure");
await page.mouse.click(box.x + box.width * 0.44, box.y + box.height / 2);
await page.waitForTimeout(400);
await page.mouse.click(box.x + box.width * 0.58, box.y + box.height / 2);
await page.waitForTimeout(400);
const measured = await wb(() => window.__workbench.state.lastMeasure);
if (!measured) { console.log("rect", JSON.stringify(await page.locator("#viewport canvas").first().boundingBox()), "old", JSON.stringify(box)); console.log(JSON.stringify(await page.evaluate(([a, b, c]) => [window.__workbench.pickAt(a, c), window.__workbench.pickAt(b, c)], [box.x + box.width * 0.44, box.x + box.width * 0.58, box.y + box.height / 2]))); await page.screenshot({ path: `${shots}/workbench-measure-fail.png` }); console.log(await wb(() => JSON.stringify({ m: window.__workbench.state.measure, sel: window.__workbench.state.selected, hid: [...window.__workbench.state.hidden], sec: window.__workbench.state.section, ex: window.__workbench.state.explode }))); }
assert.ok(measured > 10, `measure should yield a distance, got ${measured}`);
await page.click("#btn-measure");

// Screenshot export downloads a PNG
const [download] = await Promise.all([page.waitForEvent("download"), page.click("#btn-shot")]);
assert.match(download.suggestedFilename(), /project33-rocket-.*\.png/);

// Keyboard shortcuts
await page.locator("#viewport").focus();
await page.keyboard.press("4"); assert.equal(await wb(() => window.__workbench.state.mode), "blueprint");
await page.keyboard.press("r"); assert.equal(await wb(() => window.__workbench.state.mode), "solid");

// Four-bar STEP specimen
await page.click('.specimen[data-id="fourbar"]');
await page.waitForFunction(() => window.__workbench.current.id === "fourbar");
assert.equal(await wb(() => window.__workbench.current.parts.length), 4);
assert.deepEqual(await wb(() => window.__workbench.current.joints.concentric.length), 0);
await page.click('[data-overlay="pins"]');
await page.click('#modes [data-mode="blueprint"]');
await page.waitForTimeout(500);
await page.screenshot({ path: `${shots}/workbench-fourbar-blueprint.png` });
await page.click('.tree-row[data-id="coupler"] .name');
assert.match(await page.locator("#inspector").innerText(), /60\.000 mm/);
await page.locator("#explode").fill("100");
await page.click('#modes [data-mode="clay"]');
await page.waitForTimeout(400);
await page.screenshot({ path: `${shots}/workbench-fourbar-clay.png` });

// NACA and archives
await page.click('.specimen[data-id="naca"]');
await page.waitForFunction(() => window.__workbench.current.id === "naca");
await page.click('[data-overlay="extrude"]');
await page.screenshot({ path: `${shots}/workbench-naca.png` });
await page.click('.specimen[data-id="archives"]');
await page.waitForTimeout(500);
assert.equal(await page.locator("#placard").isVisible(), true);
await page.screenshot({ path: `${shots}/workbench-archives.png` });

// Mobile layout: no horizontal scroll
const mobile = await open({ width: 390, height: 844 }, "/lab/workbench.html?specimen=rocket&mode=clay");
const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
assert.ok(overflow <= 1, `horizontal overflow ${overflow}px`);
await mobile.screenshot({ path: `${shots}/workbench-mobile.png`, fullPage: false });

// Deep link
const deep = await open({ width: 1280, height: 800 }, "/lab/workbench.html?specimen=fourbar&mode=blueprint&explode=60&select=coupler");
assert.equal(await deep.evaluate(() => window.__workbench.state.selected), "coupler");
assert.ok(Math.abs(await deep.evaluate(() => window.__workbench.state.explode) - 0.6) < 1e-9);

await browser.close();
if (errors.length) { console.error(errors.join("\n")); process.exit(1); }
console.log("workbench: all interactions passed");
