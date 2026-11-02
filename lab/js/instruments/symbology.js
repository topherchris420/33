// Original, generic display symbology for the conceptual cockpit exhibit. Nothing here is
// taken from any aircraft manual: the conventions used (a horizon with a pitch ladder, speed
// and altitude tapes, a heading scale, a north-up map, a prioritised alert list) are common
// to aviation displays in general. Values come from a synthetic flight-state generator.

export const HUD_GREEN = "#8cf5c8";

/** Synthetic, smoothly varying flight state. Not a flight model; not any aircraft's data. */
export function flightState(t) {
  return {
    pitch: 2.5 + 2.2 * Math.sin(t * 0.21),
    roll: 14 * Math.sin(t * 0.13),
    heading: (84 + 10 * Math.sin(t * 0.05) + 360) % 360,
    speed: 248 + 6 * Math.sin(t * 0.17),
    altitude: 12040 + 140 * Math.sin(t * 0.09),
    vs: 140 * 0.09 * 60 * Math.cos(t * 0.09),
    routeProgress: (t * 0.012) % 1,
  };
}

/** Elements each display shows at each declutter level (1 = minimal … 5 = everything). */
export const DECLUTTER = {
  hud: [["horizon & pitch ladder", 1], ["aircraft reference", 1], ["flight-path marker", 2], ["speed tape", 2], ["altitude tape", 2], ["heading scale", 3], ["bank scale", 4], ["vertical speed", 4], ["mode annunciations", 5], ["ladder labels both sides", 5]],
  map: [["ownship", 1], ["route & waypoints", 1], ["range rings", 2], ["next-waypoint data", 2], ["compass rose", 3], ["wind vector", 4], ["grid", 5], ["all waypoint labels", 5]],
  status: [["warnings", 1], ["cautions", 2], ["advisories", 3], ["status messages", 4], ["message timestamps", 5]],
};

export function elementsAt(display, level) {
  return DECLUTTER[display].filter(([, l]) => l <= level).map(([n]) => n);
}

function bg(ctx, w, h, color = "#03070b") {
  ctx.fillStyle = color; ctx.fillRect(0, 0, w, h);
}

function frameText(ctx, w, h, text) {
  ctx.fillStyle = "rgba(143,162,173,0.85)"; ctx.font = "500 15px 'Plex Mono', monospace"; ctx.textAlign = "left"; ctx.textBaseline = "bottom";
  ctx.fillText(text, 14, h - 10);
}

