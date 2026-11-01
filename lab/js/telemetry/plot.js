// A small, precise Canvas2D plotter for stacked telemetry lanes sharing one time axis.
// Wheel zooms around the cursor, drag pans, double-click resets; arrow keys and +/− work
// when the canvas has focus. Non-finite samples break the line and get a gap marker —
// a missing value is never drawn as zero.

const C = {
  bg: "#08111a", grid: "rgba(103,216,207,0.07)", gridMajor: "rgba(103,216,207,0.16)", axis: "#4c5f6c",
  text: "#8fa2ad", ink: "#f1e9d6", teal: "#67d8cf", copper: "#e0a274", red: "#e07650", amber: "#e3c27a",
  violet: "#b49ad8", cursor: "rgba(241,233,214,0.55)",
};
export const PLOT_COLORS = C;

function niceStep(span, target = 6) {
  const raw = span / target;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const n = raw / mag;
  return (n < 1.5 ? 1 : n < 3 ? 2 : n < 7 ? 5 : 10) * mag;
}

function fmt(v, step) {
  const d = Math.max(0, -Math.floor(Math.log10(step || 1)) + (step < 1 ? 0 : 0));
  return Number(v).toFixed(Math.min(d, 4));
}

export class LanePlot {
  constructor(canvas, { lanes, xLabel = "time (s)", onCursor, padLeft = 64, padRight = 16 } = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.lanes = lanes;
    this.xLabel = xLabel;
    this.onCursor = onCursor;
    this.pad = { l: padLeft, r: padRight, t: 10, b: 30, gap: 14 };
    this.data = { series: [], bands: [], markers: [], missing: [], bars: [] };
    this.full = [0, 1];
    this.view = [0, 1];
    this.cursorX = null;
    this.playhead = null;
    this.revealUntil = null;
    this.dpr = 1;
    this._bind();
    new ResizeObserver(() => this.render()).observe(canvas);
  }

  setLanes(lanes) { this.lanes = lanes; this.render(); }

  setData(data, { keepView = false } = {}) {
    this.data = { series: [], bands: [], markers: [], missing: [], bars: [], ...data };
    const xs = [];
    for (const s of this.data.series) for (const p of s.points) if (Number.isFinite(p.x)) xs.push(p.x);
    for (const b of this.data.bars) for (const p of b.points) if (Number.isFinite(p.x)) xs.push(p.x);
    const min = data.xRange ? data.xRange[0] : Math.min(...xs), max = data.xRange ? data.xRange[1] : Math.max(...xs);
    const span = (max - min) || 1;
    this.full = [min - span * 0.03, max + span * 0.03];
    if (!keepView) this.view = [...this.full];
    this.render();
  }

  reset() { this.view = [...this.full]; this.render(); }

  zoom(factor, centerX) {
    const [a, b] = this.view;
    const c = centerX ?? (a + b) / 2;
    const minSpan = (this.full[1] - this.full[0]) / 400;
    const span = Math.max((b - a) * factor, minSpan);
    let na = c - ((c - a) / (b - a)) * span;
    let nb = na + span;
    const fs = this.full[1] - this.full[0];
    if (span >= fs) { na = this.full[0]; nb = this.full[1]; }
    this.view = [na, nb];
    this.render();
  }

  pan(fraction) {
    const span = this.view[1] - this.view[0];
    let a = this.view[0] + span * fraction;
    a = Math.max(this.full[0], Math.min(a, this.full[1] - span));
    this.view = [a, a + span];
    this.render();
  }

  zoomTo(x0, x1) { this.view = [x0, x1]; this.render(); }

  _geom() {
    const w = this.canvas.clientWidth, hgt = this.canvas.clientHeight;
    const lanes = this.lanes.filter((l) => !l.hidden);
    const weights = lanes.map((l) => l.weight ?? 1);
    const total = weights.reduce((s, v) => s + v, 0) || 1;
    const usable = hgt - this.pad.t - this.pad.b - this.pad.gap * Math.max(lanes.length - 1, 0);
    let y = this.pad.t;
    const boxes = lanes.map((lane, i) => {
      const h = (usable * weights[i]) / total;
      const box = { lane, x: this.pad.l, y, w: w - this.pad.l - this.pad.r, h };
      y += h + this.pad.gap;
      return box;
    });
    return { w, h: hgt, boxes };
  }

