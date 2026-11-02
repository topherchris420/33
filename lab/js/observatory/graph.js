// The claim constellation: every claim, requirement, prediction, pre-registration,
// discrepancy, review and cited artifact, laid out deterministically on concentric orbits
// around the one node that is still empty — accepted physical measurements.
import { h } from "../core/dom.js";
import { EVIDENCE_CLASS_COLORS } from "../core/taxonomy.js";
import { s, arc, polygon, claimGlyph } from "./svg.js";

const SIZE = 1000;
const C = SIZE / 2;
export const RINGS = { core: 0, review: 116, claim: 178, requirement: 290, prediction: 344, preregistration: 344, discrepancy: 402, artifact: 458 };
const MIN_ARC = { review: 22, claim: 60, requirement: 30, prediction: 26, preregistration: 26, discrepancy: 30, artifact: 18 };

export const NODE_TYPES = {
  claim: { label: "Claim", shape: "status ring" },
  requirement: { label: "Requirement", shape: "diamond" },
  prediction: { label: "Prediction", shape: "target" },
  preregistration: { label: "Pre-registration", shape: "dashed square" },
  discrepancy: { label: "Discrepancy", shape: "triangle" },
  artifact: { label: "Artifact", shape: "square" },
  review: { label: "Review", shape: "hexagon" },
  core: { label: "Accepted measurements", shape: "empty instrument" },
};

const deg = (r) => (r * 180) / Math.PI;
const rad = (d) => (d * Math.PI) / 180;
const wrap = (a) => { let x = a % 360; if (x < -180) x += 360; if (x >= 180) x -= 360; return x; };

function circularMean(angles) {
  let sx = 0, sy = 0;
  for (const a of angles) { sx += Math.cos(rad(a)); sy += Math.sin(rad(a)); }
  return deg(Math.atan2(sy, sx));
}

/** Build nodes and edges from the evaluated record. */
export function buildGraph(ev) {
  const nodes = new Map();
  const edges = [];
  const art = new Map(ev.artifacts.map((a) => [a.id, a]));
  const req = new Map(ev.requirements.map((r) => [r.id, r]));
  const pred = new Map(ev.predictions.map((p) => [p.id, p]));
  const pre = new Map(ev.preregistrations.map((p) => [p.id, p]));
  const disc = new Map(ev.discrepancies.map((d) => [d.id, d]));
  const add = (id, type, data, extra = {}) => {
    if (!nodes.has(id)) nodes.set(id, { id, type, data, claims: new Set(), ...extra });
    return nodes.get(id);
  };
  const link = (a, b, kind) => edges.push({ from: a, to: b, kind });

  add("CORE", "core", { count: ev.counts.accepted_physical_measurements }, { label: "0" });
  ev.claims.forEach((c) => {
    const cn = add(c.id, "claim", c, { label: c.id });
    cn.claims.add(c.id);
    const rv = add(`REV:${c.id}`, "review", { claim: c.id, ...(ev.reviews[c.id]?.current || {}), freshness: c.freshness, freshness_label: c.freshness_label }, { label: "rev" });
    rv.claims.add(c.id); link(c.id, rv.id, "review");
    for (const rid of c.requirements) {
      const n = add(rid, "requirement", req.get(rid), { label: rid.replace(/^R-/, "") });
      n.claims.add(c.id); link(c.id, rid, "requirement");
    }
    for (const pid of c.predictions) {
      const n = add(pid, "prediction", pred.get(pid), { label: pid.replace(/^PRED-/, "") });
      n.claims.add(c.id); link(c.id, pid, "prediction");
    }
    for (const pid of c.preregistrations) {
      const n = add(pid, "preregistration", pre.get(pid), { label: pid });
      n.claims.add(c.id);
      const viaPred = (pre.get(pid)?.predictions || []).filter((x) => c.predictions.includes(x));
      if (viaPred.length) viaPred.forEach((x) => link(x, pid, "preregistration")); else link(c.id, pid, "preregistration");
    }
    for (const did of [...c.discrepancies_open, ...c.discrepancies_resolved]) {
      const n = add(did, "discrepancy", disc.get(did), { label: did });
      n.claims.add(c.id); link(c.id, did, "discrepancy");
    }
    for (const aid of c.evidence) {
      const n = add(`A:${aid}`, "artifact", art.get(aid), { label: aid });
      n.claims.add(c.id); link(c.id, n.id, "evidence");
    }
    for (const aid of c.historical) {
      const n = add(`A:${aid}`, "artifact", art.get(aid), { label: aid, historical: true });
      n.claims.add(c.id); link(c.id, n.id, "historical");
    }
  });
  // Records not attributed to a claim still belong in the constellation.
  for (const d of ev.discrepancies) add(d.id, "discrepancy", d, { label: d.id });
  for (const p of ev.predictions) add(p.id, "prediction", p, { label: p.id.replace(/^PRED-/, "") });
  for (const p of ev.preregistrations) {
    add(p.id, "preregistration", p, { label: p.id });
    for (const x of p.predictions || []) if (pred.has(x) && !edges.some((e) => e.from === x && e.to === p.id)) link(x, p.id, "preregistration");
  }
  for (const d of ev.discrepancies) {
    for (const side of d.sides) {
      if (!side.artifact || !art.has(side.artifact)) continue;
      const n = add(`A:${side.artifact}`, "artifact", art.get(side.artifact), { label: side.artifact });
      link(d.id, n.id, "side");
    }
  }
  // Everything still waiting on a physical measurement points at the empty core.
  for (const r of ev.requirements) if (r.result === "not_measured") link(r.id, "CORE", "awaiting");
  for (const p of ev.predictions) if (p.result === "not_measured") link(p.id, "CORE", "awaiting");
  // Unattributed nodes inherit claims from their neighbours, for placement only.
  for (const n of nodes.values()) {
    if (n.claims.size || n.type === "core") continue;
    for (const e of edges) {
      const other = e.from === n.id ? e.to : e.to === n.id ? e.from : null;
      if (other && nodes.get(other)?.claims.size) nodes.get(other).claims.forEach((c) => n.placementClaims = (n.placementClaims || new Set()).add(c));
    }
  }
  return { nodes, edges };
}