/** Head-up combiner image. Transparent background for additive blending in 3D. */
export function drawHUD(ctx, w, h, s, level, { flags = {} } = {}) {
  ctx.clearRect(0, 0, w, h);
  ctx.save();
  ctx.strokeStyle = HUD_GREEN; ctx.fillStyle = HUD_GREEN; ctx.lineWidth = 2.4;
  ctx.font = "500 20px 'Plex Mono', monospace";
  const cx = w / 2, cy = h * 0.52, ppd = h / 38; // pixels per degree of pitch
  // Pitch ladder and horizon rotate with roll.
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate((-s.roll * Math.PI) / 180);
  ctx.beginPath(); ctx.rect(-w * 0.32, -h * 0.36, w * 0.64, h * 0.66); ctx.clip();
  const y0 = s.pitch * ppd;
  if (!flags.attitudeLost) {
    ctx.beginPath(); ctx.moveTo(-w * 0.45, y0); ctx.lineTo(-w * 0.07, y0); ctx.moveTo(w * 0.07, y0); ctx.lineTo(w * 0.45, y0); ctx.stroke();
    for (let p = -20; p <= 20; p += 5) {
      if (p === 0) continue;
      const y = y0 - p * ppd, half = w * 0.11;
      ctx.setLineDash(p < 0 ? [10, 8] : []);
      ctx.beginPath(); ctx.moveTo(-half, y); ctx.lineTo(-w * 0.04, y); ctx.moveTo(w * 0.04, y); ctx.lineTo(half, y); ctx.stroke();
      ctx.setLineDash([]);
      ctx.textAlign = "left"; ctx.textBaseline = "middle"; ctx.fillText(String(Math.abs(p)), half + 8, y);
      if (level >= 5) { ctx.textAlign = "right"; ctx.fillText(String(Math.abs(p)), -half - 8, y); }
    }
  }
  ctx.restore();
  if (flags.attitudeLost) {
    ctx.fillStyle = "#ff7a5c"; ctx.font = "600 30px 'Plex Mono', monospace"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText("ATT", cx, cy - 50); ctx.fillStyle = HUD_GREEN; ctx.font = "500 20px 'Plex Mono', monospace";
  }
  // Fixed aircraft reference.
  ctx.beginPath(); ctx.moveTo(cx - 48, cy); ctx.lineTo(cx - 18, cy); ctx.lineTo(cx - 9, cy + 14); ctx.lineTo(cx, cy); ctx.lineTo(cx + 9, cy + 14); ctx.lineTo(cx + 18, cy); ctx.lineTo(cx + 48, cy); ctx.stroke();
  if (level >= 2 && !flags.attitudeLost) {
    const fy = cy + (s.pitch - 1.4) * ppd * 0.3 + 18, fx = cx + Math.sin(s.roll / 30) * 10;
    ctx.beginPath(); ctx.arc(fx, fy, 11, 0, Math.PI * 2); ctx.moveTo(fx - 11, fy); ctx.lineTo(fx - 30, fy); ctx.moveTo(fx + 11, fy); ctx.lineTo(fx + 30, fy); ctx.moveTo(fx, fy - 11); ctx.lineTo(fx, fy - 24); ctx.stroke();
  }
  if (level >= 2) {
    tape(ctx, 34, cy, s.speed, 10, "left", flags.speed);
    tape(ctx, w - 34, cy, s.altitude, 100, "right", flags.altitude);
  }
  if (level >= 3) headingScale(ctx, cx, 46, w * 0.5, s.heading);
  if (level >= 4 && !flags.attitudeLost) {
    ctx.save(); ctx.translate(cx, cy);
    for (const a of [-45, -30, -20, -10, 0, 10, 20, 30, 45]) {
      const r = h * 0.4, ang = ((a - 90) * Math.PI) / 180;
      ctx.beginPath(); ctx.moveTo(Math.cos(ang) * r, Math.sin(ang) * r); ctx.lineTo(Math.cos(ang) * (r + (a % 30 === 0 ? 16 : 9)), Math.sin(ang) * (r + (a % 30 === 0 ? 16 : 9))); ctx.stroke();
    }
    const ang = ((-s.roll - 90) * Math.PI) / 180, r = h * 0.4 - 4;
    ctx.beginPath(); ctx.moveTo(Math.cos(ang) * r, Math.sin(ang) * r); ctx.lineTo(Math.cos(ang - 0.04) * (r - 16), Math.sin(ang - 0.04) * (r - 16)); ctx.lineTo(Math.cos(ang + 0.04) * (r - 16), Math.sin(ang + 0.04) * (r - 16)); ctx.closePath(); ctx.fill();
    ctx.restore();
    ctx.textAlign = "right"; ctx.textBaseline = "top"; ctx.fillText(`${s.vs >= 0 ? "+" : ""}${Math.round(s.vs / 10) * 10} VS`, w - 30, cy + 120);
  }
  if (level >= 5) {
    ctx.textAlign = "left"; ctx.textBaseline = "top"; ctx.fillText("NAV  ALT HOLD", 30, h - 70); ctx.fillText("1.0 G", 30, h - 44);
  }
  ctx.restore();
}

