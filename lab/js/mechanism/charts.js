// Charts for the Mechanism Lab. Every plotted value is either read from a committed file
// or computed with the tested four-bar port; captions say which.
import { s, svgRoot, path, hatchPattern, arrowMarker, C } from "./svg.js";
import { diagonal, transmissionAngle, closureResidual } from "../core/math/fourbar.js";

/* ---------------- Residual chart: f(θ) over 0–360° against the closure band ---------------- */
export function residualChart(container) {
  const W = 960, H = 330, L = 60, R = 26, T = 26, B = 48;
  const root = svgRoot(W, H, "Loop diagonal versus drive angle");
  const defs = s("defs", {}, hatchPattern("mx-band", C.teal3, { gap: 7, opacity: 0.35 }), arrowMarker("mx-arr", C.bad));
  const layer = s("g");
  root.append(defs, layer);
  container.replaceChildren(root);
  let state = null;

  function draw(cfg, theta) {
    const { a, b, c, d } = cfg;
    const lo = Math.abs(c - d), hi = c + d;
    const yMax = Math.ceil((Math.max(hi, a + b) * 1.12) / 10) * 10;
    const x = (t) => L + (t / 360) * (W - L - R);
    const y = (v) => T + (1 - v / yMax) * (H - T - B);
    const curve = [], inRange = [];
    for (let t = 0; t <= 360; t += 1) { const p = [x(t), y(diagonal(a, b, t))]; curve.push(p); if (t <= 92) inRange.push(p); }
    let maxIn = 0, maxInT = 0;
    for (let t = 0; t <= 92; t += 0.5) { const f = diagonal(a, b, t); if (f > maxIn) { maxIn = f; maxInT = t; } }
    const fMaxAll = a + b;
    const ticks = [];
    for (let t = 0; t <= 360; t += 45) ticks.push(s("g", { class: "tick" }, s("line", { x1: x(t), x2: x(t), y1: H - B, y2: H - B + 5, stroke: C.g500 }), s("text", { x: x(t), y: H - B + 18, "text-anchor": "middle", text: `${t}°` })));
    for (let v = 0; v <= yMax; v += 10) ticks.push(s("g", { class: "tick" }, s("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), stroke: C.grid }), s("text", { x: L - 8, y: y(v) + 3.5, "text-anchor": "end", text: v })));
    const fNow = diagonal(a, b, theta);
    const eps = closureResidual(a, b, c, d, theta);
    const target = fNow < lo ? lo : fNow > hi ? hi : fNow;
    layer.replaceChildren(
      ...ticks,
      s("rect", { x: x(0), y: T, width: x(92) - x(0), height: H - T - B, fill: "rgba(241,233,214,0.055)", stroke: "rgba(241,233,214,0.25)", "stroke-dasharray": "3 4" }),
      s("text", { x: x(0) + 6, y: T + 14, fill: C.ivoryDim, "font-size": 10.5, text: "RECORDED DRIVE RANGE 0–92°" }),
      s("rect", { x: L, y: y(Math.min(hi, yMax)), width: W - L - R, height: y(lo) - y(Math.min(hi, yMax)), fill: "url(#mx-band)" }),
      s("line", { x1: L, x2: W - R, y1: y(lo), y2: y(lo), stroke: C.teal3, "stroke-width": 1.2 }),
      hi <= yMax ? s("line", { x1: L, x2: W - R, y1: y(hi), y2: y(hi), stroke: C.teal3, "stroke-width": 1.2 }) : null,
      s("text", { x: W - R - 6, y: y(lo) + 14, fill: C.teal3, "text-anchor": "end", "font-size": 11, text: `|c − d| = ${lo.toFixed(1)} mm` }),
      hi <= yMax ? s("text", { x: W - R - 6, y: y(hi) - 6, fill: C.teal3, "text-anchor": "end", "font-size": 11, text: `c + d = ${hi.toFixed(1)} mm` }) : null,
      s("text", { x: x(200), y: (y(lo) + y(Math.min(hi, yMax))) / 2 + 4, fill: C.teal3, "text-anchor": "middle", "font-size": 11.5, text: "THE LOOP CAN CLOSE ONLY WHEN f(θ) IS INSIDE THIS BAND" }),
      s("path", { d: path(curve), fill: "none", stroke: C.ivoryDim, "stroke-width": 1.3, "stroke-opacity": 0.6 }),
      s("path", { d: path(inRange), fill: "none", stroke: C.ivory, "stroke-width": 2.6 }),
      s("circle", { cx: x(maxInT), cy: y(maxIn), r: 4, fill: C.ivory }),
      s("text", { x: x(maxInT) + 8, y: y(maxIn) - 8, fill: C.ivory, "font-size": 11, text: `max in range ${maxIn.toFixed(1)} mm (θ = ${maxInT}°)` }),
      s("circle", { cx: x(180), cy: y(fMaxAll), r: 3.5, fill: "none", stroke: C.ivoryDim }),
      s("text", { x: x(180), y: y(fMaxAll) + (Math.abs(fMaxAll - lo) < yMax * 0.08 ? 20 : -9), fill: C.ivoryDim, "text-anchor": "middle", "font-size": 11, text: `max at any angle ${fMaxAll.toFixed(1)} mm (a + b, θ = 180°)` }),
      s("line", { x1: x(theta), x2: x(theta), y1: T, y2: H - B, stroke: C.copper3, "stroke-width": 1, "stroke-dasharray": "2 3" }),
      eps > 0 ? s("line", { x1: x(theta), x2: x(theta), y1: y(fNow), y2: y(target), stroke: C.bad, "stroke-width": 2, "marker-end": "url(#mx-arr)" }) : null,
      s("circle", { cx: x(theta), cy: y(fNow), r: 5, fill: "#09111a", stroke: C.copper3, "stroke-width": 2 }),
      s("text", { x: x(theta) + 10, y: (y(fNow) + y(target)) / 2 + 4, fill: eps > 0 ? C.bad : C.ok, "font-size": 12, "font-weight": 500, text: eps > 0 ? `ε = ${eps.toFixed(2)} mm` : "closes" }),
      s("text", { x: L, y: H - 10, fill: C.muted, "font-size": 10.5, text: "Drive angle θ" }),
      s("text", { x: 14, y: T - 8, fill: C.muted, "font-size": 10.5, text: "Distance (mm)" }),
    );
    root.setAttribute("aria-label", `Loop diagonal f between ${diagonal(a, b, 0).toFixed(1)} and ${maxIn.toFixed(1)} mm over the 0 to 92 degree range; the loop needs ${lo.toFixed(1)} to ${hi.toFixed(1)} mm. Current angle ${theta} degrees, residual ${eps.toFixed(2)} mm.`);
    state = { maxIn, maxInT, fMaxAll };
    return state;
  }
  return { draw, root };
}

/* ---------------- Transmission angle over the drive range ---------------- */
export function transmissionChart(container) {
  const W = 520, H = 230, L = 44, R = 14, T = 16, B = 34;
  const root = svgRoot(W, H, "Transmission angle over the drive range");
  const layer = s("g");
  root.append(s("defs", {}, hatchPattern("mx-mu", C.ok, { gap: 6, opacity: 0.3 })), layer);
  container.replaceChildren(root);
  function draw(cfg) {
    const { a, b, c, d } = cfg;
    const x = (t) => L + (t / 92) * (W - L - R);
    const y = (m) => T + (1 - m / 180) * (H - T - B);
    const segs = []; let cur = [];
    const gaps = [];
    for (let t = 0; t <= 92; t += 0.5) {
      const m = transmissionAngle(a, c, b, d, t);
      if (m === null) { if (cur.length) segs.push(cur); cur = []; gaps.push(t); } else cur.push([x(t), y(m)]);
    }
    if (cur.length) segs.push(cur);
    const ticks = [];
    for (let m = 0; m <= 180; m += 45) ticks.push(s("g", { class: "tick" }, s("line", { x1: L, x2: W - R, y1: y(m), y2: y(m), stroke: C.grid }), s("text", { x: L - 6, y: y(m) + 3.5, "text-anchor": "end", text: `${m}°` })));
    for (let t = 0; t <= 92; t += 23) ticks.push(s("g", { class: "tick" }, s("text", { x: x(t), y: H - B + 16, "text-anchor": "middle", text: `${t}°` })));
    layer.replaceChildren(...ticks,
      s("rect", { x: L, y: y(140), width: W - L - R, height: y(40) - y(140), fill: "url(#mx-mu)" }),
      s("text", { x: W - R - 4, y: y(140) + 13, "text-anchor": "end", fill: C.ok, "font-size": 10.5, text: "R-C1-TRANSMISSION band 40–140°" }),
      ...gaps.map((t) => s("line", { x1: x(t), x2: x(t), y1: H - B - 6, y2: H - B, stroke: C.bad, "stroke-width": 1.5 })),
      ...segs.map((sg) => s("path", { d: path(sg), fill: "none", stroke: C.ivory, "stroke-width": 2.2 })),
      s("text", { x: L, y: H - 6, fill: C.muted, "font-size": 10, text: "θ (drive angle)   ·   red ticks: no real μ — the loop does not close" }),
    );
  }
  return { draw };
}

/* ---------------- Design-space heatmap (conceptual) ---------------- */
export const HEAT = {
  none: [12, 22, 33], partial: [66, 52, 34], outside: [227, 194, 122], within: [47, 179, 174],
};

export function classify(a, b, c, d) {
  let closed = 0, mMin = Infinity, mMax = -Infinity;
  for (let t = 0; t <= 92; t += 2) {
    const m = transmissionAngle(a, c, b, d, t);
    if (m !== null) { closed++; mMin = Math.min(mMin, m); mMax = Math.max(mMax, m); }
  }
  if (closed === 0) return { k: "none", closed };
  if (closed < 47) return { k: "partial", closed, mMin, mMax };
  if (mMin >= 40 && mMax <= 140) return { k: "within", closed, mMin, mMax };
  return { k: "outside", closed, mMin, mMax };
}

export function designHeatmap(canvas, { cRange = [5, 90], dRange = [5, 40] } = {}) {
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  const pad = { l: 48, r: 10, t: 10, b: 42 };
  const nx = 170, ny = 70;
  let grid = null, last = null;
  const cx = (c) => pad.l + ((c - cRange[0]) / (cRange[1] - cRange[0])) * (W - pad.l - pad.r);
  const dy = (d) => H - pad.b - ((d - dRange[0]) / (dRange[1] - dRange[0])) * (H - pad.t - pad.b);
  function compute(a, b) {
    grid = new Array(nx * ny);
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
      const c = cRange[0] + ((i + 0.5) / nx) * (cRange[1] - cRange[0]);
      const d = dRange[0] + ((j + 0.5) / ny) * (dRange[1] - dRange[0]);
      grid[j * nx + i] = classify(a, b, c, d).k;
    }
    last = { a, b };
  }
  function draw(cfg, marks = []) {
    if (!last || last.a !== cfg.a || last.b !== cfg.b) compute(cfg.a, cfg.b);
    ctx.fillStyle = "#060a10"; ctx.fillRect(0, 0, W, H);
    const img = ctx.createImageData(nx, ny);
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
      const col = HEAT[grid[j * nx + i]];
      const o = ((ny - 1 - j) * nx + i) * 4;
      img.data[o] = col[0]; img.data[o + 1] = col[1]; img.data[o + 2] = col[2]; img.data[o + 3] = 255;
    }
    const off = document.createElement("canvas"); off.width = nx; off.height = ny;
    off.getContext("2d").putImageData(img, 0, 0);
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(off, pad.l, pad.t, W - pad.l - pad.r, H - pad.t - pad.b);
    ctx.strokeStyle = "rgba(143,162,173,0.5)"; ctx.lineWidth = 1;
    ctx.strokeRect(pad.l + 0.5, pad.t + 0.5, W - pad.l - pad.r - 1, H - pad.t - pad.b - 1);
    ctx.fillStyle = "#8fa2ad"; ctx.font = "12px 'Plex Mono', monospace"; ctx.textAlign = "center";
    for (let c = 10; c <= cRange[1]; c += 10) ctx.fillText(String(c), cx(c), H - pad.b + 16);
    ctx.textAlign = "right";
    for (let d = 10; d <= dRange[1]; d += 10) ctx.fillText(String(d), pad.l - 6, dy(d) + 4);
    ctx.textAlign = "left";
    ctx.textAlign = "right"; ctx.fillText("coupler c (mm) →", W - pad.r, H - 5); ctx.textAlign = "left";
    ctx.save(); ctx.translate(12, H - pad.b - 4); ctx.rotate(-Math.PI / 2); ctx.fillText("output d (mm) →", 0, 0); ctx.restore();
    marks.forEach((m, idx) => {
      if (m.c < cRange[0] || m.c > cRange[1] || m.d < dRange[0] || m.d > dRange[1]) return;
      const px = cx(m.c), py = dy(m.d);
      ctx.strokeStyle = m.color; ctx.lineWidth = 2;
      ctx.beginPath();
      if (m.cross) { ctx.moveTo(px - 8, py); ctx.lineTo(px + 8, py); ctx.moveTo(px, py - 8); ctx.lineTo(px, py + 8); }
      else ctx.arc(px, py, 6, 0, Math.PI * 2);
      ctx.stroke();
      ctx.fillStyle = m.color; ctx.font = "12px 'Plex Mono', monospace";
      ctx.textAlign = m.align || (m.c > (cRange[0] + cRange[1]) / 2 ? "right" : "left");
      ctx.fillText(m.label, px + (ctx.textAlign === "right" ? -10 : 10), py + (m.dy ?? -9) + idx * 0);
    });
  }
  function pick(evt) {
    const r = canvas.getBoundingClientRect();
    const px = ((evt.clientX - r.left) / r.width) * W, py = ((evt.clientY - r.top) / r.height) * H;
    const c = cRange[0] + ((px - pad.l) / (W - pad.l - pad.r)) * (cRange[1] - cRange[0]);
    const d = dRange[0] + ((H - pad.b - py) / (H - pad.t - pad.b)) * (dRange[1] - dRange[0]);
    if (c < cRange[0] || c > cRange[1] || d < dRange[0] || d > dRange[1]) return null;
    return { c: Math.round(c * 2) / 2, d: Math.round(d * 2) / 2 };
  }
  const count = (k) => (grid ? grid.filter((g) => g === k).length : 0);
  return { draw, pick, count };
}

/* ---------------- C5: caliber axis ---------------- */
export function caliberAxis({ window: win, reference, textbook }) {
  const W = 960, H = 200, L = 40, R = 30;
  const max = 2.5;
  const x = (v) => L + (v / max) * (W - L - R);
  const root = svgRoot(W, H, `Static margin: reference ${reference.min}–${reference.max} cal, textbook ${textbook.min.toFixed(2)}–${textbook.max.toFixed(2)} cal, requirement window ${win.min}–${win.max} cal`);
  root.append(s("defs", {}, hatchPattern("mx-win", C.ok, { gap: 7, opacity: 0.35 })));
  const ticks = [];
  for (let v = 0; v <= max + 1e-9; v += 0.25) {
    const major = Math.abs(v * 2 - Math.round(v * 2)) < 1e-9;
    ticks.push(s("line", { x1: x(v), x2: x(v), y1: 150, y2: major ? 158 : 154, stroke: C.g500 }));
    if (major) ticks.push(s("text", { x: x(v), y: 174, "text-anchor": "middle", class: "tick", fill: C.muted, "font-size": 11, text: v.toFixed(1) }));
  }
  const bar = (iv, yy, color, label, src) => {
    const x0 = x(iv.min), x1 = Math.max(x(iv.max), x0 + 5);
    return s("g", {},
      s("rect", { x: x0, y: yy - 9, width: x1 - x0, height: 18, fill: color, rx: 2 }),
      s("line", { x1: x0, x2: x0, y1: yy - 14, y2: yy + 14, stroke: color, "stroke-width": 1.5 }),
      s("line", { x1: x1, x2: x1, y1: yy - 14, y2: yy + 14, stroke: color, "stroke-width": 1.5 }),
      s("text", { x: x1 + 10, y: yy - 2, fill: color, "font-size": 12, "font-weight": 500, text: label }),
      s("text", { x: x1 + 10, y: yy + 13, fill: C.muted, "font-size": 10, text: src }));
  };
  root.append(
    s("rect", { x: x(win.min), y: 18, width: x(win.max) - x(win.min), height: 132, fill: "url(#mx-win)", stroke: C.ok, "stroke-opacity": 0.6 }),
    s("text", { x: x(win.min) + 6, y: 32, fill: C.ok, "font-size": 11, text: `R-C5-WINDOW ${win.min}–${win.max} cal` }),
    s("line", { x1: L, x2: W - R, y1: 150, y2: 150, stroke: C.g500 }),
    ...ticks,
    bar(reference, 62, C.teal3, `Reference ${reference.min.toFixed(2)}–${reference.max.toFixed(2)} cal`, "static_margin.py → docs/EVIDENCE/C5_static_margin.csv"),
    bar(textbook, 112, C.amber, `Textbook cross-check ${textbook.min.toFixed(2)}–${textbook.max.toFixed(2)} cal`, "barrowman_crosscheck.py → C5_barrowman_crosscheck.json"),
    s("text", { x: L, y: 194, fill: C.muted, "font-size": 10.5, text: "Static margin (calibers) = (x_CP − x_CG) / d_ref" }),
  );
  return root;
}

/* ---------------- C5: side elevation with CG / CP stations ---------------- */
export function stabilityElevation({ elevation, stations, ghostFin, dRef }) {
  const len = elevation.length;
  const W = 980, padL = 30, padR = 30;
  const sc = (W - padL - padR) / len;
  const finTop = Math.max(...elevation.parts.filter((p) => p.kind === "trapezoidfinset").map((p) => p.rootRadius + p.span));
  const bodyR = Math.max(...elevation.parts.filter((p) => p.radius).map((p) => p.radius));
  const axisY = 26 + finTop * sc;
  const rows = stations.length;
  const H = axisY + bodyR * sc + 40 + rows * 26;
  const X = (mm) => padL + mm * sc, Y = (mm) => axisY - mm * sc;
  const root = svgRoot(W, H, "Side elevation of the OpenRocket model with centre-of-gravity and centre-of-pressure stations");
  root.classList.add("mx-elev");
  root.append(s("defs", {}, hatchPattern("mx-body", C.teal3, { gap: 5, opacity: 0.15 })));
  const draw = [];
  for (const p of elevation.paths) {
    if (p.id.endsWith("--1")) continue; // fins drawn in the upper half only
    const pts = p.points.map(([x, y]) => [X(x), Y(y)]);
    draw.push(s("path", { d: path(pts, p.closed), fill: p.id === "body" ? "url(#mx-body)" : p.fin ? "rgba(103,216,207,0.08)" : "none", stroke: p.thin ? C.g500 : C.line, "stroke-width": p.thin ? 1 : 1.4 }));
  }
  if (ghostFin) {
    const g = ghostFin;
    const pts = [[g.x0, g.r], [g.x0 + g.sweep, g.r + g.span], [g.x0 + g.sweep + g.tip, g.r + g.span], [g.x0 + g.root, g.r]].map(([x, y]) => [X(x), Y(y)]);
    draw.push(s("path", { d: path(pts), fill: "none", stroke: C.amber, "stroke-width": 1.5, "stroke-dasharray": "5 4" }),
      s("text", { x: X(g.x0 + g.sweep) - 4, y: Y(g.r + g.span) - 8, fill: C.amber, "font-size": 10.5, "text-anchor": "end", text: g.label }));
  }
  draw.push(s("line", { x1: X(-10), x2: X(len + 10), y1: axisY, y2: axisY, stroke: C.faint, "stroke-dasharray": "14 4 2 4" }));
  const baseY = axisY + bodyR * sc + 28;
  stations.forEach((st, i) => {
    const yy = baseY + i * 26;
    const x0 = X(st.min), x1 = X(st.max ?? st.min);
    const col = st.color;
    draw.push(s("line", { x1: x0, x2: x0, y1: Y(st.top ?? bodyR), y2: yy, stroke: col, "stroke-width": 1, "stroke-dasharray": st.dashed ? "3 3" : null, "stroke-opacity": 0.8 }));
    if (st.max !== undefined && x1 - x0 > 1) {
      draw.push(s("rect", { x: x0, y: yy - 6, width: x1 - x0, height: 12, fill: col, "fill-opacity": 0.28, stroke: col }));
      draw.push(s("line", { x1: x1, x2: x1, y1: Y(st.top ?? bodyR), y2: yy, stroke: col, "stroke-width": 1, "stroke-dasharray": "3 3", "stroke-opacity": 0.6 }));
    }
    if (st.symbol === "cg") {
      draw.push(s("circle", { cx: x0, cy: axisY, r: 7, fill: "#09111a", stroke: col, "stroke-width": 1.5 }),
        s("path", { d: `M${x0},${axisY - 7} A7,7 0 0,1 ${x0 + 7},${axisY} L${x0},${axisY}Z M${x0},${axisY + 7} A7,7 0 0,1 ${x0 - 7},${axisY} L${x0},${axisY}Z`, fill: col }));
    } else if (st.symbol === "cp") {
      draw.push(s("circle", { cx: x0, cy: axisY, r: 7, fill: "#09111a", stroke: col, "stroke-width": 1.5 }), s("circle", { cx: x0, cy: axisY, r: 2.2, fill: col }));
    }
    const right = x0 > W * 0.62;
    draw.push(s("circle", { cx: x0, cy: yy, r: 3, fill: col }),
      s("text", { x: right ? x0 - 10 : Math.max(x1, x0) + 10, y: yy + 4, fill: col, "font-size": 11.5, "text-anchor": right ? "end" : "start", text: st.label }));
  });
  root.append(...draw);
  return root;
}

/* ---------------- C6: margin gauge ---------------- */
export function marginGauge({ kMin, kSupplied, requiredFraction = 0.2, max = 260 }) {
  const W = 460, H = 270, cx = W / 2, cy = 220, r = 170;
  const ang = (k) => Math.PI * (1 - k / max);
  const pt = (k, rr) => [cx + rr * Math.cos(ang(k)), cy - rr * Math.sin(ang(k))];
  const arc = (k0, k1, rr) => { const p0 = pt(k0, rr), p1 = pt(k1, rr); return `M${p0[0]},${p0[1]} A${rr},${rr} 0 0,1 ${p1[0]},${p1[1]}`; };
  const kReq = kMin * (1 + requiredFraction);
  const root = svgRoot(W, H, `Spring rate gauge: supplied ${kSupplied}, minimum ${kMin.toFixed(2)}, twenty percent margin needs ${kReq.toFixed(2)} newton metres per radian`);
  const ticks = [];
  for (let k = 0; k <= max; k += 20) {
    const a = pt(k, r + 6), b = pt(k, r + (k % 100 === 0 ? 16 : 11));
    ticks.push(s("line", { x1: a[0], y1: a[1], x2: b[0], y2: b[1], stroke: C.g500 }));
    if (k % 40 === 0) { const t = pt(k, r + 30); ticks.push(s("text", { x: t[0], y: t[1] + 4, "text-anchor": "middle", fill: C.muted, "font-size": 10.5, text: k })); }
  }
  const needle = pt(kSupplied, r - 18);
  const mk = (k, label, color, rr = r - 40, anchor = "middle") => { const p = pt(k, r), q = pt(k, rr); return s("g", {}, s("line", { x1: p[0], y1: p[1], x2: q[0], y2: q[1], stroke: color, "stroke-width": 2 }), s("text", { x: q[0], y: q[1] + 14, fill: color, "font-size": 10.5, "text-anchor": anchor, text: label })); };
  root.append(
    s("path", { d: arc(0, max, r), fill: "none", stroke: C.g600, "stroke-width": 14 }),
    s("path", { d: arc(0, kMin, r), fill: "none", stroke: "rgba(224,118,80,0.55)", "stroke-width": 14 }),
    s("path", { d: arc(kMin, kReq, r), fill: "none", stroke: "rgba(227,194,122,0.55)", "stroke-width": 14 }),
    s("path", { d: arc(kReq, max, r), fill: "none", stroke: "rgba(76,201,187,0.55)", "stroke-width": 14 }),
    ...ticks,
    mk(kMin, `k_min ${kMin.toFixed(2)}`, C.bad, r - 52, "end"),
    mk(kReq, `1.2·k_min ${kReq.toFixed(2)}`, C.ok, r - 82, "start"),
    s("line", { x1: cx, y1: cy, x2: needle[0], y2: needle[1], stroke: C.ivory, "stroke-width": 3, "stroke-linecap": "round" }),
    s("circle", { cx, cy, r: 8, fill: C.ivory }),
    s("text", { x: cx, y: cy + 36, "text-anchor": "middle", fill: C.ivory, "font-size": 13, text: `k_supplied ${kSupplied} N·m/rad` }),
    s("text", { x: cx, y: cy - 34, "text-anchor": "middle", fill: C.muted, "font-size": 10, text: "N·m/rad" }),
  );
  return root;
}

/* ---------------- D-010: log-scale bars ---------------- */
export function logBars(groups) {
  const W = 640, rowH = 28, gap = 40, L = 200, R = 70;
  const H = groups.reduce((h, g) => h + gap + g.rows.length * rowH, 30);
  const root = svgRoot(W, H, "Values of the same fin quantities in different Project 33 models, log scale");
  root.classList.add("mx-bars");
  let y = 14;
  const out = [];
  for (const g of groups) {
    const lo = g.domain[0], hi = g.domain[1];
    const x = (v) => L + ((Math.log10(v) - Math.log10(lo)) / (Math.log10(hi) - Math.log10(lo))) * (W - L - R);
    out.push(s("text", { x: 0, y: y + 12, fill: C.ivory, "font-size": 12.5, "font-weight": 500, text: `${g.q} (${g.unit}, log scale)` }));
    y += 20;
    for (let e = Math.ceil(Math.log10(lo)); e <= Math.floor(Math.log10(hi)); e++) {
      const v = 10 ** e;
      out.push(s("line", { x1: x(v), x2: x(v), y1: y - 4, y2: y + g.rows.length * rowH, stroke: C.grid }), s("text", { x: x(v), y: y + g.rows.length * rowH + 11, "text-anchor": "middle", fill: C.faint, "font-size": 9.5, text: v }));
    }
    for (const r of g.rows) {
      out.push(
        s("text", { x: 0, y: y + rowH / 2 + 4, fill: C.ivoryDim, "font-size": 11.5, text: r.model.replace(" (design point)", "") }),
        s("rect", { x: L, y: y + 5, width: Math.max(2, x(r.value) - L), height: rowH - 12, fill: r.color, "fill-opacity": 0.75, rx: 2 }),
        s("text", { x: x(r.value) + 8, y: y + rowH / 2 + 4, fill: C.ivory, "font-size": 11.5, text: `${r.value} ${g.unit}` }),
      );
      y += rowH;
    }
    y += gap - 6;
  }
  root.append(...out);
  return root;
}

/* ---------------- D-009: fin planform overlay ---------------- */
export function planformOverlay(current, prior) {
  const H = 360, pad = 30, labelRoom = 190;
  const ends = (f) => [f.x0, f.x0 + f.root, f.x0 + f.sweep, f.x0 + f.sweep + f.tip];
  const x0 = Math.min(...ends(current), ...ends(prior)) - 12;
  const x1 = Math.max(...ends(current), ...ends(prior)) + 12;
  const aftEnd = Math.max(current.x0 + current.root, prior.x0 + prior.root);
  const span = Math.max(current.span, prior.span);
  const sc = (H - 2 * pad - 46) / span;
  const W = Math.round((x1 - x0) * sc + 2 * pad + labelRoom);
  const X = (mm) => pad + (mm - x0) * sc, Y = (mm) => H - pad - 30 - mm * sc;
  const poly = (f) => [[f.x0, 0], [f.x0 + f.sweep, f.span], [f.x0 + f.sweep + f.tip, f.span], [f.x0 + f.root, 0]].map(([x, y]) => [X(x), Y(y)]);
  const root = svgRoot(W, H, "Aft fin planform: current OpenRocket model versus the pre-retune model, to scale");
  root.classList.add("mx-planform");
  root.append(
    s("line", { x1: X(x0), x2: X(x1), y1: Y(0), y2: Y(0), stroke: C.g500, "stroke-width": 2 }),
    s("text", { x: X(x0), y: Y(0) + 16, fill: C.faint, "font-size": 10.5, text: "body surface (fin root line)" }),
    s("line", { x1: X(aftEnd), x2: X(aftEnd), y1: Y(0) + 4, y2: Y(span) - 4, stroke: C.faint, "stroke-dasharray": "2 3" }),
    s("text", { x: X(aftEnd) + 6, y: Y(0) + 28, fill: C.faint, "font-size": 10.5, text: `aft end, ${aftEnd.toFixed(0)} mm (both sets bottom-aligned)` }),
    s("path", { d: path(poly(current), true), fill: "rgba(103,216,207,0.14)", stroke: C.teal3, "stroke-width": 1.8 }),
    s("path", { d: path(poly(prior), true), fill: "rgba(227,194,122,0.2)", stroke: C.amber, "stroke-width": 1.8, "stroke-dasharray": "6 4" }),
    s("text", { x: X(current.x0 + current.sweep), y: Y(current.span) - 10, fill: C.teal3, "font-size": 11.5, text: current.label }),
    s("text", { x: X(prior.x0 + prior.sweep + prior.tip) + 8, y: Y(prior.span) + 4, fill: C.amber, "font-size": 11.5, text: prior.label }),
    s("text", { x: X(x0), y: pad - 10, fill: C.muted, "font-size": 10, text: "to scale · millimetres · stations from the nose tip" }),
  );
  return root;
}