/** Deterministic polar layout: claim sectors, shared nodes at the circular mean, ring relaxation. */
export function layout(graph, claims) {
  const sector = 360 / claims.length;
  const claimAngle = new Map(claims.map((c, i) => [c.id, -90 + i * sector]));
  const byRing = new Map();
  for (const n of graph.nodes.values()) {
    if (n.type === "core") { n.x = C; n.y = C; continue; }
    const ring = n.type;
    if (!byRing.has(ring)) byRing.set(ring, []);
    byRing.get(ring).push(n);
  }
  for (const [ring, list] of byRing) {
    const r = RINGS[ring];
    // group exclusive nodes by claim to fan them across the sector
    const groups = new Map();
    for (const n of list) {
      const owners = [...(n.claims.size ? n.claims : n.placementClaims || [])];
      const key = owners.length === 1 ? owners[0] : "shared";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push({ n, owners });
    }
    let unowned = 0;
    for (const [key, items] of groups) {
      items.sort((a, b) => (a.n.id < b.n.id ? -1 : 1));
      items.forEach(({ n, owners }, i) => {
        if (key !== "shared") {
          const spread = Math.min(sector * 0.86, (items.length - 1) * deg(MIN_ARC[ring] / r));
          const t = items.length > 1 ? i / (items.length - 1) - 0.5 : 0;
          n.want = claimAngle.get(key) + t * spread;
        } else if (owners.length) {
          n.want = circularMean(owners.map((o) => claimAngle.get(o)));
        } else {
          n.want = -90 + sector / 2 + unowned++ * 9; // gap between C1 and C2, kept apart from claim sectors
        }
      });
    }
    relax(list, r, deg(MIN_ARC[ring] / r));
    for (const n of list) {
      n.angle = n.a;
      n.x = C + r * Math.cos(rad(n.a));
      n.y = C + r * Math.sin(rad(n.a));
    }
  }
}

