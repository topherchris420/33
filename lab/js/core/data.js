// Data access for the laboratory. Every value shown comes from a committed file:
// either a canonical record (evidence/*.json, protocol/*.json, docs/EVIDENCE/*) read
// as published, or a derived view in lab/data/ whose inputs are pinned by SHA-256.

export const REPO = "https://github.com/topherchris420/33";
export const BRANCH = "main";

// This module lives at <site>/lab/js/core/data.js; the repository root is three levels up.
export const SITE_ROOT = new URL("../../../", import.meta.url);

const cache = new Map();

/** Fetch JSON relative to the repository root (e.g. "evidence/discrepancies.json"). */
export function loadJSON(path) {
  if (!cache.has(path)) {
    const url = new URL(path, SITE_ROOT);
    cache.set(path, fetch(url, { cache: "no-cache" }).then((r) => {
      if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
      return r.json();
    }));
  }
  return cache.get(path);
}

export function loadText(path) {
  const key = `text:${path}`;
  if (!cache.has(key)) {
    cache.set(key, fetch(new URL(path, SITE_ROOT), { cache: "no-cache" }).then((r) => {
      if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
      return r.text();
    }));
  }
  return cache.get(key);
}

export const lab = {
  evidence: () => loadJSON("lab/data/evidence.json"),
  openrocket: () => loadJSON("lab/data/openrocket.json"),
  naca: () => loadJSON("lab/data/naca0012.json"),
  telemetryFixture: () => loadJSON("lab/data/telemetry_fixture.json"),
  fourBarStep: () => loadJSON("lab/data/cad/four_bar.json"),
  archives: () => loadJSON("lab/data/cad/archives.json"),
  cadManifest: () => loadJSON("lab/data/cad/manifest.json"),
};

export const canonical = {
  fourBarSweep: () => loadJSON("docs/EVIDENCE/C1_four_bar_sweep.json"),
  c5Crosscheck: () => loadJSON("docs/EVIDENCE/C5_barrowman_crosscheck.json"),
  c5Inputs: () => loadJSON("docs/EVIDENCE/C5_static_margin_inputs.json"),
  c5Csv: () => loadText("docs/EVIDENCE/C5_static_margin.csv"),
  c6DesignPoint: () => loadJSON("docs/EVIDENCE/C6_design_point.json"),
  c6Sweep: () => loadJSON("docs/EVIDENCE/C6_spring_sweep.json"),
  c7Run: () => loadJSON("docs/EVIDENCE/C7_run_record.json"),
  c8Hinge: () => loadJSON("docs/EVIDENCE/C8_hinge_fos.json"),
  c4Summary: () => loadJSON("docs/EVIDENCE/C4_mass_summary.json"),
  groundStatus: () => loadJSON("protocol/ground_status_model.json"),
  protocol: () => loadJSON("protocol/project33_protocol.json"),
  discrepancies: () => loadJSON("evidence/discrepancies.json"),
  safetyGates: () => loadJSON("evidence/safety_gates.json"),
};

/** Link to a repository file on GitHub (source code, data, CAD). */
export function repoLink(path, line) {
  const clean = path.replace(/^\/+/, "");
  const encoded = clean.split("/").map(encodeURIComponent).join("/");
  return `${REPO}/blob/${BRANCH}/${encoded}${line ? `#L${line}` : ""}`;
}

/** Link to a document rendered on the project site when it is Markdown, else to GitHub. */
export function docLink(path) {
  const clean = path.replace(/^\/+/, "");
  if (clean.endsWith(".md")) return new URL(clean.replace(/\.md$/, ".html"), SITE_ROOT).href;
  return repoLink(clean);
}

export function siteURL(path) {
  return new URL(path.replace(/^\/+/, ""), SITE_ROOT).href;
}

export function discrepancyLink(id) {
  return `${new URL("docs/DISCREPANCIES.html", SITE_ROOT).href}#${id.toLowerCase()}`;
}

export function claimLink(id) {
  return new URL(`docs/claims/${id}.html`, SITE_ROOT).href;
}

/** Parse a small CSV (no quoted commas) into objects. */
export function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  const head = lines.shift().split(",");
  return lines.map((line) => {
    const cells = line.split(",");
    return Object.fromEntries(head.map((k, i) => [k, cells[i]]));
  });
}
