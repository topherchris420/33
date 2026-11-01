// The evidence ladder: where each claim stands on the validation gates and on the support
// scale. Physical rungs are drawn — and visibly empty — so a model never looks like a measurement.
import { h } from "../core/dom.js";
import { s, claimGlyph } from "./svg.js";

const ROW = 46, TOP = 26, LEFT = 210, COL = 54;

function ladder({ title, caption, rungs, positionOf, boundary, boundaryText, physicalFrom, physicalText, claims, onPick, kind }) {
  const height = TOP + rungs.length * ROW + 46;
  const width = LEFT + claims.length * COL + 24;
  const y = (i) => TOP + (rungs.length - 1 - i) * ROW + ROW / 2;
  const svg = s("svg", { viewBox: `0 0 ${width} ${height}`, class: `ladder ladder-${kind}`, role: "img", "aria-label": `${title}. ${caption}` });
  // physical zone
  const yPhysTop = TOP, yPhysBottom = y(physicalFrom) + ROW / 2;
  svg.append(s("rect", { x: LEFT - 12, y: yPhysTop, width: width - LEFT, height: yPhysBottom - yPhysTop, class: "phys-zone" }));
  svg.append(s("text", { x: width - 14, y: yPhysTop + 14, class: "phys-cap", "text-anchor": "end" }, physicalText));
  rungs.forEach(([key, label], i) => {
    svg.append(s("line", { x1: LEFT - 12, x2: width - 12, y1: y(i), y2: y(i), class: `rung ${i >= physicalFrom ? "rung-phys" : ""}` }));
    svg.append(s("text", { x: LEFT - 22, y: y(i) + 4, class: `rung-label ${i >= physicalFrom ? "rung-label-phys" : ""}`, "text-anchor": "end" }, label));
  });
  // human gate
  const yb = y(boundary) + ROW / 2;
  svg.append(s("line", { x1: 12, x2: width - 12, y1: yb, y2: yb, class: "human-line" }));
  svg.append(s("text", { x: 14, y: yb - 6, class: "human-cap" }, boundaryText));
  claims.forEach((c, j) => {
    const x = LEFT + j * COL + COL / 2;
    const level = positionOf(c);
    const g = s("g", { class: "ladder-claim", tabindex: "0", role: "button", "data-claim": c.id,
      "aria-label": `${c.id}: ${rungs[level]?.[1] || "none"}. Status ${c.status_label}.` });
    g.append(s("rect", { x: x - COL / 2 + 3, y: TOP, width: COL - 6, height: height - TOP - 8, class: "col-hit", rx: 3 }));
    g.append(s("line", { x1: x, x2: x, y1: y(0) + ROW / 2 - 6, y2: y(level), class: `fill fill-${c.status}` }));
    for (let i = 0; i < rungs.length; i++) {
      if (i <= level) g.append(s("circle", { cx: x, cy: y(i), r: 3, class: "tick-on" }));
      else g.append(s("circle", { cx: x, cy: y(i), r: 3, class: `tick-off ${i >= physicalFrom ? "tick-phys" : ""}` }));
    }
    const glyph = claimGlyph(c.status, 11);
    glyph.setAttribute("transform", `translate(${x},${y(level)})`);
    g.append(glyph);
    g.append(s("text", { x, y: height - 22, class: "ladder-id", "text-anchor": "middle" }, c.id));
    g.addEventListener("click", () => onPick(c.id));
    g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onPick(c.id); } });
    svg.append(g);
  });
  return h("figure", { class: "panel ticked ladder-fig" },
    h("div", { class: "panel-head" }, h("h4", {}, title)),
    h("div", { class: "panel-body" }, svg, h("figcaption", { class: "muted small" }, caption)));
}

export function renderLadders(container, ev, onPick) {
  const gates = ev.vocabulary.gates;
  const support = ev.vocabulary.support_levels;
  const gateIndex = (c) => gates.findIndex(([k]) => k === c.gate);
  const supportIndex = (c) => support.findIndex(([k]) => k === c.support);
  container.append(
    ladder({
      kind: "gates", title: "Validation gate reached", rungs: gates, claims: ev.claims, onPick,
      positionOf: gateIndex,
      boundary: gates.findIndex(([k]) => k === "synthetic_test"),
      boundaryText: "HUMAN GATE — ONLY A NAMED HUMAN CAN CROSS",
      physicalFrom: gates.findIndex(([k]) => k === "inert_physical_measurement"),
      physicalText: "PHYSICAL — NO CLAIM HAS REACHED THESE RUNGS",
      caption: "Gates from inert bench setup onward need a human-registered pre-registration or a human-accepted inert measurement. No AI model, CI run, or repository setting can move a claim across them.",
    }),
    ladder({
      kind: "support", title: "Strongest accepted evidence", rungs: support, claims: ev.claims, onPick,
      positionOf: supportIndex,
      boundary: support.findIndex(([k]) => k === "software"),
      boundaryText: "ONLY A HUMAN-ACCEPTED INERT MEASUREMENT LIFTS A CLAIM ABOVE THIS LINE",
      physicalFrom: support.findIndex(([k]) => k === "bench_observed"),
      physicalText: "PHYSICAL — EMPTY",
      caption: "Support is derived, never authored. Implementation and model support sit below the line; software verification would too. A supported software implementation is not demonstrated physical performance.",
    }));
}