function relax(list, r, minSep) {
  list.forEach((n) => { n.a = n.want; });
  if (list.length < 2) return;
  for (let iter = 0; iter < 400; iter++) {
    list.sort((p, q) => wrap(p.a + 90) - wrap(q.a + 90));
    let moved = false;
    for (let i = 0; i < list.length; i++) {
      const p = list[i], q = list[(i + 1) % list.length];
      let gap = wrap(q.a - p.a);
      if (i === list.length - 1) gap = (gap + 360) % 360;
      if (gap < minSep) {
        const push = (minSep - gap) / 2 + 0.01;
        p.a -= push; q.a += push; moved = true;
      }
    }
    for (const n of list) n.a += wrap(n.want - n.a) * 0.02;
    if (!moved && iter > 20) break;
  }
}

function edgePath(a, b) {
  // Gentle curve bowed toward the centre so orbits read as orbits.
  const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
  const k = 0.18;
  const cx = mx + (C - mx) * k, cy = my + (C - my) * k;
  return `M${a.x.toFixed(1)},${a.y.toFixed(1)} Q${cx.toFixed(1)},${cy.toFixed(1)} ${b.x.toFixed(1)},${b.y.toFixed(1)}`;
}

function requirementClass(r) { return `req-${r?.result || "unknown"}`; }

function nodeGlyph(n) {
  const g = s("g", { class: `node node-${n.type}`, transform: `translate(${n.x.toFixed(1)},${n.y.toFixed(1)})`, "data-id": n.id, "data-type": n.type });
  switch (n.type) {
    case "core": {
      g.append(s("circle", { r: 56, class: "core-halo" }), s("circle", { r: 44, class: "core-ring" }), s("circle", { r: 30, class: "core-ring core-ring-in" }));
      for (let i = 0; i < 24; i++) {
        const a = (i / 24) * 2 * Math.PI, r0 = i % 6 === 0 ? 34 : 38;
        g.append(s("line", { x1: r0 * Math.cos(a), y1: r0 * Math.sin(a), x2: 43 * Math.cos(a), y2: 43 * Math.sin(a), class: "core-tick" }));
      }
      g.append(s("text", { class: "core-num", y: 9 }, String(n.data.count)));
      g.append(s("text", { class: "core-cap", y: 24 }, "ACCEPTED"));
      break;
    }
    case "claim": {
      g.append(s("circle", { r: 34, class: "hit" }), claimGlyph(n.data.status, 26));
      g.append(s("text", { class: "claim-id", y: 5 }, n.id));
      // Titles sit above claims in the upper half and below in the lower half, clear of every orbit.
      const above = Math.sin(rad(n.angle)) < -0.1;
      g.append(s("text", { class: "claim-title", x: 0, y: above ? -40 : 50, "text-anchor": "middle" }, n.data.title));
      g.setAttribute("tabindex", "0");
      g.setAttribute("role", "button");
      g.setAttribute("aria-label", `${n.id}, ${n.data.title}. Status ${n.data.status_label}. Strongest accepted evidence ${n.data.support_label}. Press Enter to focus and open the passport.`);
      break;
    }
    case "requirement":
      g.append(s("circle", { r: 13, class: "hit" }), s("polygon", { points: polygon(0, 0, 9, 4, -90), class: `diamond ${requirementClass(n.data)}` }));
      if (n.data?.result === "conflicting") g.append(s("line", { x1: 0, y1: -9, x2: 0, y2: 9, class: "split" }));
      break;
    case "prediction":
      g.append(s("circle", { r: 12, class: "hit" }), s("circle", { r: 7.5, class: `target ${n.data?.result === "not_measured" ? "unmeasured" : ""}` }),
        s("line", { x1: -11, y1: 0, x2: 11, y2: 0, class: "cross" }), s("line", { x1: 0, y1: -11, x2: 0, y2: 11, class: "cross" }));
      break;
    case "preregistration":
      g.append(s("circle", { r: 12, class: "hit" }), s("rect", { x: -7, y: -7, width: 14, height: 14, class: `prereg prereg-${n.data?.status}` }));
      break;
    case "discrepancy": {
      const open = n.data?.status === "open";
      const strong = n.data?.effect === "contradicts_claim";
      g.append(s("circle", { r: 13, class: "hit" }), s("polygon", { points: polygon(0, 1.5, 10, 3, -90), class: `tri ${open ? "tri-open" : "tri-resolved"} ${strong ? "tri-strong" : ""}` }));
      break;
    }
    case "artifact": {
      const color = EVIDENCE_CLASS_COLORS[n.data?.class] || "#8fa2ad";
      const superseded = n.data?.status === "superseded";
      g.append(s("circle", { r: 9, class: "hit" }), s("rect", { x: -4.5, y: -4.5, width: 9, height: 9, class: `art ${superseded ? "art-superseded" : ""}`, style: `--c:${color}` }));
      break;
    }
    case "review": {
      const human = n.data?.kind === "human";
      g.append(s("circle", { r: 10, class: "hit" }), s("polygon", { points: polygon(0, 0, 7, 6, 0), class: `hex ${human ? "hex-human" : "hex-snapshot"}` }));
      break;
    }
    default: break;
  }
  if (n.type !== "claim" && n.type !== "core") {
    // Radial labels, read outward, flipped on the left half so they are never upside down.
    const a = wrap(n.angle);
    const flip = a > 90 || a < -90;
    const off = n.type === "artifact" ? 9 : 14;
    g.append(s("text", { class: "node-label", transform: `rotate(${(flip ? a + 180 : a).toFixed(2)})`, x: flip ? -off : off, y: 3, "text-anchor": flip ? "end" : "start" }, n.label));
  }
  return g;
}