function tape(ctx, x, cy, value, step, side, flag) {
  const boxW = 104, boxH = 36, dir = side === "left" ? 1 : -1;
  const bx = side === "left" ? x : x - boxW;
  ctx.save();
  ctx.lineWidth = 2;
  const stale = flag === "stale", bad = flag === "inconsistent", lost = flag === "unavailable", missing = flag === "missing";
  ctx.strokeStyle = bad || lost ? "#ff7a5c" : stale ? "#ffd27a" : HUD_GREEN;
  ctx.fillStyle = ctx.strokeStyle;
  if (!lost) {
    for (let k = -3; k <= 3; k++) {
      const v = Math.round(value / step) * step + k * step;
      const y = cy - (v - value) * (44 / step);
      const tx = side === "left" ? bx + boxW + 4 : bx - 4;
      ctx.beginPath(); ctx.moveTo(tx, y); ctx.lineTo(tx + dir * 12, y); ctx.stroke();
      if (Math.abs(y - cy) > 26) { ctx.textAlign = side === "left" ? "right" : "left"; ctx.textBaseline = "middle"; ctx.globalAlpha = 0.75; ctx.fillText(String(v), side === "left" ? bx + boxW - 6 : bx + 8, y); ctx.globalAlpha = 1; }
    }
  }
  ctx.strokeRect(bx, cy - boxH / 2, boxW, boxH);
  ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.font = "600 22px 'Plex Mono', monospace";
  const txt = lost ? (side === "left" ? "SPD" : "ALT") : missing ? "– – –" : String(Math.round(value));
  ctx.fillText(txt, bx + boxW / 2, cy + 1);
  if (stale || bad || lost) { ctx.font = "600 15px 'Plex Mono', monospace"; ctx.fillText(stale ? "AGED" : bad ? "DISAGREE" : "FAIL", bx + boxW / 2, cy + 34); }
  ctx.restore();
}

function headingScale(ctx, cx, y, width, heading) {
  ctx.save();
  ctx.beginPath(); ctx.rect(cx - width / 2, y - 30, width, 60); ctx.clip();
  for (let d = -40; d <= 40; d += 5) {
    const hd = Math.round(heading / 5) * 5 + d;
    const x = cx + (hd - heading) * (width / 60);
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, y + (hd % 10 === 0 ? 14 : 8)); ctx.stroke();
    if (hd % 10 === 0) { ctx.textAlign = "center"; ctx.textBaseline = "bottom"; ctx.fillText(String(((hd % 360) + 360) % 360 / 10 | 0).padStart(2, "0"), x, y - 4); }
  }
  ctx.restore();
  ctx.beginPath(); ctx.moveTo(cx, y + 18); ctx.lineTo(cx - 7, y + 30); ctx.lineTo(cx + 7, y + 30); ctx.closePath(); ctx.fill();
}

export const WAYPOINTS = [
  { id: "A", x: -0.55, y: 0.55 }, { id: "B", x: -0.15, y: 0.1 }, { id: "C", x: 0.35, y: -0.05 }, { id: "D", x: 0.6, y: -0.55 }, { id: "E", x: 0.05, y: -0.8 },
];

