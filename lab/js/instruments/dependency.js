// Failure-dependency views. Left: an abstract, generic aircraft-information graph (original,
// synthetic — no real system). Right: Project 33's own source-pinned ground-status model
// (protocol/ground_status_model.json). Both answer one question: if this fails, what can I
// still trust? Neither implies shared hardware or specifications.
import { h, clear, announce, reducedMotion } from "../core/dom.js";
import { repoLink } from "../core/data.js";

// requires: list of groups; every group must have at least one healthy member (AND of ORs).
export const GENERIC = {
  layers: ["Power", "Sources", "Processing", "Displays", "Functions"],
  nodes: [
    { id: "busA", label: "Power bus A", layer: 0, requires: [] },
    { id: "busB", label: "Power bus B", layer: 0, requires: [] },
    { id: "air", label: "Air data unit", layer: 1, requires: [["busA"]] },
    { id: "ins", label: "Inertial unit", layer: 1, requires: [["busA", "busB"]] },
    { id: "gnss", label: "Satellite nav receiver", layer: 1, requires: [["busB"]] },
    { id: "dp1", label: "Display processor 1", layer: 2, requires: [["busA"]] },
    { id: "dp2", label: "Display processor 2", layer: 2, requires: [["busB"]] },
    { id: "dl", label: "Left display", layer: 3, requires: [["busA"], ["dp1", "dp2"]] },
    { id: "dr", label: "Right display", layer: 3, requires: [["busB"], ["dp2", "dp1"]] },
    { id: "hud", label: "Head-up display", layer: 3, requires: [["busA"], ["dp1"]] },
    { id: "fAtt", label: "Attitude", layer: 4, requires: [["ins"], ["dl", "dr", "hud"]], fn: true },
    { id: "fAir", label: "Speed & altitude", layer: 4, requires: [["air"], ["dl", "hud"]], fn: true },
    { id: "fNav", label: "Navigation map", layer: 4, requires: [["gnss"], ["ins"], ["dr", "dl"]], fn: true },
    { id: "fAlert", label: "Alerting", layer: 4, requires: [["dp1", "dp2"], ["dl", "dr"]], fn: true },
  ],
};

/** Evaluate node health given a set of failed node ids. Returns Map id -> "ok" | "degraded" | "lost". */
export function evaluateGeneric(failed) {
  const status = new Map();
  for (const n of GENERIC.nodes) {
    if (failed.has(n.id)) { status.set(n.id, "lost"); continue; }
    let lost = false, degraded = false;
    for (const group of n.requires) {
      const alive = group.filter((g) => status.get(g) !== "lost");
      if (!alive.length) lost = true;
      else if (alive.length < group.length || alive.some((g) => status.get(g) === "degraded")) degraded = true;
    }
    status.set(n.id, lost ? "lost" : degraded ? "degraded" : "ok");
  }
  return status;
}

export function mountGeneric({ svgHost, readout, resetBtn }) {
  const failed = new Set();
  const W = 830, H = 420, colX = (l) => 72 + l * 171, pos = new Map();
  const byLayer = GENERIC.layers.map((_, l) => GENERIC.nodes.filter((n) => n.layer === l));
  byLayer.forEach((nodes, l) => nodes.forEach((n, i) => pos.set(n.id, [colX(l), 70 + ((i + 0.5) * (H - 100)) / nodes.length])));
  const NS = "http://www.w3.org/2000/svg";
  const el = (tag, attrs = {}, ...kids) => { const e = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v); kids.forEach((k) => e.append(k)); return e; };
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Generic dependency graph. Select a node to fail it.", class: "dep-svg" });
  GENERIC.layers.forEach((name, l) => svg.append(el("text", { x: colX(l), y: 26, class: "dep-layer", "text-anchor": "middle" }, name.toUpperCase())));
  const edges = [];
  for (const n of GENERIC.nodes) for (const group of n.requires) for (const g of group) {
    const [x1, y1] = pos.get(g), [x2, y2] = pos.get(n.id);
    const path = el("path", { d: `M${x1 + 58},${y1} C${x1 + 100},${y1} ${x2 - 100},${y2} ${x2 - 58},${y2}`, class: `dep-edge${group.length > 1 ? " redundant" : ""}`, "data-from": g, "data-to": n.id });
    svg.append(path); edges.push(path);
  }
  const nodeEls = new Map();
  for (const n of GENERIC.nodes) {
    const [x, y] = pos.get(n.id);
    const g = el("g", { class: `dep-node${n.fn ? " fn" : ""}`, transform: `translate(${x},${y})`, tabindex: "0", role: "button", "aria-pressed": "false", "data-node": n.id, "aria-label": `${n.label}: toggle failure` });
    g.append(el("rect", { x: -58, y: -16, width: 116, height: 32, rx: n.fn ? 16 : 3 }), el("text", { "text-anchor": "middle", y: 4 }, n.label));
    const toggle = () => { failed.has(n.id) ? failed.delete(n.id) : failed.add(n.id); update(n.id); };
    g.addEventListener("click", toggle);
    g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } });
    svg.append(g); nodeEls.set(n.id, g);
  }
  svgHost.append(svg);
  function update(origin) {
    const status = evaluateGeneric(failed);
    const instant = reducedMotion();
    for (const n of GENERIC.nodes) {
      const g = nodeEls.get(n.id);
      g.style.transitionDelay = instant || !origin ? "0ms" : `${n.layer * 140}ms`;
      g.dataset.status = status.get(n.id);
      g.setAttribute("aria-pressed", String(failed.has(n.id)));
      g.dataset.failed = String(failed.has(n.id));
    }
    for (const p of edges) {
      const s = status.get(p.dataset.from);
      p.dataset.status = s;
      p.style.transitionDelay = instant || !origin ? "0ms" : `${GENERIC.nodes.find((n) => n.id === p.dataset.from).layer * 140}ms`;
    }
    const fns = GENERIC.nodes.filter((n) => n.fn);
    clear(readout,
      h("p", { class: "label" }, failed.size ? `Failed: ${[...failed].map((id) => GENERIC.nodes.find((n) => n.id === id).label).join(", ")}` : "Nothing failed. Select any box to fail it."),
      h("ul", { class: "dep-fns" }, fns.map((f) => h("li", { "data-status": status.get(f.id) }, h("span", { class: "dep-dot" }), f.label, " — ", h("b", {}, { ok: "available", degraded: "available, redundancy lost", lost: "lost" }[status.get(f.id)])))));
    if (origin) announce(`${GENERIC.nodes.find((n) => n.id === origin).label} ${failed.has(origin) ? "failed" : "restored"}`);
  }
  resetBtn.addEventListener("click", () => { failed.clear(); update(); announce("All generic resources restored"); });
  update();
  return { failed, update };
}