  xToPx(x, g) { return this.pad.l + ((x - this.view[0]) / (this.view[1] - this.view[0])) * (g.w - this.pad.l - this.pad.r); }
  pxToX(px, g) { return this.view[0] + ((px - this.pad.l) / (g.w - this.pad.l - this.pad.r)) * (this.view[1] - this.view[0]); }

  _yRange(lane) {
    if (lane.range) return lane.range;
    const vals = [];
    const inView = (x) => x >= this.view[0] && x <= this.view[1];
    for (const s of this.data.series) if (s.lane === lane.id) for (const p of s.points) if (Number.isFinite(p.y) && inView(p.x)) vals.push(p.y);
    for (const b of this.data.bands) if (b.lane === lane.id) for (const p of b.points) if (inView(p.x)) vals.push(p.lo, p.hi);
    for (const b of this.data.bars) if (b.lane === lane.id) for (const p of b.points) if (Number.isFinite(p.y) && inView(p.x)) vals.push(p.y);
    if (lane.ref !== undefined) vals.push(lane.ref, 0);
    if (!vals.length) return [-1, 1];
    let lo = Math.min(...vals), hi = Math.max(...vals);
    if (lo === hi) { lo -= 1; hi += 1; }
    const m = (hi - lo) * 0.12;
    return [lo - m, hi + m];
  }