/** North-up moving map with synthetic waypoints. */
export function drawMap(ctx, w, h, s, level, { navFlag = null } = {}) {
  bg(ctx, w, h, "#041018");
  const cx = w / 2, cy = h / 2, R = w * 0.42;
  const P = (p) => [cx + p.x * R, cy - p.y * R];
  // ownship position along the route
  const segs = WAYPOINTS.length - 1, u = s.routeProgress * segs, i = Math.min(Math.floor(u), segs - 1), f = u - i;
  const a = WAYPOINTS[i], b = WAYPOINTS[i + 1];
  const own = { x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f };
  ctx.save();
  ctx.translate(-(own.x * R) * 0.6, (own.y * R) * 0.6);
  if (level >= 5) {
    ctx.strokeStyle = "rgba(103,216,207,0.07)"; ctx.lineWidth = 1;
    for (let g = -w; g <= w * 2; g += 48) { ctx.beginPath(); ctx.moveTo(g, -h); ctx.lineTo(g, h * 2); ctx.stroke(); ctx.beginPath(); ctx.moveTo(-w, g); ctx.lineTo(w * 2, g); ctx.stroke(); }
  }
  ctx.strokeStyle = navFlag === "unavailable" ? "rgba(255,122,92,0.35)" : "#d78cf0"; ctx.lineWidth = 3;
  ctx.beginPath(); WAYPOINTS.forEach((p, k) => { const [x, y] = P(p); k ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }); ctx.stroke();
  ctx.font = "500 17px 'Plex Mono', monospace";
  WAYPOINTS.forEach((p, k) => {
    const [x, y] = P(p);
    ctx.fillStyle = "#03070b"; ctx.strokeStyle = "#f1e9d6"; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(x, y - 9); ctx.lineTo(x + 9, y); ctx.lineTo(x, y + 9); ctx.lineTo(x - 9, y); ctx.closePath(); ctx.fill(); ctx.stroke();
    if (level >= 5 || k === i + 1) { ctx.fillStyle = "#f1e9d6"; ctx.textAlign = "left"; ctx.textBaseline = "middle"; ctx.fillText(`WPT ${p.id}`, x + 14, y); }
  });
  ctx.restore();
  // ownship at the centre
  const ox = cx, oy = cy;
  if (level >= 2) {
    ctx.strokeStyle = "rgba(103,216,207,0.35)"; ctx.lineWidth = 1.5; ctx.setLineDash([6, 6]);
    for (const r of [R * 0.5, R]) { ctx.beginPath(); ctx.arc(ox, oy, r, 0, Math.PI * 2); ctx.stroke(); }
    ctx.setLineDash([]);
    ctx.fillStyle = "rgba(103,216,207,0.8)"; ctx.font = "500 14px 'Plex Mono', monospace"; ctx.textAlign = "left";
    ctx.fillText("10", ox + R * 0.5 + 4, oy - 4); ctx.fillText("20 NM", ox + R + 4, oy - 4);
  }
  if (level >= 3) {
    ctx.strokeStyle = "rgba(241,233,214,0.5)"; ctx.lineWidth = 1.5;
    for (let d = 0; d < 360; d += 10) {
      const ang = ((d - 90) * Math.PI) / 180, r1 = R * 1.08, r2 = r1 + (d % 30 === 0 ? 14 : 7);
      ctx.beginPath(); ctx.moveTo(ox + Math.cos(ang) * r1, oy + Math.sin(ang) * r1); ctx.lineTo(ox + Math.cos(ang) * r2, oy + Math.sin(ang) * r2); ctx.stroke();
    }
    ctx.fillStyle = "#f1e9d6"; ctx.textAlign = "center"; ctx.textBaseline = "bottom"; ctx.font = "600 16px 'Plex Mono', monospace"; ctx.fillText("N", ox, oy - R * 1.08 - 16);
  }
  if (level >= 4) {
    ctx.save(); ctx.translate(w - 60, 70); ctx.rotate((235 * Math.PI) / 180);
    ctx.strokeStyle = "#8fd3ff"; ctx.fillStyle = "#8fd3ff"; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(0, -24); ctx.lineTo(0, 24); ctx.stroke(); ctx.beginPath(); ctx.moveTo(0, 24); ctx.lineTo(-8, 10); ctx.lineTo(8, 10); ctx.fill();
    ctx.restore();
    ctx.fillStyle = "#8fd3ff"; ctx.font = "500 14px 'Plex Mono', monospace"; ctx.textAlign = "center"; ctx.fillText("WIND", w - 60, 120);
  }
  const heading = Math.atan2(b.x - a.x, b.y - a.y);
  ctx.save(); ctx.translate(ox, oy); ctx.rotate(heading);
  ctx.fillStyle = navFlag === "unavailable" ? "#ff7a5c" : navFlag === "stale" ? "#ffd27a" : "#f1e9d6";
  ctx.beginPath(); ctx.moveTo(0, -16); ctx.lineTo(11, 12); ctx.lineTo(0, 6); ctx.lineTo(-11, 12); ctx.closePath(); ctx.fill();
  ctx.restore();
  if (level >= 2) {
    ctx.fillStyle = "#f1e9d6"; ctx.font = "500 17px 'Plex Mono', monospace"; ctx.textAlign = "left"; ctx.textBaseline = "top";
    ctx.fillText(`NEXT WPT ${b.id}`, 16, 16);
    ctx.fillStyle = "rgba(241,233,214,0.7)"; ctx.fillText(`${(Math.hypot(b.x - own.x, b.y - own.y) * 20).toFixed(1)} NM`, 16, 40);
  }
  if (navFlag && navFlag !== "nominal") {
    ctx.fillStyle = navFlag === "stale" ? "#ffd27a" : "#ff7a5c"; ctx.font = "600 20px 'Plex Mono', monospace"; ctx.textAlign = "right"; ctx.textBaseline = "top";
    ctx.fillText({ missing: "NAV DATA GAP", stale: "NAV POS AGED", inconsistent: "NAV DISAGREE", unavailable: "NAV FAIL" }[navFlag], w - 16, 16);
  }
  frameText(ctx, w, h, "SYNTHETIC MAP · NORTH UP");
}

