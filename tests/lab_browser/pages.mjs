// Smoke and interaction test for the hub, guided lab, and research archive.
// Usage: node tests/lab_browser/pages.mjs [baseURL]   (serve with python tools/serve_lab.py 8100)
import { createRequire } from "node:module";
import assert from "node:assert/strict";
const { chromium } = createRequire(import.meta.url)("playwright");
const base = process.argv[2] || "http://localhost:8100";
const shots = process.env.SHOTS || "/tmp/claude-0/shots";
const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const errors = [];
async function open(path, viewport = { width: 1440, height: 900 }) {
  const page = await browser.newPage({ viewport });
  page.setDefaultTimeout(180000);
  page.on("console", (m) => { if (m.type() === "error") errors.push(`${path}: ${m.text()}`); });
  page.on("pageerror", (e) => errors.push(`${path}: ${e.message}`));
  await page.goto(`${base}${path}`, { waitUntil: "networkidle" });
  return page;
}
const overflow = (p) => p.evaluate(() => document.documentElement.scrollWidth - innerWidth);

// Hub
const hub = await open("/lab/index.html");
await hub.waitForFunction(() => document.querySelectorAll("#counts > div").length === 7);
assert.match(await hub.locator("#hub-record").innerText(), /8 claims/);
assert.equal(await hub.locator(".hub-modes .card").count(), 4);
assert.equal(await hub.locator("#cats .cat").count(), 3);
await hub.screenshot({ path: `${shots}/hub-desktop.png`, fullPage: true });
const hubM = await open("/lab/index.html", { width: 390, height: 844 });
assert.ok(await overflow(hubM) <= 1);
await hubM.screenshot({ path: `${shots}/hub-mobile.png` });

// Guided lab: every lesson opens, the right answer is accepted, progress updates.
const g = await open("/lab/guided.html");
await g.waitForFunction(() => window.__guided);
const ids = await g.$$eval("#lessons button", (bs) => bs.map((b) => b.dataset.id));
assert.equal(ids.length, 6);
for (const id of ids) {
  await g.click(`#lessons button[data-id="${id}"]`);
  await g.waitForFunction((x) => window.__guided.lesson === x, id);
  const labels = g.locator(".challenge label");
  const n = await labels.count();
  // Try each option until the verdict says Right (wrong answers must say Not quite).
  let ok = false;
  for (let i = 0; i < n && !ok; i++) {
    await labels.nth(i).click();
    const v = await g.locator(".challenge .verdict").innerText();
    ok = v.startsWith("Right");
    if (!ok) assert.match(v, /^Not quite/);
  }
  assert.ok(ok, `lesson ${id} has a correct answer`);
}
assert.match(await g.locator("#progress").innerText(), /6 of 6/);
await g.click("#vg-replay");
await g.waitForTimeout(3000);
await g.screenshot({ path: `${shots}/guided-desktop.png` });
await g.click('#lessons button[data-id="dims"]');
await g.waitForTimeout(8000);
await g.screenshot({ path: `${shots}/guided-dims.png` });
const gM = await open("/lab/guided.html#closure", { width: 390, height: 844 });
await gM.waitForFunction(() => window.__guided);
assert.ok(await overflow(gM) <= 1);
await gM.screenshot({ path: `${shots}/guided-mobile.png` });

// Archive: matrix, live observation recompute, provenance digests.
const a = await open("/lab/archive.html");
await a.waitForFunction(() => document.querySelectorAll("#prov tbody tr").length > 5);
assert.ok(await a.locator("#matrix tbody tr").count() >= 15);
const obs = await a.locator("#obs").innerText();
assert.match(obs, /LAB-OBS-1/);
assert.match(obs, /0 also keep the transmission angle within 40–140°/);
assert.match(obs, /14\.6–25\.0 mm/);
assert.match(await a.locator("#rights").innerText(), /not permitted/);
await a.screenshot({ path: `${shots}/archive-desktop.png`, fullPage: true });
const aM = await open("/lab/archive.html", { width: 390, height: 844 });
assert.ok(await overflow(aM) <= 1);

await browser.close();
if (errors.length) { console.error(errors.join("\n")); process.exit(1); }
console.log("hub, guided, archive: all checks passed");
