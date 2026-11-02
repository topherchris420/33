import { mountShell } from "../core/shell.js";
import { h, $, clear, announce } from "../core/dom.js";
import { lab, docLink } from "../core/data.js";
import { statusChip } from "../core/taxonomy.js";
import { renderConstellation, makeTooltip, NODE_TYPES } from "./graph.js";
import { passport, nodeDetail } from "./passport.js";
import { renderLadders } from "./ladder.js";
import { claimTable, discrepancyRegister, groundedQuestions } from "./register.js";
import { s } from "./svg.js";

mountShell();

const ev = await lab.evidence().catch((err) => {
  clear($("#main"), h("div", { class: "wrap section" }, h("div", { class: "notice warn" }, `The evidence record could not be loaded (${err.message}). Read the generated passports instead: `, h("a", { href: docLink("docs/claims/README.md") }, "claim passports"))));
  throw err;
});

// ---------- hero ----------
function instrument(count) {
  const svg = s("svg", { viewBox: "0 0 240 240", class: "instrument", role: "img", "aria-label": `${count} accepted inert physical measurements` });
  svg.append(s("circle", { cx: 120, cy: 120, r: 112, class: "inst-bezel" }), s("circle", { cx: 120, cy: 120, r: 96, class: "inst-face" }));
  for (let i = 0; i < 60; i++) {
    const a = (-225 + (270 * i) / 59) * (Math.PI / 180);
    const major = i % 10 === 0;
    const r0 = major ? 78 : 84;
    svg.append(s("line", { x1: 120 + r0 * Math.cos(a), y1: 120 + r0 * Math.sin(a), x2: 120 + 90 * Math.cos(a), y2: 120 + 90 * Math.sin(a), class: major ? "inst-tick major" : "inst-tick" }));
  }
  const a0 = -225 * (Math.PI / 180);
  svg.append(s("text", { x: 120, y: 104, class: "inst-num", "text-anchor": "middle" }, String(count)));
  svg.append(s("text", { x: 120, y: 182, class: "inst-cap", "text-anchor": "middle" }, "ACCEPTED INERT"));
  svg.append(s("text", { x: 120, y: 195, class: "inst-cap", "text-anchor": "middle" }, "MEASUREMENTS"));
  svg.append(s("line", { x1: 120, y1: 120, x2: 120 + 70 * Math.cos(a0), y2: 120 + 70 * Math.sin(a0), class: "inst-needle" }), s("circle", { cx: 120, cy: 120, r: 5, class: "inst-hub" }));
  return svg;
}

const c = ev.counts;
const stat = (value, label, cls = "", title) => h("div", { class: `stat ${cls}`, title }, h("b", { class: "num" }, value), h("span", {}, label));
clear($("#hero-instrument"), instrument(c.accepted_physical_measurements),
  h("p", { class: "inst-note" }, "This needle moves only when a named human accepts an inert measurement with a named instrument, method, and uncertainty. No software can move it."));
clear($("#hero-stats"),
  stat(c.claims, "claims"),
  stat(c.claim_status.contradicted || 0, "contradicted", "st-contradicted"),
  stat(c.claim_status.open || 0, "unresolved", "st-open"),
  stat(c.claim_status.supported_within_limits || 0, "supported within stated limits", "st-supported"),
  stat(c.accepted_physical_measurements, "accepted physical measurements", "st-zero"),
  stat(`${c.discrepancies_open}/${c.discrepancies_total}`, "discrepancies open"),
  stat(`${c.predictions_not_measured}/${c.predictions_total}`, "predictions not measured", "st-unmeasured"),
  stat(c.artifacts, "artifacts with SHA-256", "", `${c.current_artifacts} current, ${c.archived_items} items in the failure archive`));
$("#hero-scope").textContent = ev.scope;

// ---------- constellation + passport ----------
const graphHost = $("#graph");
const tip = makeTooltip(graphHost);
const side = $("#passport");
const sideTitle = $("#passport-title");

