import { h } from '../core/dom.js';

const finite = n => typeof n === 'number' && Number.isFinite(n);
const hash = s => typeof s === 'string' && /^[0-9a-f]{64}$/.test(s);
const string = s => typeof s === 'string' && s.trim().length > 0 && s.length <= 200;
const origins = ['synthetic', 'undeclared'];
export function validateAltimeterReport(r) {
  if (r?.schema !== 'project33.altimeter_review/1' || !Array.isArray(r.samples) || !r.samples.length || r.samples.length > 20000) throw new Error('Expected a Project 33 altimeter review with 1 to 20000 samples');
  if (!['rocket', 'launcher', 'stationary_bench'].includes(r.sensor?.mount) || !string(r.sensor.id)) throw new Error('Invalid sensor identity or mount');
  if (!hash(r.model_sha256) || !hash(r.implementation_sha256) || (r.input_sha256 !== undefined && !hash(r.input_sha256))) throw new Error('Invalid source digest');
  if (!Array.isArray(r.origins) || !r.origins.length || r.origins.length > 2 || r.origins.some(o => !origins.includes(o))) throw new Error('Invalid origin declaration');
  if (!finite(r.reference?.pressure_pa) || r.reference.pressure_pa <= 0 || !finite(r.reference.temperature_k) || !string(r.reference.description)) throw new Error('Invalid reference declaration');
  let previous = -1;
  for (const p of r.samples) {
    if (!finite(p.time_s) || p.time_s < 0 || p.time_s <= previous || !origins.includes(p.origin) || !r.origins.includes(p.origin)) throw new Error('Invalid sample clock or origin');
    previous = p.time_s;
    if (!['INVALID', 'WARMUP', 'ESTIMATED'].includes(p.status) || !['REFERENCE', 'RISING', 'FALLING', 'UNKNOWN'].includes(p.phase) || typeof p.break_before !== 'boolean' || !Number.isSafeInteger(p.segment) || p.segment < 0) throw new Error('Invalid estimate state');
    for (const k of ['pressure_pa', 'height_m', 'vertical_rate_m_s']) if (p[k] !== null && !finite(p[k])) throw new Error('Invalid sample value');
    if (p.status === 'INVALID' ? p.height_m !== null || p.vertical_rate_m_s !== null || p.phase !== 'UNKNOWN' : p.pressure_pa <= 0 || p.pressure_pa === null || p.height_m === null || (p.status === 'ESTIMATED') !== (p.vertical_rate_m_s !== null)) throw new Error('Sample values conflict with validity');
  }
  if (!Array.isArray(r.events) || r.events.length > r.samples.length || !Array.isArray(r.observations) || r.observations.length > 100) throw new Error('Invalid event list');
  const start = r.samples[0].time_s, end = r.samples.at(-1).time_s;
  for (const e of r.events) {
    if (r.sensor.mount !== 'rocket' || !['ASCENT_REVIEW', 'SIMULATED_RELEASE_MARKER'].includes(e.kind) || !finite(e.time_s) || e.time_s < start || e.time_s > end || !Number.isSafeInteger(e.segment) || e.segment < 1) throw new Error('Invalid model-rocket review marker');
    if (e.kind === 'SIMULATED_RELEASE_MARKER' && (!finite(e.sampled_peak_time_s) || e.sampled_peak_time_s < start || e.sampled_peak_time_s > e.time_s || !finite(e.sampled_peak_height_m))) throw new Error('Invalid sampled peak');
  }
  for (const e of r.observations) if (!['parachute_observed', 'ground_contact_observed'].includes(e.kind) || !finite(e.time_s) || e.time_s < start || e.time_s > end || !string(e.operator) || !string(e.note)) throw new Error('Invalid declared observation');
  const s = r.summary;
  if (!s || !['samples', 'invalid', 'gaps', 'segments'].every(k => Number.isSafeInteger(s[k]) && s[k] >= 0 && s[k] <= r.samples.length) || s.samples !== r.samples.length || typeof s.rocket_altitude_available !== 'boolean' || s.rocket_altitude_available !== (r.sensor.mount === 'rocket' && r.samples.some(p => p.height_m !== null)) || (s.maximum_relative_height_m !== null && !finite(s.maximum_relative_height_m))) throw new Error('Invalid review summary');
  return r;
}

function svgElement(tag, attrs = {}) {
  const e = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attrs)) e.setAttribute(key, String(value));
  return e;
}