/** Render the constellation and wire interactions. Returns a controller. */
export function renderConstellation(container, ev, { onSelect, tooltip }) {
  const graph = buildGraph(ev);
  layout(graph, ev.claims);
  const svg = s("svg", { viewBox: `0 0 ${SIZE} ${SIZE}`, class: "constellation", role: "group", "aria-label": "Claim constellation. Claims are focusable buttons; a table alternative follows the graph." });
  const defs = s("defs", {},
    s("radialGradient", { id: "obs-glow" }, s("stop", { offset: "0%", "stop-color": "rgba(103,216,207,0.22)" }), s("stop", { offset: "100%", "stop-color": "rgba(103,216,207,0)" })));
  svg.append(defs);
  const orbits = s("g", { class: "orbits", "aria-hidden": "true" });
  for (const [ring, r] of Object.entries(RINGS)) {
    if (!r || ring === "preregistration") continue;
    orbits.append(s("circle", { cx: C, cy: C, r, class: `orbit orbit-${ring}` }));
  }
  // ring captions at twelve o'clock, so the orbit grammar is legible
  const captions = [["requirement", "REQUIREMENTS"], ["prediction", "PREDICTIONS · PRE-REG."], ["discrepancy", "DISCREPANCIES"], ["artifact", "CITED ARTIFACTS"]];
  for (const [ring, text] of captions) {
    // set along the free boundary between the last and first claim sectors
    const r = RINGS[ring] + 6, id = `orbit-cap-${ring}`;
    orbits.append(s("path", { id, d: arc(C, C, r, -128, -102), fill: "none", stroke: "none" }));
    orbits.append(s("text", { class: "orbit-cap" }, s("textPath", { href: `#${id}`, startOffset: "50%", "text-anchor": "middle" }, text)));
  }
  svg.append(s("circle", { cx: C, cy: C, r: 120, fill: "url(#obs-glow)", "aria-hidden": "true" }), orbits);
  const edgeLayer = s("g", { class: "edges", "aria-hidden": "true" });
  const nodeLayer = s("g", { class: "nodes" });
  svg.append(edgeLayer, nodeLayer);
  const edgeEls = [];
  for (const e of graph.edges) {
    const a = graph.nodes.get(e.from), b = graph.nodes.get(e.to);
    if (!a || !b) continue;
    const el = s("path", { d: edgePath(a, b), class: `edge edge-${e.kind}`, "data-from": e.from, "data-to": e.to });
    edgeLayer.append(el);
    edgeEls.push({ ...e, el });
  }
  const nodeEls = new Map();
  // draw in z-order: artifacts first, claims and core last
  const order = ["artifact", "discrepancy", "preregistration", "prediction", "requirement", "review", "claim", "core"];
  [...graph.nodes.values()].sort((a, b) => order.indexOf(a.type) - order.indexOf(b.type)).forEach((n) => {
    const el = nodeGlyph(n);
    nodeLayer.append(el);
    nodeEls.set(n.id, el);
  });
  container.append(svg);

  const neighbours = new Map();
  for (const e of edgeEls) {
    if (!neighbours.has(e.from)) neighbours.set(e.from, new Set());
    if (!neighbours.has(e.to)) neighbours.set(e.to, new Set());
    neighbours.get(e.from).add(e.to); neighbours.get(e.to).add(e.from);
  }

  // ---------- view box animation, zoom and pan ----------
  let view = { x: 0, y: 0, w: SIZE, h: SIZE }, anim = null;
  const reduce = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const setView = (v) => {
    view = v;
    svg.setAttribute("viewBox", `${v.x.toFixed(1)} ${v.y.toFixed(1)} ${v.w.toFixed(1)} ${v.h.toFixed(1)}`);
    // Counter-scale text so labels keep a constant reading size while the geometry zooms.
    svg.style.setProperty("--z", (Math.sqrt(Math.max(v.w / SIZE, 0.2)) * textBoost).toFixed(3));
  };
  // On narrow screens enlarge text a little so claim titles stay legible without zooming.
  let textBoost = 1;
  new ResizeObserver(() => {
    const w = svg.clientWidth || SIZE;
    textBoost = Math.min(Math.max(640 / w, 1), 1.35);
    setView(view);
  }).observe(svg);
  function animateTo(target) {
    cancelAnimationFrame(anim);
    if (reduce()) { setView(target); return; }
    const from = { ...view }, start = performance.now(), dur = 650;
    const step = (now) => {
      const t = Math.min((now - start) / dur, 1), e = 1 - Math.pow(1 - t, 3);
      setView({ x: from.x + (target.x - from.x) * e, y: from.y + (target.y - from.y) * e, w: from.w + (target.w - from.w) * e, h: from.h + (target.h - from.h) * e });
      if (t < 1) anim = requestAnimationFrame(step);
    };
    anim = requestAnimationFrame(step);
  }
  function fitTo(ids, pad = 70) {
    const pts = ids.map((id) => graph.nodes.get(id)).filter(Boolean);
    if (!pts.length) return;
    let x0 = Math.min(...pts.map((p) => p.x)) - pad, x1 = Math.max(...pts.map((p) => p.x)) + pad;
    let y0 = Math.min(...pts.map((p) => p.y)) - pad, y1 = Math.max(...pts.map((p) => p.y)) + pad;
    let w = Math.max(x1 - x0, 560), hh = Math.max(y1 - y0, 560);
    const side = Math.max(w, hh);
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    animateTo({ x: cx - side / 2, y: cy - side / 2, w: side, h: side });
  }
  svg.addEventListener("wheel", (e) => {
    e.preventDefault();
    const rect = svg.getBoundingClientRect();
    const px = view.x + ((e.clientX - rect.left) / rect.width) * view.w;
    const py = view.y + ((e.clientY - rect.top) / rect.height) * view.h;
    const k = Math.exp(e.deltaY * 0.0015);
    const w = Math.min(Math.max(view.w * k, 160), SIZE * 1.4);
    const f = w / view.w;
    setView({ x: px - (px - view.x) * f, y: py - (py - view.y) * f, w, h: w });
  }, { passive: false });
  let drag = null;
  svg.addEventListener("pointerdown", (e) => {
    if (e.target.closest(".node")) return;
    drag = { x: e.clientX, y: e.clientY, v: { ...view } };
    svg.setPointerCapture(e.pointerId);
    svg.classList.add("dragging");
  });
  svg.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const rect = svg.getBoundingClientRect();
    const dx = ((e.clientX - drag.x) / rect.width) * view.w, dy = ((e.clientY - drag.y) / rect.height) * view.h;
    setView({ ...drag.v, x: drag.v.x - dx, y: drag.v.y - dy });
  });
  const endDrag = () => { drag = null; svg.classList.remove("dragging"); };
  svg.addEventListener("pointerup", endDrag);
  svg.addEventListener("pointercancel", endDrag);

  // ---------- focus / highlight ----------
  let focused = null, selected = null;
  const hiddenTypes = new Set(), hiddenStatuses = new Set();
  function applyVisibility() {
    const hiddenClaims = new Set(ev.claims.filter((c) => hiddenStatuses.has(c.status)).map((c) => c.id));
    for (const [id, el] of nodeEls) {
      const n = graph.nodes.get(id);
      let hide = hiddenTypes.has(n.type);
      if (n.type === "claim" && hiddenClaims.has(id)) hide = true;
      if (n.type !== "claim" && n.type !== "core" && n.claims.size && [...n.claims].every((c) => hiddenClaims.has(c))) hide = true;
      el.classList.toggle("is-hidden", hide);
      n.hidden = hide;
    }
    for (const e of edgeEls) e.el.classList.toggle("is-hidden", graph.nodes.get(e.from).hidden || graph.nodes.get(e.to).hidden);
  }
  function highlight(id, cls = "has-focus") {
    const keep = new Set([id, ...(neighbours.get(id) || [])]);
    const n = graph.nodes.get(id);
    if (n?.type === "claim") {
      // include the second hop from discrepancies and pre-registrations so the whole argument is visible
      for (const nb of neighbours.get(id) || []) {
        const t = graph.nodes.get(nb)?.type;
        if (t === "prediction" || t === "requirement") for (const x of neighbours.get(nb) || []) if (graph.nodes.get(x)?.type === "preregistration" || x === "CORE") keep.add(x);
      }
    }
    svg.classList.remove("has-focus", "has-hover");
    svg.classList.add(cls);
    for (const [nid, el] of nodeEls) { el.classList.toggle("is-lit", keep.has(nid)); el.classList.toggle("is-focus", nid === id); }
    for (const e of edgeEls) e.el.classList.toggle("is-lit", keep.has(e.from) && keep.has(e.to) && (e.from === id || e.to === id || graph.nodes.get(id)?.type === "claim"));
    return keep;
  }
  function clearHighlight() {
    svg.classList.remove("has-focus", "has-hover");
    for (const el of nodeEls.values()) el.classList.remove("is-lit", "is-focus");
    for (const e of edgeEls) e.el.classList.remove("is-lit");
  }
  function focus(id, { zoom = true, announceSelect = true } = {}) {
    const n = graph.nodes.get(id);
    if (!n) return false;
    focused = id; selected = id;
    const keep = highlight(id);
    if (zoom) fitTo([...keep].filter((k) => k !== "CORE" || n.type !== "claim"));
    if (announceSelect) onSelect?.(n);
    return true;
  }
  function reset() {
    focused = null; selected = null;
    clearHighlight();
    animateTo({ x: 0, y: 0, w: SIZE, h: SIZE });
  }

  // ---------- events ----------
  nodeLayer.addEventListener("click", (e) => {
    const g = e.target.closest(".node");
    if (!g) return;
    focus(g.dataset.id, { zoom: g.dataset.type === "claim" });
  });
  nodeLayer.addEventListener("keydown", (e) => {
    const g = e.target.closest(".node");
    if (!g) return;
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); focus(g.dataset.id); }
  });
  svg.addEventListener("keydown", (e) => { if (e.key === "Escape") reset(); });
  nodeLayer.addEventListener("pointerover", (e) => {
    const g = e.target.closest(".node");
    if (!g) return;
    const n = graph.nodes.get(g.dataset.id);
    tooltip?.show(n, e);
    if (!focused) highlight(n.id, "has-hover");
  });
  nodeLayer.addEventListener("pointermove", (e) => { if (e.target.closest(".node")) tooltip?.move(e); });
  nodeLayer.addEventListener("pointerout", (e) => {
    const g = e.target.closest(".node");
    if (!g || g.contains(e.relatedTarget)) return;
    tooltip?.hide();
    if (!focused) clearHighlight(); else highlight(focused);
  });
  nodeLayer.addEventListener("focusin", (e) => {
    const g = e.target.closest(".node");
    if (g && !focused) highlight(g.dataset.id, "has-hover");
  });
  nodeLayer.addEventListener("focusout", () => { if (!focused) clearHighlight(); });

  return {
    graph, svg, focus, reset, fitTo,
    get focused() { return focused; },
    setTypeVisible(type, visible) { if (visible) hiddenTypes.delete(type); else hiddenTypes.add(type); applyVisibility(); },
    setStatusVisible(status, visible) { if (visible) hiddenStatuses.delete(status); else hiddenStatuses.add(status); applyVisibility(); },
    zoom(k) { const w = Math.min(Math.max(view.w * k, 160), SIZE * 1.4); const cx = view.x + view.w / 2, cy = view.y + view.h / 2; animateTo({ x: cx - w / 2, y: cy - w / 2, w, h: w }); },
    search(query) {
      const q = query.trim().toLowerCase();
      if (!q) return [];
      const hits = [...graph.nodes.values()].filter((n) => n.type !== "core" && !n.hidden && (n.id.toLowerCase().includes(q) || n.label.toLowerCase().includes(q)
        || (n.type === "claim" && n.data.title.toLowerCase().includes(q))
        || (n.type === "discrepancy" && n.data.title.toLowerCase().includes(q))
        || (n.type === "artifact" && n.data.path.toLowerCase().includes(q))));
      const rank = (n) => (n.id.toLowerCase() === q || n.label.toLowerCase() === q ? 0 : n.id.toLowerCase().startsWith(q) ? 1 : 2);
      hits.sort((a, b) => rank(a) - rank(b) || (a.id < b.id ? -1 : 1));
      return hits;
    },
    nodeElement: (id) => nodeEls.get(id),
  };
}

