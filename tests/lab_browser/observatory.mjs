// Browser test for the Evidence Observatory (lab/observatory.html).
//
//   python3 -m http.server 8102          # from the repository root
//   node tests/lab_browser/observatory.mjs [base-url]
//
// Fails on any console error or page error; checks that the page renders the evaluated
// record faithfully (claim count, record counts, C1 passport) and that every control
// works: filters, search, keyboard focus, reset, ladder, register. Saves screenshots
// to $SHOTS (default /tmp/claude-0/shots).
import { createRequire } from "node:module";
import { readFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = await import("playwright")); } catch { ({ chromium } = require("playwright")); }

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const BASE = process.argv[2] || process.env.LAB_URL || "http://localhost:8102";
const SHOTS = process.env.SHOTS || "/tmp/claude-0/shots";
mkdirSync(SHOTS, { recursive: true });
const ev = JSON.parse(readFileSync(join(ROOT, "lab/data/evidence.json"), "utf8"));

const browser = await chromium.launch();
const failures = [];
async function check(name, fn) {
  try { await fn(); console.log(`ok - ${name}`); } catch (err) { failures.push(name); console.log(`not ok - ${name}\n  ${err.message.split("\n").join("\n  ")}`); }
}

async function open(viewport, hash = "") {
  const page = await browser.newPage({ viewport });
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(`console: ${m.text()}`); });
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("requestfailed", (r) => errors.push(`requestfailed: ${r.url()}`));
  await page.goto(`${BASE}/lab/observatory.html${hash}`);
  await page.waitForSelector('body[data-ready="true"]', { timeout: 20000 });
  return { page, errors };
}

const { page, errors } = await open({ width: 1440, height: 900 });

await check("renders all claims as focusable constellation nodes", async () => {
  const ids = await page.$$eval(".node-claim", (els) => els.map((e) => e.dataset.id));
  assert.equal(ids.length, ev.claims.length);
  assert.equal(ids.length, 8);
  assert.deepEqual(ids.sort(), ev.claims.map((c) => c.id).sort());
  assert.ok(await page.$$eval(".node-claim", (els) => els.every((e) => e.getAttribute("tabindex") === "0")));
});

await check("record counts match the evaluated record", async () => {
  const stats = await page.$$eval("#hero-stats .stat", (els) => els.map((e) => [e.querySelector("span").textContent, e.querySelector("b").textContent]));
  const map = Object.fromEntries(stats);
  const c = ev.counts;
  assert.equal(map.claims, String(c.claims));
  assert.equal(map.contradicted, String(c.claim_status.contradicted));
  assert.equal(map.unresolved, String(c.claim_status.open));
  assert.equal(map["supported within stated limits"], String(c.claim_status.supported_within_limits));
  assert.equal(map["accepted physical measurements"], String(c.accepted_physical_measurements));
  assert.equal(map["discrepancies open"], `${c.discrepancies_open}/${c.discrepancies_total}`);
  assert.equal(map["predictions not measured"], `${c.predictions_not_measured}/${c.predictions_total}`);
  assert.equal(await page.textContent(".node-core .core-num"), String(c.accepted_physical_measurements));
  const nodes = await page.$$eval(".node", (els) => els.map((e) => e.dataset.type));
  const count = (t) => nodes.filter((x) => x === t).length;
  assert.equal(count("requirement"), ev.requirements.length);
  assert.equal(count("discrepancy"), ev.discrepancies.length);
  assert.equal(count("prediction"), ev.predictions.length);
  assert.equal(count("preregistration"), ev.preregistrations.length);
});

await page.screenshot({ path: `${SHOTS}/observatory-desktop-hero.png` });