function showIntro() {
  sideTitle.textContent = "Passport";
  clear(side,
    h("div", { class: "pp-intro" },
      h("p", { class: "eyebrow" }, "Choose a claim"),
      h("h3", {}, "Every claim carries a passport."),
      h("p", { class: "muted" }, "Select a claim in the constellation, the ladder, or the table. Its passport shows the statement, requirements, contradictions, missing measurements, review state, and the exact files behind it — each with its digest."),
      h("div", { class: "pp-claims" }, ev.claims.map((cl) => h("button", { class: "pp-claim-btn", type: "button", onclick: () => select(cl.id) },
        h("span", { class: "mono" }, cl.id), h("span", { class: "t" }, cl.title), statusChip(cl.status, cl.status_label))))));
}

let graph;
function select(id, { fromGraph = false, scroll = true } = {}) {
  const node = graph.graph.nodes.get(id);
  if (!node) return false;
  if (!fromGraph) graph.focus(id, { zoom: node.type === "claim" || true, announceSelect: false });
  render(node);
  history.replaceState(null, "", `#${id}`);
  if (scroll && window.matchMedia("(max-width: 900px)").matches) side.closest(".obs-side").scrollIntoView({ behavior: "smooth", block: "start" });
  return true;
}

function render(node) {
  if (node.type === "claim") {
    sideTitle.textContent = `Passport · ${node.id}`;
    clear(side, passport(node.data, ev, { onId: (x) => openId(x) }));
    announce(`${node.id} ${node.data.title}: ${node.data.status_label}. Passport opened.`);
  } else {
    sideTitle.textContent = node.type === "core" ? NODE_TYPES.core.label : `${NODE_TYPES[node.type].label} · ${node.type === "artifact" ? node.data.id : node.id}`;
    clear(side, nodeDetail(node, ev, { onId: (x) => openId(x) }));
    announce(`${NODE_TYPES[node.type].label} ${node.id} selected.`);
  }
  side.scrollTop = 0;
}

function openId(id) {
  if (graph.graph.nodes.has(id)) { select(id); return; }
  if (graph.graph.nodes.has(`A:${id}`)) { select(`A:${id}`); return; }
}

graph = renderConstellation(graphHost, ev, {
  tooltip: tip,
  onSelect: (node) => { render(node); history.replaceState(null, "", `#${node.id}`);
    if (window.matchMedia("(max-width: 900px)").matches) side.closest(".obs-side").scrollIntoView({ behavior: "smooth", block: "start" }); },
});

// legend
const legend = $("#legend");
const legendItems = [
  ["claim", "Claim — ring shows status"], ["requirement", "Requirement — fill shows result"], ["prediction", "Registered prediction"],
  ["preregistration", "Pre-registration (drafted)"], ["discrepancy", "Discrepancy — solid open, hollow resolved"], ["artifact", "Cited artifact — colour = evidence class"],
  ["review", "Review — hollow = tooling snapshot"], ["core", "Accepted measurements (empty)"],
];
function legendGlyph(type) {
  const svg = s("svg", { viewBox: "-14 -14 28 28", width: 22, height: 22, "aria-hidden": "true", class: "legend-glyph" });
  const map = {
    claim: () => [s("circle", { r: 9, class: "glyph-core" }), s("path", { d: "M0,-9 A9,9 0 1 1 -8.5,3", class: "ring ring-dashed glyph-open-legend" })],
    requirement: () => [s("polygon", { points: "0,-8 8,0 0,8 -8,0", class: "diamond req-not_satisfied" })],
    prediction: () => [s("circle", { r: 6.5, class: "target unmeasured" }), s("line", { x1: -10, x2: 10, class: "cross" }), s("line", { y1: -10, y2: 10, class: "cross" })],
    preregistration: () => [s("rect", { x: -6.5, y: -6.5, width: 13, height: 13, class: "prereg prereg-proposed" })],
    discrepancy: () => [s("polygon", { points: "0,-8 7.6,5 -7.6,5", class: "tri tri-open tri-strong" })],
    artifact: () => [s("rect", { x: -4.5, y: -4.5, width: 9, height: 9, class: "art", style: "--c:#e3c27a" })],
    review: () => [s("polygon", { points: "7,0 3.5,6 -3.5,6 -7,0 -3.5,-6 3.5,-6", class: "hex hex-snapshot" })],
    core: () => [s("circle", { r: 9, class: "core-ring" }), s("circle", { r: 5, class: "core-ring core-ring-in" })],
  };
  svg.append(...map[type]());
  return svg;
}
clear(legend, legendItems.map(([t, label]) => h("li", {}, legendGlyph(t), h("span", {}, label))),
  h("li", { class: "legend-status" },
    statusChip("contradicted", "Contradicted — fractured ring"), statusChip("open", "Unresolved — unfinished arc"),
    statusChip("supported_within_limits", "Supported within stated limits — bracketed")));

