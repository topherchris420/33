import { h } from '../core/dom.js';

const SHA = /^[a-f0-9]{64}$/i;
function entries(value, key, name, nullable = false) {
  if (!Array.isArray(value) || !value.length || value.length > 10000) throw new TypeError(`${name} must be a nonempty bounded list`);
  const result = new Map();
  for (const item of value) {
    if (!item || typeof item[key] !== 'string' || !item[key].trim() || item[key].length > 1024) throw new TypeError(`Invalid ${name} identity`);
    if (result.has(item[key])) throw new TypeError(`Duplicate ${name} identity: ${item[key]}`);
    if (!(nullable && item.sha256 === null) && (typeof item.sha256 !== 'string' || !SHA.test(item.sha256))) throw new TypeError(`Invalid ${name} SHA-256`);
    result.set(item[key], item.sha256 === null ? null : item.sha256.toLowerCase());
  }
  return result;
}
function identity(value, field) {
  if (value === null || value === undefined || value === '') return null;
  if (typeof value !== 'string' || value.length > 1024) throw new TypeError(`Invalid ${field}`);
  return value;
}
function parsePlan(plan) {
  if (!plan || plan.schema !== 'project33.bench_plan/1' || plan.scope !== 'stationary_inert_demonstrator') throw new TypeError('Expected a Project 33 stationary inert bench plan');
  return {
    sources: entries(plan.source_snapshot, 'path', 'source snapshot'),
    firmware: entries(plan.installed_firmware, 'id', 'installed firmware', true),
    specimen: new Map([
      ['hardware_revision', identity(plan.hardware_revision, 'hardware revision')],
      ['specimen_id', identity(plan.specimen?.id, 'specimen ID')],
    ]),
  };
}

/** Compare declared identities only. Never accesses the files named by a manifest. */
export function comparePlans(left, right) {
  const a = parsePlan(left), b = parsePlan(right), rows = [];
  for (const group of ['sources', 'firmware', 'specimen']) {
    const keys = [...new Set([...a[group].keys(), ...b[group].keys()])].sort();
    for (const key of keys) {
      const l = a[group].get(key), r = b[group].get(key);
      const state = !a[group].has(key) ? 'added' : !b[group].has(key) ? 'missing' : l === null || r === null ? 'unknown' : l === r ? 'matched' : 'changed';
      rows.push({ group, key, state, left: l ?? null, right: r ?? null });
    }
  }
  const counts = Object.fromEntries(['matched', 'changed', 'missing', 'added', 'unknown'].map(s => [s, rows.filter(r => r.state === s).length]));
  return { rows, counts, meaning: 'Declaration comparison only; no hardware identity or evidence acceptance is established.' };
}

export function mountConfiguration(root) {
  if (!root) return;
  const left = h('input', { id: 'config-left', type: 'file', accept: '.json,application/json' });
  const right = h('input', { id: 'config-right', type: 'file', accept: '.json,application/json' });
  const output = h('div', { id: 'config-result', role: 'status', style: { overflowWrap: 'anywhere' } });
  const render = (a, b, synthetic = false) => {
    const result = comparePlans(a, b);
    const counts = Object.entries(result.counts).map(([k,v]) => `${v} ${k}`).join(' · ');
    const rows = result.rows.map(row => h('tr', { 'data-config-state': row.state },
      h('td', {}, `${row.group} / ${row.key}`), h('td', {}, row.state.toUpperCase()),
      h('td', {}, h('code', {}, row.left ?? 'UNKNOWN / ABSENT')),
      h('td', {}, h('code', {}, row.right ?? 'UNKNOWN / ABSENT'))));
    const table = h('table', {},
      h('thead', {}, h('tr', {}, ...['Identity', 'Result', 'Left', 'Right'].map(t => h('th', {}, t)))),
      h('tbody', {}, ...rows));
    output.replaceChildren(h('p', {}, synthetic ? 'SYNTHETIC EXAMPLE / ' : 'LOCAL DECLARATIONS / ', counts),
      h('p', { class: 'small muted' }, result.meaning),
      h('div', { style: { overflowX: 'auto' } }, table));
  };
  const compare = h('button', { class: 'btn', type: 'button', id: 'config-compare', onclick: async () => {
    compare.disabled = true;
    try {
      const files = [left.files[0], right.files[0]];
      if (files.some(f => !f)) throw new Error('Select both bench-plan JSON files.');
      if (files.some(f => f.size > 2 * 1024 * 1024)) throw new Error('Each plan must be at most 2 MB.');
      const plans = await Promise.all(files.map(async f => JSON.parse(await f.text())));
      render(...plans);
    } catch (error) { output.replaceChildren(h('p', { role: 'alert' }, `Comparison unavailable: ${error.message}`)); }
    finally { compare.disabled = false; }
  } }, 'Compare local plans');
  const example = h('button', { class: 'btn ghost', type: 'button', id: 'config-example', onclick: () => {
    const a = { schema: 'project33.bench_plan/1', scope: 'stationary_inert_demonstrator', hardware_revision: 'EXAMPLE-A', specimen: { id: 'SYNTHETIC' }, source_snapshot: [{ path: 'example.py', sha256: 'a'.repeat(64) }], installed_firmware: [{ id: 'rocket', sha256: null }] };
    const b = structuredClone(a); b.source_snapshot[0].sha256 = 'b'.repeat(64);
    render(a, b, true);
  } }, 'Try synthetic example');
  const invalidate = () => output.replaceChildren(h('p', {}, 'Selection changed. Compare the selected files to see their current result.'));
  left.addEventListener('change', invalidate); right.addEventListener('change', invalidate);
  root.replaceChildren(
    h('p', {}, 'Load plans created by the existing bench configuration workflow. Missing binary digests remain unknown.'),
    h('div', { class: 'grid-2' }, h('label', { for: left.id }, 'Left plan ', left), h('label', { for: right.id }, 'Right plan ', right)),
    h('div', { class: 'btn-row', style: { marginTop: '18px' } }, compare, example), output);
}
