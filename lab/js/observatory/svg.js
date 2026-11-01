// SVG helpers for the Evidence Observatory.
export const NS = "http://www.w3.org/2000/svg";

export function s(tag, attrs = {}, ...children) {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "class") el.setAttribute("class", v);
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, String(v));
  }
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

/** Arc path on a circle (degrees, 0° = +x, clockwise in screen space). */
export function arc(cx, cy, r, a0, a1) {
  const p = (a) => [cx + r * Math.cos((a * Math.PI) / 180), cy + r * Math.sin((a * Math.PI) / 180)];
  const [x0, y0] = p(a0), [x1, y1] = p(a1);
  const large = Math.abs(a1 - a0) > 180 ? 1 : 0;
  return `M${x0.toFixed(2)},${y0.toFixed(2)} A${r},${r} 0 ${large} 1 ${x1.toFixed(2)},${y1.toFixed(2)}`;
}

export function polygon(cx, cy, r, sides, rotDeg = -90) {
  const pts = [];
  for (let i = 0; i < sides; i++) {
    const a = ((rotDeg + (360 * i) / sides) * Math.PI) / 180;
    pts.push(`${(cx + r * Math.cos(a)).toFixed(2)},${(cy + r * Math.sin(a)).toFixed(2)}`);
  }
  return pts.join(" ");
}

/**
 * Draw the status glyph of a claim. The shape carries the meaning, colour reinforces it:
 * contradicted = fractured ring, open = unfinished arc, supported = closed ring in scope brackets.
 */
export function claimGlyph(status, r) {
  const g = s("g", { class: `glyph glyph-${status}` });
  g.append(s("circle", { r: r - 1, class: "glyph-core" }));
  if (status === "contradicted") {
    g.append(s("path", { d: arc(0, 0, r, -62, 118), class: "ring" }));
    g.append(s("path", { d: arc(0, 0, r, 136, 280), class: "ring" }));
    // fracture: a zig-zag crack through the two gaps
    const crack = [[-0.92, -0.62], [-0.55, -0.36], [-0.7, -0.08], [-0.3, 0.06]].map(([x, y]) => `${(x * r).toFixed(1)},${(y * r).toFixed(1)}`);
    g.append(s("polyline", { points: crack.join(" "), class: "crack" }));
    const crack2 = [[0.45, 0.88], [0.62, 0.6], [0.4, 0.42]].map(([x, y]) => `${(x * r).toFixed(1)},${(y * r).toFixed(1)}`);
    g.append(s("polyline", { points: crack2.join(" "), class: "crack" }));
  } else if (status === "open") {
    g.append(s("path", { d: arc(0, 0, r, -90, 200), class: "ring ring-dashed" }));
    g.append(s("circle", { cx: r * Math.cos((200 * Math.PI) / 180), cy: r * Math.sin((200 * Math.PI) / 180), r: 2.2, class: "ring-end" }));
  } else if (status === "supported_within_limits") {
    g.append(s("circle", { r, class: "ring" }));
    const b = r + 7, h = r * 0.8;
    g.append(s("path", { d: `M${-b + 4},${-h} H${-b} V${h} H${-b + 4}`, class: "bracket" }));
    g.append(s("path", { d: `M${b - 4},${-h} H${b} V${h} H${b - 4}`, class: "bracket" }));
  } else {
    g.append(s("circle", { r, class: "ring ring-hollow" }));
  }
  return g;
}