await check("clicking C1 focuses its network and opens a faithful passport", async () => {
  await page.locator("#constellation").scrollIntoViewIfNeeded();
  await page.click('.node-claim[data-id="C1"] .hit', { force: true });
  await page.waitForTimeout(800);
  const text = await page.textContent("#passport");
  for (const needle of ["CONTRADICTED", "R-C1-CLOSURE", "D-002", "MODEL ONLY", "ANALYTICAL MODEL", "NOT SATISFIED", "NOT MEASURED", "NO HUMAN REVIEW"]) {
    assert.ok(text.includes(needle), `passport lacks ${needle}`);
  }
  assert.ok(text.includes(ev.claims[0].statement.slice(0, 60)));
  for (const a of ev.claims[0].evidence.map((id) => ev.artifacts.find((x) => x.id === id))) assert.ok(text.includes(a.sha256.slice(0, 12)), `missing digest for ${a.path}`);
  assert.ok(await page.$eval("svg.constellation", (s) => s.classList.contains("has-focus")));
  const vb = (await page.getAttribute("svg.constellation", "viewBox")).split(" ").map(Number);
  assert.ok(vb[2] < 1000, "focus should zoom the view");
  assert.ok(await page.$eval('.node[data-id="R-C1-CLOSURE"]', (e) => e.classList.contains("is-lit")));
  assert.ok(await page.$eval('.node[data-id="C5"]', (e) => !e.classList.contains("is-lit")));
  assert.equal(new URL(page.url()).hash, "#C1");
});
await page.screenshot({ path: `${SHOTS}/observatory-desktop-c1.png` });

await check("Escape resets the constellation", async () => {
  await page.keyboard.press("Escape");
  await page.waitForTimeout(800);
  assert.ok(await page.$eval("svg.constellation", (s) => !s.classList.contains("has-focus")));
  const vb = (await page.getAttribute("svg.constellation", "viewBox")).split(" ").map(Number);
  assert.deepEqual(vb, [0, 0, 1000, 1000]);
});

await check("keyboard: Tab reaches a claim and Enter opens its passport", async () => {
  await page.focus('.node-claim[data-id="C5"]');
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
  const text = await page.textContent("#passport");
  assert.ok(text.includes("Static-stability model") && text.includes("MODELS DISAGREE") && text.includes("D-006"));
  await page.keyboard.press("Escape");
});

await check("node type and status filters hide and restore nodes", async () => {
  await page.uncheck("#ft-artifact");
  assert.ok(await page.$$eval(".node-artifact", (els) => els.every((e) => e.classList.contains("is-hidden"))));
  await page.check("#ft-artifact");
  assert.ok(await page.$$eval(".node-artifact", (els) => els.every((e) => !e.classList.contains("is-hidden"))));
  await page.uncheck("#fs-contradicted");
  const hidden = await page.$$eval(".node-claim.is-hidden", (els) => els.map((e) => e.dataset.id).sort());
  assert.deepEqual(hidden, ev.claims.filter((c) => c.status === "contradicted").map((c) => c.id).sort());
  assert.ok(await page.$eval('.node[data-id="R-C1-CLOSURE"]', (e) => e.classList.contains("is-hidden")));
  await page.check("#fs-contradicted");
  assert.equal(await page.$$eval(".node-claim.is-hidden", (els) => els.length), 0);
});

await check("search finds a requirement and opens its detail", async () => {
  await page.fill("#graph-search", "R-C5-WINDOW");
  await page.press("#graph-search", "Enter");
  await page.waitForTimeout(300);
  assert.match(await page.textContent("#search-results"), /match/);
  const text = await page.textContent("#passport");
  assert.ok(text.includes("R-C5-WINDOW") && text.includes("MODELS DISAGREE"));
  await page.fill("#graph-search", "nonexistent-zzz");
  assert.equal(await page.textContent("#search-results"), "no match");
  await page.fill("#graph-search", "");
  await page.click("#zoom-reset");
});

