import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFileSync, mkdirSync } from 'node:fs';
import { resolve, extname, sep } from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const ROOT = process.cwd();

test('manual search, deep links, reading marks, failure fallback and responsive layout', { timeout: 120000 }, async () => {
  const server = createServer((req, res) => {
    const file = resolve(ROOT, '.' + decodeURIComponent(new URL(req.url, 'http://local').pathname));
    if (!file.startsWith(ROOT + sep)) return res.writeHead(403).end();
    try {
      const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json' };
      res.writeHead(200, { 'content-type': types[extname(file)] || 'application/octet-stream' });
      res.end(readFileSync(file));
    } catch { res.writeHead(404).end(); }
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  let browser;
  try {
    browser = await chromium.launch({ channel: 'msedge', headless: true });
    const page = await browser.newPage({ viewport: { width: 1360, height: 900 } });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    const url = `http://127.0.0.1:${server.address().port}/lab/bench-manual.html`;
    await page.goto(url + '#manual-sessions');
    await page.waitForSelector('body[data-manual-ready=true]');
    assert.equal(await page.locator('#manual-chapters article:visible').count(), 9);
    assert.equal(await page.evaluate(() => document.activeElement.id), 'manual-sessions');
    assert.equal(await page.locator('.manual-checklist').count(), 9);
    assert.equal(await page.locator('.manual-trouble').count(), 7);
    await page.locator('.manual-trouble summary').first().click();
    assert.match(await page.locator('.manual-trouble[open]').first().textContent(), /UART/);
    await page.fill('#manual-search', 'raw session');
    assert.match(await page.textContent('#manual-status'), /1 glossary terms/);
    await page.fill('#manual-search', 'zznothingmatcheszz');
    assert.match(await page.textContent('#manual-status'), /No matches/);
    await page.click('text=Clear search');
    await page.check('#read-scope');
    await page.reload();
    await page.waitForSelector('body[data-manual-ready=true]');
    assert.equal(await page.isChecked('#read-scope'), true);
    await page.click('text=Reset reading marks');
    assert.equal(await page.isChecked('#read-scope'), false);
    await page.fill('#manual-search', 'zznothingmatcheszz');
    await page.click('.manual-toc a[href="#manual-limits"]');
    assert.equal(await page.inputValue('#manual-search'), '');
    assert.equal(await page.locator('#manual-limits').isVisible(), true);
    assert.match(await page.getAttribute('video source', 'src'), /project33-bench-manual-github-720p.mp4/);
    assert.equal(await page.locator('video[controls]').count(), 1);
    mkdirSync('build/manual-study', { recursive: true });
    await page.locator('#reference').scrollIntoViewIfNeeded();
    await page.screenshot({ path: 'build/manual-study/desktop.png' });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.screenshot({ path: 'build/manual-study/mobile.png' });
    assert.deepEqual(errors, []);
    // Denied browser storage must not prevent use of the manual.
    const blocked = await browser.newPage();
    await blocked.addInitScript(() => Object.defineProperty(window, 'localStorage', { get() { throw new Error('denied'); } }));
    await blocked.goto(url);
    await blocked.waitForSelector('body[data-manual-ready=true]');
    await blocked.check('#read-scope');
    assert.match(await blocked.textContent('#manual-progress'), /Storage unavailable/);
    await blocked.route('**/bench_manual.json', route => route.fulfill({ status: 503, body: '' }));
    await blocked.reload();
    assert.match(await blocked.textContent('#manual-reader'), /could not be loaded/);
  } finally { await browser?.close(); server.close(); }
});