/** Prioritised alert / status list. */
export function drawStatus(ctx, w, h, messages, level) {
  bg(ctx, w, h);
  const order = { warning: 0, caution: 1, advisory: 2, status: 3 };
  const shownKinds = ["warning", "caution", "advisory", "status"].slice(0, Math.min(4, Math.max(1, level)));
  const shown = messages.filter((m) => shownKinds.includes(m.kind)).sort((a, b) => order[a.kind] - order[b.kind]);
  const colors = { warning: "#ff6a4d", caution: "#ffcc5c", advisory: "#67d8cf", status: "#c9d4da" };
  ctx.font = "600 17px 'Plex Mono', monospace"; ctx.textBaseline = "middle";
  ctx.fillStyle = "rgba(143,162,173,0.85)"; ctx.textAlign = "left"; ctx.fillText("ALERTS & STATUS", 16, 26);
  ctx.strokeStyle = "rgba(143,162,173,0.4)"; ctx.beginPath(); ctx.moveTo(16, 44); ctx.lineTo(w - 16, 44); ctx.stroke();
  const top = shown.find((m) => m.kind === "warning" || m.kind === "caution");
  if (top) {
    ctx.fillStyle = colors[top.kind]; ctx.fillRect(w - 130, 12, 114, 28);
    ctx.fillStyle = "#03070b"; ctx.textAlign = "center"; ctx.fillText(top.kind === "warning" ? "WARNING" : "CAUTION", w - 73, 27);
  }
  shown.slice(0, 9).forEach((m, i) => {
    const y = 70 + i * 40;
    ctx.fillStyle = colors[m.kind];
    if (m.kind === "warning") { ctx.fillRect(16, y - 15, w - 32, 30); ctx.fillStyle = "#03070b"; }
    ctx.textAlign = "left"; ctx.fillText(m.text, 28, y);
    if (level >= 5) { ctx.textAlign = "right"; ctx.globalAlpha = 0.7; ctx.fillText(m.age || "00:12", w - 28, y); ctx.globalAlpha = 1; }
  });
  if (!shown.length) { ctx.fillStyle = "rgba(201,212,218,0.6)"; ctx.textAlign = "left"; ctx.fillText("NO ACTIVE ALERTS", 28, 70); }
  const hidden = messages.length - shown.length;
  if (hidden > 0) { ctx.fillStyle = "rgba(143,162,173,0.85)"; ctx.textAlign = "left"; ctx.font = "500 15px 'Plex Mono', monospace"; ctx.fillText(`+${hidden} lower-priority message${hidden > 1 ? "s" : ""} suppressed by declutter`, 16, h - 44); }
  frameText(ctx, w, h, "SYNTHETIC MESSAGES · GENERIC PRIORITY ORDER");
}