/** Floating tooltip for graph nodes. */
export function makeTooltip(host) {
  const tip = h("div", { class: "obs-tip", role: "tooltip", hidden: true });
  host.append(tip);
  const describe = (n) => {
    const d = n.data || {};
    switch (n.type) {
      case "claim": return [n.id, d.title, `${d.status_label} · ${d.support_label} · gate: ${d.gate_label}`];
      case "requirement": return [n.id, d.text, `${d.label}${d.evidence_class ? ` (${d.evidence_class})` : ""} · check: ${d.check}`];
      case "prediction": return [n.id, d.quantity, `${d.result_label} · predicted ${d.predicted ?? "—"} ${d.unit || ""}`];
      case "preregistration": return [n.id, d.title, `${(d.status || "").toUpperCase()} — drafted, not registered by a human`];
      case "discrepancy": return [n.id, d.title, `${(d.status || "").toUpperCase()} · ${d.kind?.replace(/_/g, " ")}`];
      case "artifact": return [n.label, d.path, `${d.class_label}${d.status === "superseded" ? " · SUPERSEDED (failure archive)" : ""}`];
      case "review": return [`Review of ${d.claim}`, d.recorded_by || "never reviewed", `${d.freshness_label} · ${d.kind === "human" ? "human review" : "tooling snapshot — not an engineering review"}`];
      case "core": return ["Accepted physical measurements", "Inert measurements accepted by a named human", `${d.count} — every dashed line is a requirement or prediction waiting here`];
      default: return [n.id, "", ""];
    }
  };
  return {
    show(n, e) {
      const [a, b, c] = describe(n);
      tip.replaceChildren(h("b", {}, a), b ? h("span", {}, b) : null, c ? h("small", {}, c) : null);
      tip.hidden = false;
      this.move(e);
    },
    move(e) {
      const r = host.getBoundingClientRect();
      let x = e.clientX - r.left + 14, y = e.clientY - r.top + 14;
      const w = tip.offsetWidth, hh = tip.offsetHeight;
      if (x + w > r.width - 6) x = e.clientX - r.left - w - 14;
      if (y + hh > r.height - 6) y = e.clientY - r.top - hh - 14;
      tip.style.transform = `translate(${Math.max(4, x)}px, ${Math.max(4, y)}px)`;
    },
    hide() { tip.hidden = true; },
  };
}
