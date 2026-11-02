import { h } from './core/dom.js';
import { loadJSON, docLink, repoLink } from './core/data.js';

const root = document.querySelector('#manual-reader');
const KEY = 'project33-manual-reading-v1';

async function boot() {
  const data = await loadJSON('lab/data/bench_manual.json');
  let marks = {};
  let storageAvailable = true;
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || '{}');
    if (saved && saved.revision === data.revision && typeof saved.marks === 'object' && saved.marks) marks = saved.marks;
  } catch { storageAvailable = false; }
  const status = h('p', { role: 'status', class: 'muted', id: 'manual-status' });
  const progress = h('p', { id: 'manual-progress', class: 'small' });
  const search = h('input', { type: 'search', id: 'manual-search', placeholder: 'Search chapters, terms and sources', autocomplete: 'off' });
  const content = h('div', { id: 'manual-chapters' });
  const toc = h('nav', { 'aria-label': 'Manual chapters', class: 'manual-toc' });
  const inputs = new Map();
  const cards = new Map();
  function updateProgress() {
    const count = data.chapters.filter(c => marks[c.id] === true).length;
    progress.textContent = `${count} of ${data.chapters.length} chapters marked read. Personal reading only; no evidence or approval is recorded.${storageAvailable ? ' Marks reset when the indexed edition changes.' : ' Storage unavailable; marks last only on this page.'}`;
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify({ revision: data.revision, marks })); }
    catch { storageAvailable = false; }
    updateProgress();
  }
  for (const chapter of data.chapters) {
    const id = `manual-${chapter.id}`;
    const link = h('a', { href: `#${id}` }, `${chapter.number} / ${chapter.title}`);
    link.addEventListener('click', () => { search.value = ''; filter(); });
    toc.append(link);
    const checkbox = h('input', { type: 'checkbox', id: `read-${chapter.id}` });
    checkbox.checked = marks[chapter.id] === true;
    checkbox.addEventListener('change', () => { marks[chapter.id] = checkbox.checked; save(); });
    inputs.set(chapter.id, checkbox);
    const card = h('article', { class: 'manual-chapter', id, tabindex: '-1' },
      h('p', { class: 'eyebrow' }, `SECTION ${chapter.number}`),
      h('h3', {}, chapter.title), h('p', { class: 'manual-summary' }, chapter.summary),
      h('div', { class: `manual-notice ${chapter.notice_level.toLowerCase()}` }, h('strong', {}, chapter.notice_level), h('p', {}, chapter.notice)),
      ...chapter.paragraphs.map(p => h('p', {}, p)),
      h('h4', {}, 'Review checklist'),
      h('ol', { class: 'manual-checklist' }, ...chapter.checklist.map(item => h('li', {}, item))),
      ...(chapter.troubleshooting || []).map(item => h('details', { class: 'manual-trouble' },
        h('summary', {}, item.symptom), h('p', {}, h('strong', {}, 'Interpretation: '), item.interpretation),
        h('p', {}, h('strong', {}, 'Record review: '), item.review), h('a', { href: docLink(item.source) }, 'Read the source'))),
      h('ul', { class: 'manual-sources' }, ...chapter.sources.map(path => h('li', {}, h('a', { href: docLink(path) }, path.replace('docs/', '').replace('.md', '').replaceAll('_', ' ')), ' · ', h('a', { href: repoLink(path) }, 'source')))),
      h('label', { class: 'manual-read', for: checkbox.id }, checkbox, ' I have read this chapter'));
    cards.set(chapter.id, card);
    content.append(card);
  }
  const terms = h('dl', { class: 'manual-glossary' });
  const termNodes = [];
  for (const [term, definition] of Object.entries(data.glossary)) {
    const dt = h('dt', {}, term), dd = h('dd', {}, definition);
    termNodes.push({ dt, dd, text: `${term} ${definition}`.toLowerCase() });
    terms.append(dt, dd);
  }
  function filter() {
    const words = search.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    const matches = text => words.every(w => text.includes(w));
    let count = 0, termCount = 0;
    for (const chapter of data.chapters) {
      const visible = matches(JSON.stringify(chapter).toLowerCase());
      cards.get(chapter.id).hidden = !visible;
      if (visible) count++;
    }
    for (const term of termNodes) {
      const visible = matches(term.text);
      term.dt.hidden = term.dd.hidden = !visible;
      if (visible) termCount++;
    }
    status.textContent = count || termCount ? `${count} chapters and ${termCount} glossary terms shown.` : 'No matches. Try a different term or clear the search.';
  }
  search.addEventListener('input', filter);
  const reset = h('button', { class: 'btn ghost', type: 'button', onclick: () => {
    marks = {}; for (const input of inputs.values()) input.checked = false; save();
  } }, 'Reset reading marks');
  const clear = h('button', { class: 'btn', type: 'button', onclick: () => { search.value = ''; filter(); search.focus(); } }, 'Clear search');
  const print = h('button', { class: 'btn', type: 'button', onclick: () => {
    search.value = ''; filter();
    for (const detail of root.querySelectorAll('details')) detail.open = true;
    window.print();
  } }, 'Print reference');
  const commands = h('section', { class: 'manual-chapter' }, h('h3', {}, 'Offline review quick reference'),
    h('p', {}, 'Run from a local checkout. Choose a fresh output directory for each packet.'),
    h('pre', {}, h('code', {}, 'python -m evidence status\npython -m evidence check\npython -m evidence build --output build/review\npython -m evidence verify build/review')));
  root.replaceChildren(
    h('div', { class: 'manual-controls' }, h('label', { for: search.id }, 'Find a topic'), search, h('div', { class: 'btn-row' }, clear, print, reset), status, progress),
    h('div', { class: 'manual-layout' }, toc, content), commands,
    h('section', { class: 'manual-chapter', id: 'manual-glossary' }, h('h3', {}, 'Glossary / evidence language'), terms),
    h('details', { class: 'manual-provenance' }, h('summary', {}, `Source index · edition ${data.revision.slice(0, 12)}`),
      h('p', {}, 'SHA-256 digests identify the source bytes at generation. They are not validation results. A changed source requires rebuilding the index.'),
      ...data.sources.map(s => h('p', {}, h('a', { href: repoLink(s.path) }, s.path), h('code', {}, s.sha256)))));
  function followHash() {
    const target = [...cards.values()].find(c => `#${c.id}` === location.hash);
    if (target) { search.value = ''; filter(); target.scrollIntoView(); target.focus({ preventScroll: true }); }
  }
  window.addEventListener('hashchange', followHash);
  updateProgress(); filter(); followHash();
  document.body.dataset.manualReady = 'true';
}
boot().catch(() => {
  root.replaceChildren(h('p', { role: 'alert' }, 'The manual index could not be loaded. Reload this page or use the document links in the film guide below.'));
});
