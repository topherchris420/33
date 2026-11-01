// Cinematic test: the film is a pure function of time. Seeks to every chapter, checks the
// overlays that must (and must not) appear, exercises controls, and saves frames.
import { createRequire } from "node:module";
import assert from "node:assert/strict";
const { chromium } = createRequire(import.meta.url)("playwright");
const base = process.argv[2] || "http://localhost:8100";
const shots = process.env.SHOTS || "/tmp/claude-0/shots";
const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--autoplay-policy=no-user-gesture-required"] });
const errors = [];
const page = await browser.newPage({ viewport: { width: 1440, height: 860 } });
page.setDefaultTimeout(180000);
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
page.on("pageerror", (e) => errors.push(e.message));
await page.goto(`${base}/lab/cinematic.html`, { waitUntil: "networkidle" });
await page.waitForFunction(() => window.__film, null, { timeout: 120000 });
const at = async (t, name) => {
  await page.evaluate((x) => window.__film.seek(x), t);
  await page.waitForTimeout(300);
  if (name) await page.screenshot({ path: `${shots}/cinematic-${name}.png` });
};
await page.screenshot({ path: `${shots}/cinematic-start.png` });
await page.click("#play-silent");
assert.equal(await page.evaluate(() => window.__film.playing), true);
await page.waitForTimeout(1200);
assert.ok(await page.evaluate(() => window.__film.t) > 0.2, "time advances while playing");
await page.click("#toggle");
assert.equal(await page.evaluate(() => window.__film.playing), false);
await at(3.5, "01-pencil");
assert.match(await page.locator("#caption").innerText(), /Every machine begins with a question/);
await at(10, "02-workshop");
await at(15.2, "03-lever");
await at(22.5, "04-scan");
await at(29.5, "05-dimensions");
await at(35.8, "06-exploded");
await at(40, "07-annotation");
assert.match(await page.locator("#annotation").innerText(), /GEOMETRY IS NOT VALIDATION/);
await at(46, "08-schematic");
await at(54, "09-does-it-work");
assert.equal(await page.locator("#evidence").isVisible(), true);
assert.match(await page.locator("#evidence").innerText(), /C1[\s\S]*CONTRADICTED/);
await at(61, "10-narration");
assert.equal(await page.locator("#evidence").isVisible(), false);
await at(65.5, "11-reassemble");
await at(76, "12-title");
assert.equal(await page.locator("#title").isVisible(), true);
// Captions toggle hides captions
await at(57);
await page.click("#cc");
assert.equal(await page.locator("#caption").isVisible(), false);
await page.click("#cc");
// Skip lands on the title, replay restarts
await page.click("#skip");
assert.ok(await page.evaluate(() => window.__film.t) >= 70);
await page.click("#replay");
assert.ok(await page.evaluate(() => window.__film.t) < 2);
await page.click("#toggle");
// Chapters
await page.click("#chapters button:nth-child(8)");
assert.ok(Math.abs(await page.evaluate(() => window.__film.t) - 50.01) < 0.5);
// Determinism: the same time renders the same overlay state
await at(36); const a = await page.locator("#tag").innerText();
await at(12); await at(36); assert.equal(await page.locator("#tag").innerText(), a);
// Mobile
const m = await browser.newPage({ viewport: { width: 390, height: 844 } });
m.on("pageerror", (e) => errors.push(e.message));
await m.goto(`${base}/lab/cinematic.html?t=54`, { waitUntil: "networkidle" });
await m.waitForFunction(() => window.__film, null, { timeout: 120000 });
await m.evaluate(() => { document.querySelector("#start").hidden = true; });
await m.waitForTimeout(500);
await m.screenshot({ path: `${shots}/cinematic-mobile.png` });
assert.ok(await m.evaluate(() => document.documentElement.scrollWidth - innerWidth) <= 1);
await browser.close();
if (errors.length) { console.error(errors.join("\n")); process.exit(1); }
console.log("cinematic: all checks passed");