export function mountAltimeter(root) {
  if (!root) return;
  const file = h('input', { id: 'altimeter-file', type: 'file', accept: '.json,application/json' });
  const example = h('button', { id: 'altimeter-example', type: 'button', class: 'btn' }, 'Load synthetic flight example');
  const output = h('div', { id: 'altimeter-result', 'aria-live': 'polite' });
  let revision = 0;
  function render(report) {
    const r = validateAltimeterReport(report), samples = r.samples;
    const rocket = r.sensor.mount === 'rocket';
    const width = Math.max(280, Math.min(960, root.clientWidth - 32));
    const svg = svgElement('svg', { viewBox: `0 0 ${width} 280`, role: 'img', 'aria-label': 'Relative pressure height over time; line breaks mark unavailable data', class: 'altimeter-chart' });
    const title = svgElement('title'); title.textContent = 'Estimated pressure height, not geometric altitude or ground clearance'; svg.append(title);
    const valid = samples.filter(p => p.height_m !== null);
    const low = Math.min(0, ...valid.map(p => p.height_m)), high = Math.max(1, ...valid.map(p => p.height_m));
    const start = samples[0].time_s, span = samples.at(-1).time_s - start || 1;
    const x = t => 60 + (width - 90) * (t - start) / span, y = h => 235 - 200 * (h - low) / (high - low);
    let path = '', move = true;
    for (const p of samples) {
      if (p.height_m === null) { move = true; continue; }
      path += `${move || p.break_before ? 'M' : 'L'}${x(p.time_s).toFixed(2)},${y(p.height_m).toFixed(2)} `;
      move = false;
    }
    svg.append(svgElement('path', { d: path, fill: 'none', stroke: '#77d9ef', 'stroke-width': 2 }));
    for (const [xx, yy, label] of [[60, 22, `${high.toFixed(1)} m`], [60, 258, `${low.toFixed(1)} m / ${start.toFixed(1)} s`], [width - 80, 258, `${samples.at(-1).time_s.toFixed(1)} s`]]) {
      const text = svgElement('text', { x: xx, y: yy, fill: 'currentColor', 'font-size': 16 }); text.textContent = label; svg.append(text);
    }
    const cursor = svgElement('line', { y1: 30, y2: 235, stroke: '#f4c88a', 'stroke-width': 1 }); svg.append(cursor);
    const scrub = h('input', { id: 'altimeter-time', type: 'range', min: 0, max: samples.length - 1, value: 0, step: 1 });
    const reading = h('div', { id: 'altimeter-reading', role: 'status', 'aria-live': 'off' });
    function select() {
      const p = samples[Number(scrub.value)]; cursor.setAttribute('x1', x(p.time_s)); cursor.setAttribute('x2', x(p.time_s));
      const value = (n, unit) => n === null ? 'NOT AVAILABLE' : `${n.toFixed(2)} ${unit}`;
      reading.replaceChildren(h('p', {}, `${p.time_s.toFixed(2)} s / ${p.status} / ${p.phase} / segment ${p.segment}`),
        h('dl', { class: 'kv' }, h('dt', {}, 'Relative pressure height'), h('dd', {}, value(p.height_m, 'm')),
          h('dt', {}, 'Estimated vertical rate'), h('dd', {}, value(p.vertical_rate_m_s, 'm/s')), h('dt', {}, 'Raw pressure'), h('dd', {}, value(p.pressure_pa, 'Pa'))));
      scrub.setAttribute('aria-valuetext', `${p.time_s.toFixed(2)} seconds, ${p.status}`);
    }
    scrub.addEventListener('input', select);
    output.replaceChildren(h('p', { class: 'label' }, `OFFLINE REVIEW / declared origin: ${r.origins.join(', ')} / sensor mount: ${r.sensor.mount}`),
      h('p', {}, `${r.sensor.id}. ${r.summary.samples} samples; ${r.summary.invalid} invalid; ${r.summary.gaps} time gaps.`),
      h('p', { class: 'notice' }, rocket ? 'Rocket-mounted source declared. Release markers are simulated analysis events. A peak followed by descent does not prove parachute deployment or safe recovery.' : 'GROUND / BENCH SOURCE: these readings do not establish rocket altitude. Model-rocket release markers are suppressed.'),
      svg, h('label', { for: scrub.id }, 'Review sample'), scrub, reading,
      h('h3', {}, 'Model markers'), r.events.length ? h('ul', {}, ...r.events.map(e => h('li', {}, `${e.time_s.toFixed(2)} s / ${e.kind.replaceAll('_', ' ')}${e.sampled_peak_time_s === undefined ? '' : ` / sampled peak ${e.sampled_peak_height_m.toFixed(2)} m at ${e.sampled_peak_time_s.toFixed(2)} s`}`))) : h('p', {}, 'No model-rocket markers in this report.'),
      h('h3', {}, 'Declared recovery observations'), r.observations.length ? h('ul', {}, ...r.observations.map(e => h('li', {}, `${e.time_s.toFixed(2)} s / ${e.kind.replaceAll('_', ' ')} / ${e.operator}: ${e.note}`))) : h('p', {}, 'No recovery observation supplied. Pressure alone does not identify an open parachute or ground contact.'),
      h('p', { class: 'small muted' }, `Reference: ${r.reference.pressure_pa} Pa, ${r.reference.temperature_k} K. ${r.reference.description}. This view displays a supplied derived report; it does not verify its original log or accept physical evidence.`));
    select();
  }
  file.addEventListener('change', async () => {
    const current = ++revision, selected = file.files[0]; output.replaceChildren();
    if (!selected) return;
    try {
      if (selected.size > 8 * 1024 * 1024) throw new Error('Report must be at most 8 MB');
      const report = JSON.parse(await selected.text()); if (current === revision) render(report);
    } catch (error) { if (current === revision) output.replaceChildren(h('p', { role: 'alert' }, error.message)); }
  });
  example.addEventListener('click', async () => {
    const current = ++revision; file.value = ''; output.textContent = 'Loading synthetic example...';
    try {
      const url = new URL('../../data/altimeter_example_review.json', import.meta.url);
      const response = await fetch(url); if (!response.ok) throw new Error('Synthetic example could not load');
      const report = await response.json(); if (current === revision) render(report);
    } catch (error) { if (current === revision) output.replaceChildren(h('p', { role: 'alert' }, error.message)); }
  });
  root.replaceChildren(h('div', { class: 'cluster' }, example, h('a', { class: 'btn ghost', href: 'data/altimeter_example_log.json', download: '' }, 'Download synthetic input')),
    h('label', { for: file.id }, 'Open an altimeter review JSON file'), file, output);
}