/** Small generic primary-flight-display preview for the information-architecture panel. */
export function drawPreview(ctx, w, h, s, sources) {
  bg(ctx, w, h, "#04090f");
  const ins = sources.inertial, air = sources.airdata, gnss = sources.gnss;
  // attitude: sky/ground
  const cx = w / 2, cy = h / 2, ppd = h / 40;
  ctx.save();
  ctx.beginPath(); ctx.rect(w * 0.22, h * 0.12, w * 0.56, h * 0.76); ctx.clip();
  if (ins.state === "unavailable") {
    ctx.fillStyle = "#0a1016"; ctx.fillRect(0, 0, w, h);
  } else {
    ctx.translate(cx, cy); ctx.rotate((-s.roll * Math.PI) / 180);
    const y0 = s.pitch * ppd;
    ctx.fillStyle = ins.state === "stale" ? "#3b4a57" : "#1f5a86"; ctx.fillRect(-w, -h * 2 + y0, w * 2, h * 2);
    ctx.fillStyle = ins.state === "stale" ? "#4a4236" : "#6b4a2a"; ctx.fillRect(-w, y0, w * 2, h * 2);
    ctx.strokeStyle = "#fff"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(-w, y0); ctx.lineTo(w, y0); ctx.stroke();
    ctx.lineWidth = 1.4;
    for (const p of [-10, -5, 5, 10]) { ctx.beginPath(); ctx.moveTo(-26, y0 - p * ppd); ctx.lineTo(26, y0 - p * ppd); ctx.stroke(); }
  }
  ctx.restore();
  ctx.strokeStyle = "#ffcc5c"; ctx.lineWidth = 4;
  ctx.beginPath(); ctx.moveTo(cx - 44, cy); ctx.lineTo(cx - 14, cy); ctx.moveTo(cx + 14, cy); ctx.lineTo(cx + 44, cy); ctx.stroke();
  ctx.font = "600 15px 'Plex Mono', monospace"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
  if (ins.state === "unavailable") { ctx.fillStyle = "#ff6a4d"; ctx.fillText("ATT FAIL", cx, cy - 40); }
  if (ins.state === "stale") { ctx.fillStyle = "#ffcc5c"; ctx.fillText(`ATT AGED ${ins.age.toFixed(1)} s`, cx, cy - 40); }
  if (ins.state === "missing") { ctx.fillStyle = "#ffcc5c"; ctx.fillText("ATT — sample gap", cx, cy - 40); }
  if (ins.state === "inconsistent") { ctx.fillStyle = "#ffcc5c"; ctx.fillText("ATT COMPARE", cx, cy - 40); }
  // speed / altitude boxes
  box(ctx, 6, cy, w * 0.19, Math.round(s.speed), "SPD", air, true);
  box(ctx, w - w * 0.19 - 6, cy, w * 0.19, Math.round(s.altitude), "ALT", air, false);
  // nav line
  ctx.textAlign = "left"; ctx.font = "500 13px 'Plex Mono', monospace";
  const navText = { nominal: "POS  ± 8 m  · OK", missing: "POS  – – –  (no update)", stale: `POS  AGED ${gnss.age.toFixed(1)} s`, inconsistent: "POS  DISAGREE 0.9 NM", unavailable: "POS  FAIL" }[gnss.state];
  ctx.fillStyle = gnss.state === "nominal" ? "#c9d4da" : gnss.state === "unavailable" ? "#ff6a4d" : "#ffcc5c";
  ctx.fillText(navText, 10, h - 14);
  ctx.fillStyle = "rgba(143,162,173,0.7)"; ctx.textAlign = "right"; ctx.fillText("SYNTHETIC", w - 10, h - 14);
}

function box(ctx, x, cy, bw, value, label, src, left) {
  const st = src.state;
  ctx.strokeStyle = st === "nominal" ? "#c9d4da" : st === "unavailable" || st === "inconsistent" ? "#ff6a4d" : "#ffcc5c";
  ctx.lineWidth = 2; ctx.strokeRect(x, cy - 20, bw, 40);
  ctx.fillStyle = ctx.strokeStyle; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.font = "600 17px 'Plex Mono', monospace";
  const text = st === "unavailable" ? label : st === "missing" ? "– – –" : String(value);
  ctx.fillText(text, x + bw / 2, cy + 1);
  ctx.font = "600 11px 'Plex Mono', monospace";
  const sub = { stale: `AGED ${src.age.toFixed(1)}s`, inconsistent: left ? "SPD DISAGREE" : `${value + 260} / ${value}`, unavailable: "FAIL", missing: "GAP" }[st];
  if (sub) ctx.fillText(sub, x + bw / 2, cy + 32);
}