  render() {
    const cv = this.canvas, ctx = this.ctx;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = cv.clientWidth, hgt = cv.clientHeight;
    if (!w || !hgt) return;
    if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(hgt * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(hgt * dpr); }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = C.bg; ctx.fillRect(0, 0, w, hgt);
    const g = this._geom();
    const xStep = niceStep(this.view[1] - this.view[0], Math.max(3, Math.floor(w / 110)));
    ctx.font = "10.5px 'Plex Mono', monospace";
    for (const box of g.boxes) this._lane(ctx, g, box, xStep);
    // x axis labels
    ctx.fillStyle = C.text; ctx.textAlign = "center"; ctx.textBaseline = "top";
    const last = g.boxes[g.boxes.length - 1];
    if (last) {
      for (let x = Math.ceil(this.view[0] / xStep) * xStep; x <= this.view[1]; x += xStep) {
        const px = this.xToPx(x, g);
        ctx.fillText(fmt(x, xStep), px, last.y + last.h + 6);
      }
      ctx.textAlign = "right"; ctx.fillStyle = C.text;
      ctx.fillText(this.xLabel, g.w - this.pad.r, last.y + last.h + 18);
    }
    // markers spanning all lanes
    const top = g.boxes[0]?.y ?? 0, bottom = last ? last.y + last.h : hgt;
    for (const m of this.data.markers) {
      if (m.x < this.view[0] || m.x > this.view[1]) continue;
      const px = this.xToPx(m.x, g);
      ctx.save();
      ctx.strokeStyle = m.color || C.copper; ctx.setLineDash([3, 3]); ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(px, top); ctx.lineTo(px, bottom); ctx.stroke();
      ctx.setLineDash([]);
      if (m.tag) {
        ctx.fillStyle = m.color || C.copper;
        ctx.beginPath(); ctx.arc(px, top + 9 + (m.stack || 0) * 18, 8, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = "#060a10"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.font = "600 10px 'Plex Mono', monospace";
        ctx.fillText(m.tag, px, top + 9.5 + (m.stack || 0) * 18);
      }
      ctx.restore();
    }
    // playhead
    if (this.playhead !== null && this.playhead >= this.view[0] && this.playhead <= this.view[1]) {
      const px = this.xToPx(this.playhead, g);
      ctx.strokeStyle = C.teal; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(px, top); ctx.lineTo(px, bottom); ctx.stroke();
    }
    // cursor
    if (this.cursorX !== null) {
      const px = this.xToPx(this.cursorX, g);
      ctx.strokeStyle = C.cursor; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(px, top); ctx.lineTo(px, bottom); ctx.stroke();
    }
  }

  _lane(ctx, g, box, xStep) {
    const { lane } = box;
    const [ylo, yhi] = this._yRange(lane);
    const yToPx = (y) => box.y + box.h - ((y - ylo) / (yhi - ylo)) * box.h;
    // frame + grid
    ctx.fillStyle = "rgba(16,28,40,0.55)"; ctx.fillRect(box.x, box.y, box.w, box.h);
    ctx.strokeStyle = C.grid; ctx.lineWidth = 1;
    for (let x = Math.ceil(this.view[0] / xStep) * xStep; x <= this.view[1]; x += xStep) {
      const px = Math.round(this.xToPx(x, g)) + 0.5;
      ctx.beginPath(); ctx.moveTo(px, box.y); ctx.lineTo(px, box.y + box.h); ctx.stroke();
    }
    const yStep = niceStep(yhi - ylo, Math.max(2, Math.floor(box.h / 34)));
    ctx.fillStyle = C.text; ctx.textAlign = "right"; ctx.textBaseline = "middle";
    for (let y = Math.ceil(ylo / yStep) * yStep; y <= yhi; y += yStep) {
      const py = Math.round(yToPx(y)) + 0.5;
      ctx.strokeStyle = Math.abs(y) < yStep / 1000 ? C.gridMajor : C.grid;
      ctx.beginPath(); ctx.moveTo(box.x, py); ctx.lineTo(box.x + box.w, py); ctx.stroke();
      ctx.fillText(fmt(y, yStep), box.x - 6, py);
    }
    ctx.strokeStyle = C.axis; ctx.strokeRect(box.x + 0.5, box.y + 0.5, box.w - 1, box.h - 1);
    // lane label
    ctx.save();
    ctx.fillStyle = C.ink; ctx.textAlign = "left"; ctx.textBaseline = "top"; ctx.font = "500 10.5px 'Plex Mono', monospace";
    ctx.fillText(`${lane.label}${lane.unit ? ` [${lane.unit}]` : ""}`, box.x + 8, box.y + 6);
    ctx.restore();
    ctx.save();
    ctx.beginPath(); ctx.rect(box.x, box.y, box.w, box.h); ctx.clip();
    const reveal = this.revealUntil;
    const shown = (p) => reveal === null || reveal === undefined || (p.order ?? p.x) <= reveal + 1e-9;
    // reference line
    if (lane.ref !== undefined) {
      const py = yToPx(lane.ref);
      ctx.strokeStyle = C.amber; ctx.setLineDash([5, 4]); ctx.globalAlpha = 0.8;
      ctx.beginPath(); ctx.moveTo(box.x, py); ctx.lineTo(box.x + box.w, py); ctx.stroke();
      ctx.setLineDash([]); ctx.globalAlpha = 1;
      ctx.fillStyle = C.amber; ctx.textAlign = "right"; ctx.textBaseline = "bottom";
      ctx.fillText(lane.refLabel || `nominal ${lane.ref}`, box.x + box.w - 6, py - 2);
    }
    // bands
    for (const band of this.data.bands.filter((b) => b.lane === lane.id)) {
      const pts = band.points.filter(shown);
      if (pts.length < 2) continue;
      ctx.fillStyle = band.color || "rgba(180,154,216,0.16)";
      ctx.beginPath();
      pts.forEach((p, i) => { const px = this.xToPx(p.x, g), py = yToPx(p.hi); i ? ctx.lineTo(px, py) : ctx.moveTo(px, py); });
      for (let i = pts.length - 1; i >= 0; i--) ctx.lineTo(this.xToPx(pts[i].x, g), yToPx(pts[i].lo));
      ctx.closePath(); ctx.fill();
    }
    // bars (sample-interval strip)
    for (const bars of this.data.bars.filter((b) => b.lane === lane.id)) {
      for (const p of bars.points) {
        if (!shown(p)) continue;
        const px = this.xToPx(p.x, g);
        if (p.y === null || !Number.isFinite(p.y)) continue;
        const y0 = yToPx(0), y1 = yToPx(p.y);
        ctx.fillStyle = p.color || C.teal;
        const bw = Math.max(2, Math.min(9, box.w / Math.max(bars.points.length, 1) * 0.6));
        ctx.fillRect(px - bw / 2, Math.min(y0, y1), bw, Math.max(Math.abs(y1 - y0), 1.5));
      }
    }
    // series
    for (const s of this.data.series.filter((s) => s.lane === lane.id && !s.hidden)) {
      ctx.strokeStyle = s.color; ctx.lineWidth = s.width || 1.5; ctx.setLineDash(s.dash || []);
      ctx.globalAlpha = s.alpha ?? 1;
      ctx.beginPath();
      let pen = false;
      for (const p of s.points) {
        if (!shown(p)) { pen = false; continue; }
        if (!Number.isFinite(p.y)) { pen = false; continue; }
        if (p.gapBefore) pen = false;
        const px = this.xToPx(p.x, g), py = yToPx(p.y);
        if (pen) ctx.lineTo(px, py); else ctx.moveTo(px, py);
        pen = true;
      }
      if (s.kind !== "points") ctx.stroke();
      ctx.setLineDash([]);
      if (s.markers !== false) {
        ctx.fillStyle = s.color;
        for (const p of s.points) {
          if (!shown(p) || !Number.isFinite(p.y)) continue;
          const px = this.xToPx(p.x, g), py = yToPx(p.y);
          const r = s.markerSize ?? (s.kind === "points" ? 2.2 : 2.6);
          ctx.beginPath(); ctx.arc(px, py, r, 0, Math.PI * 2); ctx.fill();
        }
      }
      ctx.globalAlpha = 1;
    }
    // missing markers (invalid / dropped samples)
    // Label gap markers only while they are sparse enough to read.
    const laneMissing = this.data.missing.filter((m) => m.lane === lane.id && m.x >= this.view[0] && m.x <= this.view[1]);
    let labelled = laneMissing.length > 6 ? 6 : 0;
    for (const m of this.data.missing.filter((m) => m.lane === lane.id)) {
      if (!shown(m)) continue;
      const px = this.xToPx(m.x, g);
      ctx.fillStyle = m.color || C.red; ctx.strokeStyle = m.color || C.red;
      ctx.globalAlpha = 0.18; ctx.fillRect(px - 3, box.y, 6, box.h); ctx.globalAlpha = 1;
      ctx.beginPath(); ctx.moveTo(px - 4, box.y + box.h - 2); ctx.lineTo(px + 4, box.y + box.h - 2); ctx.lineTo(px, box.y + box.h - 9); ctx.closePath(); ctx.fill();
      if (m.label && box.w > 300 && labelled < 6) { labelled++; ctx.textAlign = "left"; ctx.textBaseline = "bottom"; ctx.fillText(m.label, px + 6, box.y + box.h - 3); }
    }
    ctx.restore();
    box.yToPx = yToPx;
  }

  /** Nearest sample per series at x (for the cursor readout). */
  sampleAt(x) {
    const out = [];
    for (const s of this.data.series) {
      if (s.hidden || s.readout === false) continue;
      let best = null, bd = Infinity;
      for (const p of s.points) { const d = Math.abs(p.x - x); if (d < bd) { bd = d; best = p; } }
      if (best) out.push({ series: s, point: best });
    }
    return out;
  }

  _bind() {
    const cv = this.canvas;
    cv.tabIndex = 0;
    let drag = null;
    const local = (e) => { const r = cv.getBoundingClientRect(); return { px: e.clientX - r.left, py: e.clientY - r.top }; };
    cv.addEventListener("wheel", (e) => {
      e.preventDefault();
      const g = this._geom();
      this.zoom(e.deltaY > 0 ? 1.18 : 1 / 1.18, this.pxToX(local(e).px, g));
    }, { passive: false });
    cv.addEventListener("pointerdown", (e) => { drag = { px: local(e).px, view: [...this.view] }; cv.setPointerCapture(e.pointerId); });
    cv.addEventListener("pointermove", (e) => {
      const g = this._geom();
      const { px } = local(e);
      if (drag) {
        const span = drag.view[1] - drag.view[0];
        const dx = ((px - drag.px) / (g.w - this.pad.l - this.pad.r)) * span;
        let a = drag.view[0] - dx;
        a = Math.max(this.full[0], Math.min(a, this.full[1] - span));
        this.view = [a, a + span];
      }
      this.cursorX = this.pxToX(px, g);
      this.render();
      this.onCursor?.(this.cursorX, this.sampleAt(this.cursorX));
    });
    cv.addEventListener("pointerup", () => { drag = null; });
    cv.addEventListener("pointerleave", () => { this.cursorX = null; this.render(); this.onCursor?.(null, []); });
    cv.addEventListener("dblclick", () => this.reset());
    cv.addEventListener("keydown", (e) => {
      const map = { ArrowLeft: () => this.pan(-0.15), ArrowRight: () => this.pan(0.15), "+": () => this.zoom(1 / 1.3), "=": () => this.zoom(1 / 1.3), "-": () => this.zoom(1.3), "0": () => this.reset() };
      if (map[e.key]) { e.preventDefault(); map[e.key](); }
    });
  }
}

/** A simple spectrum plot (log amplitude) with labelled reference frequencies. */
export function drawSpectrum(canvas, spectra, { refs = [], nyquist } = {}) {
  const ctx = canvas.getContext("2d");
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = canvas.clientWidth, hgt = canvas.clientHeight;
  if (!w || !hgt) return;
  canvas.width = Math.round(w * dpr); canvas.height = Math.round(hgt * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.fillStyle = C.bg; ctx.fillRect(0, 0, w, hgt);
  const pad = { l: 52, r: 12, t: 12, b: 30 };
  const fmax = nyquist ?? Math.max(...spectra[0].data.map((d) => d.hz));
  const amps = spectra.flatMap((s) => s.data.map((d) => d.amplitude)).filter((a) => a > 0);
  const amax = Math.max(...amps) * 1.6, amin = Math.max(amax / 1e4, Math.min(...amps));
  const X = (hz) => pad.l + (hz / fmax) * (w - pad.l - pad.r);
  const Y = (a) => pad.t + (1 - (Math.log10(Math.max(a, amin)) - Math.log10(amin)) / (Math.log10(amax) - Math.log10(amin))) * (hgt - pad.t - pad.b);
  ctx.font = "10.5px 'Plex Mono', monospace";
  ctx.strokeStyle = C.grid;
  for (let e = Math.ceil(Math.log10(amin)); e <= Math.log10(amax); e++) {
    const y = Y(10 ** e);
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(w - pad.r, y); ctx.stroke();
    ctx.fillStyle = C.text; ctx.textAlign = "right"; ctx.textBaseline = "middle"; ctx.fillText(`1e${e}`, pad.l - 6, y);
  }
  const step = niceStep(fmax, 6);
  for (let f = 0; f <= fmax + 1e-9; f += step) {
    const x = X(f);
    ctx.strokeStyle = C.grid; ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, hgt - pad.b); ctx.stroke();
    ctx.fillStyle = C.text; ctx.textAlign = "center"; ctx.textBaseline = "top"; ctx.fillText(fmt(f, step), x, hgt - pad.b + 6);
  }
  ctx.textAlign = "right"; ctx.fillText("frequency (Hz)", w - pad.r, hgt - 12);
  for (const r of refs) {
    const x = X(r.hz);
    ctx.strokeStyle = r.color || C.amber; ctx.setLineDash([4, 3]);
    ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, hgt - pad.b); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = r.color || C.amber; ctx.textAlign = "left"; ctx.textBaseline = "top";
    ctx.fillText(r.label, Math.min(x + 4, w - 120), pad.t + 2 + (r.row || 0) * 13);
  }
  for (const s of spectra) {
    ctx.strokeStyle = s.color; ctx.lineWidth = s.width || 1.4; ctx.globalAlpha = s.alpha ?? 1;
    ctx.beginPath();
    s.data.forEach((d, i) => { const x = X(d.hz), y = Y(d.amplitude); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
    ctx.stroke(); ctx.globalAlpha = 1;
  }
  ctx.strokeStyle = C.axis; ctx.strokeRect(pad.l + 0.5, pad.t + 0.5, w - pad.l - pad.r - 1, hgt - pad.t - pad.b - 1);
}
