// The laboratory's classification language. Three information categories, four asset
// classes, and the evidence states. Each has a shape as well as a colour, so meaning
// never depends on colour alone.
import { h } from "./dom.js";

export const CATEGORIES = {
  historical: {
    label: "Historical aerospace engineering",
    short: "Historical",
    css: "cat-historical",
    text: "General aviation human-machine-interface practice. Original, non-operational illustrations; "
      + "nothing here is reproduced from the distribution-restricted F-117A supplement.",
  },
  research: {
    label: "Project 33 research",
    short: "Project 33",
    css: "cat-research",
    text: "Read from the repository: geometry, models, firmware architecture, claims, contradictions, and validation records.",
  },
  conceptual: {
    label: "Conceptual exploration",
    short: "Conceptual",
    css: "cat-conceptual",
    text: "Original educational models that explain a principle. Not verified hardware, not a Project 33 design.",
  },
  synthetic: {
    label: "Synthetic data",
    short: "Synthetic",
    css: "cat-synthetic",
    text: "Fabricated to exercise software. It can never support a physical or performance claim.",
  },
};

export const ASSETS = {
  "source-cad": { label: "Source CAD", css: "asset-source-cad", text: "Tessellated from a committed CAD file (STEP). Part names, colours, and edges come from the file." },
  "source-model": { label: "Source model", css: "asset-source-model", text: "Generated from a committed engineering model's parameters (OpenRocket design file, tested generator)." },
  reconstructed: { label: "Reconstructed concept", css: "asset-reconstructed", text: "Assembled by the lab from documented values where no CAD exists. Positions or shapes not in a source are marked." },
  illustration: { label: "Educational illustration", css: "asset-illustration", text: "Original drawing to explain a concept. Carries no dimensions or performance." },
  "not-translated": { label: "Not translated", css: "asset-not-translated", text: "Source exists but could not be converted faithfully; shown as an inventory only." },
};

export const STATUS = {
  contradicted: { label: "Contradicted", css: "status-contradicted", glyph: "fracture" },
  open: { label: "Unresolved", css: "status-open", glyph: "open-arc" },
  supported_within_limits: { label: "Supported within stated limits", css: "status-supported_within_limits", glyph: "bracketed" },
  superseded: { label: "Superseded", css: "status-not_measured", glyph: "hollow" },
};

export const EVIDENCE_CLASS_COLORS = {
  specification: "#8fa2ad",
  implementation: "#67d8cf",
  test_procedure: "#4fa3c7",
  synthetic: "#b49ad8",
  analytical: "#e3c27a",
  simulated: "#e0a274",
  execution_record: "#4cc9bb",
  bench_observed: "#f1e9d6",
  bench_measured: "#ffffff",
};

export function categoryBadge(key, extra = "") {
  const c = CATEGORIES[key];
  return h("span", { class: `cat ${c.css}`, title: c.text }, extra ? `${c.short} · ${extra}` : c.label);
}

export function assetBadge(key) {
  const a = ASSETS[key];
  return h("span", { class: `asset ${a.css}`, title: a.text }, a.label);
}

export function statusChip(status, label) {
  const s = STATUS[status] || { label: status, css: "status-not_measured" };
  return h("span", { class: `status ${s.css}` }, label || s.label);
}

export function notMeasured(text = "NOT MEASURED") {
  return h("span", { class: "not-measured" }, text);
}

export function notSpecified() {
  return notMeasured("NOT SPECIFIED");
}