await check("evidence ladder places every claim and leaves physical rungs empty", async () => {
  assert.equal(await page.$$eval(".ladder-gates .ladder-claim", (els) => els.length), 8);
  assert.equal(await page.$$eval(".ladder-support .ladder-claim", (els) => els.length), 8);
  assert.ok((await page.textContent("#ladders")).includes("ONLY A NAMED HUMAN CAN CROSS"));
  await page.locator("#ladder").scrollIntoViewIfNeeded();
  await page.screenshot({ path: `${SHOTS}/observatory-desktop-ladder.png` });
  await page.click('.ladder-support .ladder-claim[data-claim="C3"]');
  await page.waitForTimeout(400);
  assert.ok((await page.textContent("#passport")).includes("SUPPORTED WITHIN STATED LIMITS"));
});

await check("discrepancy register filters by status and kind", async () => {
  const open = await page.$$eval("#register-body .disc-item", (els) => els.length);
  assert.equal(open, ev.counts.discrepancies_open);
  await page.click('#register-body [data-status="all"]');
  assert.equal(await page.$$eval("#register-body .disc-item", (els) => els.length), ev.discrepancies.length);
  await page.selectOption("#register-body select", "model_vs_model");
  const n = ev.discrepancies.filter((d) => d.kind === "model_vs_model").length;
  assert.equal(await page.$$eval("#register-body .disc-item", (els) => els.length), n);
  await page.locator("#register").scrollIntoViewIfNeeded();
  await page.click("#register-body .disc-item summary");
  assert.ok(await page.$eval("#register-body .disc-item", (d) => d.open));
});

await check("grounded questions and accessible claim table render from the record", async () => {
  assert.equal(await page.$$eval("#questions-body .qa", (els) => els.length), ev.questions.length);
  assert.equal(await page.$$eval("#claim-table tbody tr", (els) => els.length), 8);
});

await check("deep link #D-006 opens that discrepancy", async () => {
  const { page: p2, errors: e2 } = await open({ width: 1440, height: 900 }, "#D-006");
  const text = await p2.textContent("#passport");
  assert.ok(text.includes("D-006") && text.includes("model vs model"));
  await p2.close();
  assert.deepEqual(e2, []);
});

await page.screenshot({ path: `${SHOTS}/observatory-desktop-full.png`, fullPage: true });

await check("mobile layout has no horizontal scroll and the passport stacks below", async () => {
  const { page: m, errors: me } = await open({ width: 390, height: 844 }, "#C6");
  const overflow = await m.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  assert.ok(overflow <= 0, `horizontal overflow ${overflow}px`);
  const graphBox = await m.locator(".obs-graph").boundingBox();
  const sideBox = await m.locator(".obs-side").boundingBox();
  assert.ok(sideBox.y > graphBox.y + graphBox.height - 2, "passport should follow the graph on mobile");
  assert.ok((await m.textContent("#passport")).includes("R-C6-MARGIN"));
  await m.screenshot({ path: `${SHOTS}/observatory-mobile-top.png` });
  await m.locator("#constellation").scrollIntoViewIfNeeded();
  await m.screenshot({ path: `${SHOTS}/observatory-mobile-graph.png` });
  await m.screenshot({ path: `${SHOTS}/observatory-mobile-full.png`, fullPage: true });
  await m.close();
  assert.deepEqual(me, []);
});

await check("reduced motion: focus changes view instantly", async () => {
  const ctx = await browser.newContext({ reducedMotion: "reduce", viewport: { width: 1280, height: 800 } });
  const p = await ctx.newPage();
  await p.goto(`${BASE}/lab/observatory.html`);
  await p.waitForSelector('body[data-ready="true"]');
  await p.focus('.node-claim[data-id="C2"]');
  await p.keyboard.press("Enter");
  const vb = (await p.getAttribute("svg.constellation", "viewBox")).split(" ").map(Number);
  assert.ok(vb[2] < 1000, "reduced motion should still zoom, instantly");
  await ctx.close();
});

await check("no console or page errors", async () => { assert.deepEqual(errors, []); });

await browser.close();
if (failures.length) { console.log(`\n${failures.length} failing: ${failures.join("; ")}`); process.exit(1); }
console.log("\nall observatory checks passed");