/** Project 33: which channels and capabilities survive a set of failed units. */
export function evaluateGroundStatus(model, failedUnits) {
  const ok = (item) => item.requires.every((u) => !failedUnits.has(u));
  return {
    channels: model.channels.map((c) => ({ ...c, available: ok(c) })),
    capabilities: model.capabilities.map((c) => ({ ...c, available: ok(c) })),
  };
}

export function mountGroundStatus({ model, unitsHost, resultHost, resetBtn }) {
  const failed = new Set();
  for (const u of model.units) {
    unitsHost.append(h("button", { class: "btn gs-unit", type: "button", "data-unit": u.id, "aria-pressed": "false", title: u.name,
      onclick: (e) => { failed.has(u.id) ? failed.delete(u.id) : failed.add(u.id); e.currentTarget.setAttribute("aria-pressed", String(failed.has(u.id))); render(); announce(`${u.name} ${failed.has(u.id) ? "failed" : "restored"}`); } },
    h("span", { class: "mono" }, u.id), h("small", {}, u.name)));
  }
  const pins = (src) => h("ul", { class: "gs-pins" }, (src || []).map((s) => h("li", {}, h("a", { class: "src", href: repoLink(s.path), target: "_blank", rel: "noopener" }, s.path),
    s.contains ? h("code", {}, s.contains.length > 110 ? `${s.contains.slice(0, 110)}…` : s.contains) : s.absent ? h("code", {}, `absent: ${s.absent}`) : s.count ? h("code", {}, `count(${s.count}) = ${s.equals}`) : null)));
  function item(c, kind) {
    return h("li", { class: `gs-item ${c.available ? "ok" : "lost"}${c.safety ? " safety" : ""}`, "data-id": c.id, "data-available": String(c.available) },
      h("details", {},
        h("summary", {}, h("span", { class: "dep-dot" }), h("span", { class: "gs-name" }, c.name),
          h("span", { class: "gs-tag" }, c.available ? "available" : "lost"), c.safety ? h("span", { class: "gs-safety" }, "safety") : null),
        h("div", { class: "gs-body" },
          h("p", { class: "small" }, h("span", { class: "label" }, "requires "), c.requires.map((u) => h("code", { class: failed.has(u) ? "gs-failed" : "" }, u)), kind === "channel" && c.timeout_s ? h("span", { class: "muted" }, ` · silence after ${c.timeout_s} s is the observable symptom`) : null),
          h("p", { class: "small" }, c.why), pins(c.source))));
  }
  function render() {
    const r = evaluateGroundStatus(model, failed);
    const lostCh = r.channels.filter((c) => !c.available).length, lostCap = r.capabilities.filter((c) => !c.available).length;
    clear(resultHost,
      h("p", { class: "label gs-summary" }, failed.size ? `${lostCh} of ${r.channels.length} channels and ${lostCap} of ${r.capabilities.length} capabilities lost` : "All units healthy. Fail one or more units above."),
      h("h4", {}, "Observable channels"), h("ul", { class: "gs-list" }, r.channels.map((c) => item(c, "channel"))),
      h("h4", {}, "Capabilities"), h("ul", { class: "gs-list" }, r.capabilities.map((c) => item(c, "capability"))),
      h("h4", {}, "Never available — absent, not failed"),
      h("ul", { class: "gs-list" }, model.absent_capabilities.map((c) => h("li", { class: "gs-item absent" }, h("details", {}, h("summary", {}, h("span", { class: "dep-dot" }), h("span", { class: "gs-name" }, c.name), h("span", { class: "gs-tag" }, "absent")), h("div", { class: "gs-body" }, h("p", { class: "small" }, c.why), pins(c.source)))))),
      h("details", { class: "gs-notmodeled" }, h("summary", { class: "label" }, "What the model does not cover (from the file)"), h("ul", { class: "small" }, model.not_modeled.map((t) => h("li", {}, t)))));
  }
  resetBtn.addEventListener("click", () => { failed.clear(); for (const b of unitsHost.querySelectorAll("button")) b.setAttribute("aria-pressed", "false"); render(); announce("All Project 33 units restored"); });
  render();
  return { failed, render };
}