// filters
const typeFilters = $("#type-filters");
for (const [type, def] of Object.entries(NODE_TYPES)) {
  if (type === "core" || type === "claim") continue;
  const id = `ft-${type}`;
  const box = h("input", { type: "checkbox", id, checked: true });
  box.addEventListener("change", () => { graph.setTypeVisible(type, box.checked); announce(`${def.label} nodes ${box.checked ? "shown" : "hidden"}`); });
  typeFilters.append(h("label", { class: "chk", for: id }, box, h("span", {}, def.label)));
}
const statusFilters = $("#status-filters");
for (const [status, label] of Object.entries(ev.vocabulary.claim_statuses)) {
  if (!ev.claims.some((cl) => cl.status === status)) continue;
  const id = `fs-${status}`;
  const box = h("input", { type: "checkbox", id, checked: true });
  box.addEventListener("change", () => { graph.setStatusVisible(status, box.checked); announce(`${label[0]} claims ${box.checked ? "shown" : "hidden"}`); });
  statusFilters.append(h("label", { class: "chk", for: id }, box, statusChip(status, label[0])));
}

// search
const search = $("#graph-search");
const results = $("#search-results");
function runSearch(go = false) {
  const hits = graph.search(search.value);
  clear(results, search.value.trim() ? (hits.length ? `${hits.length} match${hits.length > 1 ? "es" : ""}` : "no match") : "");
  for (const el of graphHost.querySelectorAll(".node.is-match")) el.classList.remove("is-match");
  hits.slice(0, 40).forEach((n) => graph.nodeElement(n.id)?.classList.add("is-match"));
  if (go && hits[0]) select(hits[0].id);
}
search.addEventListener("input", () => runSearch(false));
search.addEventListener("keydown", (e) => {
  if (e.key === "Enter") { e.preventDefault(); runSearch(true); }
  if (e.key === "Escape") { search.value = ""; runSearch(false); graph.reset(); }
});

$("#zoom-in").addEventListener("click", () => graph.zoom(0.75));
$("#zoom-out").addEventListener("click", () => graph.zoom(1.33));
$("#zoom-reset").addEventListener("click", () => { graph.reset(); showIntro(); history.replaceState(null, "", location.pathname); announce("Constellation reset"); });
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !e.target.closest("input, select, textarea")) { graph.reset(); }
});

// ---------- ladders, table, register, questions ----------
renderLadders($("#ladders"), ev, (id) => { select(id, { scroll: false }); $("#constellation").scrollIntoView({ behavior: "smooth", block: "start" }); });
$("#claim-table").append(claimTable(ev, (id) => { select(id, { scroll: false }); $("#constellation").scrollIntoView({ behavior: "smooth", block: "start" }); }));
const register = discrepancyRegister($("#register-body"), ev, (id) => { select(id); $("#constellation").scrollIntoView({ behavior: "smooth", block: "start" }); });
groundedQuestions($("#questions-body"), ev, (id) => { select(id); $("#constellation").scrollIntoView({ behavior: "smooth", block: "start" }); });

clear($("#principles-list"), ev.principles.map((p) => h("li", {}, p)));
clear($("#ai-boundary"), ev.ai_boundary.map((p) => h("li", {}, p)));
clear($("#limitations"), ev.limitations.map((p) => h("li", {}, p)), h("li", {}, ev.lab_note));

// ---------- deep links ----------
function fromHash() {
  const id = decodeURIComponent(location.hash.slice(1));
  if (!id) { showIntro(); return; }
  if (!select(id, { scroll: false }) && !select(`A:${id}`, { scroll: false })) showIntro();
}
window.addEventListener("hashchange", fromHash);
fromHash();
document.body.dataset.ready = "true";
