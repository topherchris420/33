// Minimal SVG helpers for the Mechanism Lab charts.
export const NS = "http://www.w3.org/2000/svg";

export function s(tag, attrs = {}, ...children) {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "text") el.textContent = v;
    else el.setAttribute(k, String(v));
  }
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

export function svgRoot(width, height, label) {
  return s("svg", { viewBox: `0 0 ${width} ${height}`, class: "mx-svg", role: "img", "aria-label": label, preserveAspectRatio: "xMidYMid meet" });
}

export function path(points, closed = false) {
  if (!points.length) return "";
  return points.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join("") + (closed ? "Z" : "");
}

export function hatchPattern(id, color, { angle = 45, gap = 6, width = 1, opacity = 0.5 } = {}) {
  return s("pattern", { id, patternUnits: "userSpaceOnUse", width: gap, height: gap, patternTransform: `rotate(${angle})` },
    s("line", { x1: 0, y1: 0, x2: 0, y2: gap, stroke: color, "stroke-width": width, "stroke-opacity": opacity }));
}

export function arrowMarker(id, color) {
  return s("marker", { id, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse" },
    s("path", { d: "M0,0 L10,5 L0,10 z", fill: color }));
}

export const C = {
  ivory: "#f1e9d6", ivoryDim: "#cfc6b2", muted: "#8fa2ad", faint: "#5e717c", line: "#eef6f8",
  teal: "#0b5d63", teal4: "#2fb3ae", teal3: "#67d8cf", copper: "#c47a45", copper3: "#e0a274",
  bad: "#e07650", amber: "#e3c27a", ok: "#4cc9bb", grid: "rgba(103,216,207,0.08)", g500: "#33434f", g600: "#24313b",
};
