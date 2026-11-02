/* V3D-TO-33-1 claymation engine — the stage: binder, pages, camera, turns. */
(function () {
  "use strict";
  var P = window.P33T, C = P.C, clamp = P.clamp, lerp = P.lerp, F = P.F;
  var CT = function () { return window.P33T_CONTENT; };

  /* World: the open binder. Right page R, left page L (back of the previous
   * page), rings between them. 1 world unit = 1 px at zoom 1. */
  var R = (P.R = { x: 0, y: 0, w: 1120, h: 1450 });
  var LP = (P.LP = { x: -1180, y: 0, w: 1120, h: 1450 });
  var RINGS = (P.RINGS = [190, 725, 1260]);
  P.CAM_A = { x: 220, y: 490, z: 1 };     // page right, bench left
  P.CAM_PAGE = { x: 560, y: 600, z: 0.92 }; // whole page centred

  /* Scene context helpers */
  var S = (P.S = {});
  P.ev = function (name) {
    var t = S.cut.events[name];
    if (t === undefined) { if (!P._warned) { P._warned = {}; } if (!P._warned[name]) { P._warned[name] = 1; console.warn("missing event", name); } return 1e9; }
    return t;
  };
  P.since = function (name) { return F.t - P.ev(name); };
  P.prog = function (name, dur, ease, delay) { var a = P.ev(name) + (delay || 0); return P.seg(F.t, a, a + dur, ease); };
  P.after = function (name, delay) { return F.t >= P.ev(name) + (delay || 0); };

  P.camera = function (ctx, cam) {
    ctx.translate(S.W / 2, S.H / 2); ctx.scale(cam.z, cam.z); ctx.translate(-cam.x, -cam.y);
  };
  P.camLerp = function (a, b, k) { return { x: lerp(a.x, b.x, k), y: lerp(a.y, b.y, k), z: lerp(a.z, b.z, k) }; };
  P.screenToWorld = function (cam, sx, sy) { return [(sx - S.W / 2) / cam.z + cam.x, (sy - S.H / 2) / cam.z + cam.y]; };

  P.drawMat = function (ctx) {
    ctx.fillStyle = C.mat; ctx.fillRect(-4000, -3000, 9000, 7000);
    var m = P.matTexture(); ctx.drawImage(m, -2100, -650);
  };

  /* Binder boards and the left page. Props are drawn by the scene on top. */
  P.drawBinder = function (ctx, o) {
    o = o || {};
    var tint = o.board || C.teal;
    P.board(ctx, LP.x - 26, LP.y - 30, LP.w + 40, LP.h + 60, tint);
    P.board(ctx, R.x - 14, R.y - 30, R.w + 44, R.h + 60, tint);
    // spine strip between boards
    ctx.fillStyle = "rgba(4,40,44,0.9)"; ctx.fillRect(-58, -30, 46, R.h + 60);
    if (o.leftPage !== false) {
      P.sheet(ctx, LP.x, LP.y, LP.w, LP.h, { holes: RINGS, holesRight: true, key: "L" });
      // show-through of the previous page: faint mirrored lines of type
      ctx.save(); ctx.fillStyle = "rgba(40,40,30,0.045)";
      for (var i = 0; i < 22; i++) { var len = 260 + ((i * 397) % 560); if (i % 7 === 3) continue; ctx.fillRect(LP.x + LP.w - 120 - len, LP.y + 160 + i * 36, len, 11); }
      ctx.restore();
      P.type(ctx, P33PUB(), LP.x + 60, LP.y + 52, 19, { alpha: 0.6 });
      P.type(ctx, "(Blank)", LP.x + LP.w / 2 - 42, LP.y + LP.h - 42, 19, { alpha: 0.7 });
      if (o.leftPageNo) P.type(ctx, o.leftPageNo, LP.x + LP.w / 2 - o.leftPageNo.length * 5.7 - 52, LP.y + LP.h - 42, 19, { alpha: 0.7 });
    }
  };
  function P33PUB() { return CT().pub; }
  P.drawRings = function (ctx, open) {
    RINGS.forEach(function (y) { P.ring(ctx, -32, y, open); });
  };

  /* ---------- the manual page ---------- */
  var layoutCache = {};
  P.pageLayout = function (id, size, measure) {
    var key = id + size + "/" + measure;
    if (!layoutCache[key]) layoutCache[key] = P.layout(CT().pages[id].blocks || [], measure);
    return layoutCache[key];
  };
  /* st: {size, measure, ticks:{id:prog}, mark:{id:alpha}, x, y (page origin), w, h, top} */
  P.drawPage = function (ctx, id, st) {
    st = st || {};
    var pg = CT().pages[id], x = st.x === undefined ? R.x : st.x, y = st.y === undefined ? R.y : st.y, w = st.w || R.w, h = st.h || R.h;
    var size = st.size || 23, cw = size * 0.6, measure = st.measure || Math.floor(950 / cw), lh = size * 1.5;
    if (!st.noSheet) P.sheet(ctx, x, y, w, h, { holes: st.holes === false ? [] : RINGS.map(function (r) { return r - (y - R.y); }), key: "R" + id, tint: st.tint });
    var x0 = x + (st.left || 120), top = y + (st.top || 150);
    // page furniture
    if (!st.noFurniture) {
      P.type(ctx, P33PUB(), x + 80, y + 54, 19, { alpha: 0.85 });
      if (pg.section) P.type(ctx, pg.section, x + w - 70 - pg.section.length * 11.4, y + 54, 19, { alpha: 0.85 });
      ctx.fillStyle = "rgba(28,32,28,0.55)"; ctx.fillRect(x + 80, y + 68, w - 150, 2);
      if (pg.pageNo) P.type(ctx, pg.pageNo, x + w / 2 - pg.pageNo.length * 6, y + h - 46, 21);
    }
    var L = P.pageLayout(id, size, measure), info = { rows: {}, segs: {}, x0: x0, top: top, lh: lh, cw: cw, measure: measure };
    L.rows.forEach(function (row, i) {
      var ry = top + row.y * lh;
      info.rows[row.block] = info.rows[row.block] || { y0: ry, y1: ry + lh };
      info.rows[row.block].y1 = ry + lh;
      var a = st.dim && st.dim[row.block] !== undefined ? st.dim[row.block] : 1;
      var seed = P.hashStr(id) + i * 977;
      if (row.box) {
        var bh = 0, k;
        for (k = i; k < i + row.box.rows; k++) bh += (L.rows[k].kind === "boxpad" ? 0.55 : 1) * lh;
        var bx = x0 - 6, bw = measure * cw + 12, by = ry - lh * 0.15;
        ctx.save(); ctx.globalAlpha = a;
        if (row.box.type === "note") {
          ctx.fillStyle = C.ink; ctx.fillRect(bx, by, bw, 2.5); ctx.fillRect(bx, by + bh - 4, bw, 2.5);
        } else {
          var col = row.box.type === "warning" ? C.red : C.mustard;
          ctx.fillStyle = row.box.type === "warning" ? "rgba(178,58,46,0.06)" : "rgba(199,154,42,0.08)"; ctx.fillRect(bx, by, bw, bh - 2);
          ctx.strokeStyle = col; ctx.lineWidth = row.box.type === "warning" ? 5 : 4; ctx.strokeRect(bx, by, bw, bh - 2);
          if (row.box.type === "warning") { ctx.lineWidth = 1.5; ctx.strokeRect(bx + 7, by + 7, bw - 14, bh - 16); }
        }
        ctx.restore();
      }
      if (row.kind === "h") { P.cond(ctx, row.text, x0, ry + size * 1.05, size * 1.55, { color: C.ink }); return; }
      if (row.kind === "h2") { P.cond(ctx, row.text, x0, ry + size * 0.95, size * 1.12, { color: C.ink, medium: true }); return; }
      if (row.kind === "boxlabel") {
        var col2 = row.block && /^w/.test(row.block) ? C.red : null;
        var kind = row.text;
        P.font(ctx, P.FONT.monoB, size * 1.02); ctx.textAlign = "center";
        ctx.fillStyle = kind === "WARNING" ? C.red : kind === "CAUTION" ? "#8E6A12" : C.ink; ctx.globalAlpha = a;
        ctx.fillText(kind, x0 + measure * cw / 2, ry + size * 0.9); ctx.textAlign = "left"; ctx.globalAlpha = 1; return;
      }
      if (row.kind === "th" || row.kind === "caption") {
        row.segs.forEach(function (sg) { P.type(ctx, sg.text, x0 + sg.col * cw, ry + size, row.kind === "caption" ? size * 0.82 : size, { bold: row.kind === "th", seed: seed, alpha: a }); });
        if (row.kind === "th") { ctx.fillStyle = "rgba(28,32,28,0.7)"; ctx.fillRect(x0, ry + lh * 0.92, row.rule * cw, 2); }
        return;
      }
      (row.segs || []).forEach(function (sg, si) {
        var sx = x0 + sg.col * cw, isPage = sg.style === "page", isCmd = sg.style === "cmd";
        if (isPage) info.segs[row.block] = { x: sx, y: ry, w: sg.text.length * cw, h: lh };
        var bold = isPage && /NOT|OUTSIDE|CONTRA|UNRES/.test(sg.text);
        var color = isCmd ? C.tealDeep : row.kind === "small" ? "#4B5049" : C.ink;
        if (sg.item && st.itemBold !== false) {
          P.type(ctx, sg.text.slice(0, sg.item), sx, ry + size, size, { bold: true, color: color, seed: seed + si, alpha: a });
          P.type(ctx, sg.text.slice(sg.item), sx + sg.item * cw, ry + size, size, { color: color, seed: seed + si + 9, alpha: a });
        } else P.type(ctx, sg.text, sx, ry + size, row.kind === "small" ? size * 0.82 : size, { bold: bold || (isCmd && st.cmdBold), color: color, seed: seed + si, alpha: a });
      });
    });
    // ticks in the left margin, marks (pencil underline), change bars in the right margin
    Object.keys(st.ticks || {}).forEach(function (bid) {
      var r = info.rows[bid]; if (!r) return;
      P.tick(ctx, x0 - 50, r.y0 + size * 1.0, st.ticks[bid], 1.0);
    });
    (st.bars || []).forEach(function (bid) {
      var r = info.rows[bid]; if (!r) return;
      P.part("chbar", 10, 80, function (rr) { return [{ path: P.rrect(-4, -40, 8, 80, 4, rr, 0.5), color: C.teal }]; }).draw(ctx, x + w - 52, (r.y0 + r.y1) / 2, { sy: (r.y1 - r.y0 + 8) / 80, key: bid });
    });
    return info;
  };

  /* Tab divider card: coloured card stock with a protruding tab and a label. */
  P.drawDivider = function (ctx, id, o) {
    o = o || {};
    var d = CT().pages[id], tint = { teal: "#5E9A97", mustard: "#D2AE52", sage: "#AEB5A6" }[d.tabColor] || "#5E9A97";
    var x = R.x, y = R.y, w = R.w, h = R.h, tabY = 140 + (["I", "II", "III", "V"].indexOf(d.tab) * 200);
    P.part("divider-" + id, w + 90, h, function (r) {
      var p = new Path2D();
      p.addPath(P.rrect(-(w + 90) / 2, -h / 2, w, h, 10, r, 1.2));
      p.addPath(P.rrect(w / 2 - 110, -h / 2 + tabY, 150, 160, 22, r, 1));
      return [{ path: p, color: tint, opts: { tex: 0.55, occ: 0.3, sheen: 0.05 } }];
    }, { res: 0.8 }).draw(ctx, x + (w + 90) / 2, y + h / 2, { jitterAmp: 0.3 });
    // tab legend
    P.cond(ctx, d.tab, x + w + 40, y + tabY + 98, 64, { color: "rgba(16,19,16,0.8)", align: "center" });
    // punched holes
    RINGS.forEach(function (ry) { ctx.fillStyle = "#24302C"; ctx.beginPath(); ctx.arc(x + 34, y + ry, 13, 0, 7); ctx.fill(); });
    // glued label card
    var lx = x + 110, ly = y + 150, lw = w - 220, lh2 = 760;
    P.sheet(ctx, lx, ly, lw, lh2, { key: "lab" + id, shadow: 0.25 });
    P.type(ctx, P33PUB(), lx + 40, ly + 50, 19, { alpha: 0.8 });
    P.cond(ctx, d.section, lx + 40, ly + 150, 44, { color: C.teal, medium: true });
    var tl = P.wrap(d.title, 30);
    tl.forEach(function (l, i) { P.cond(ctx, l, lx + 40, ly + 228 + i * 70, 72, { color: C.ink }); });
    var yy = ly + 260 + tl.length * 70, size = 20, cw = size * 0.6, meas = Math.floor((lw - 80) / cw);
    var L = P.layout(d.blocks, meas);
    L.rows.forEach(function (row) { (row.segs || []).forEach(function (sg) { P.type(ctx, sg.text, lx + 40 + sg.col * cw, yy + row.y * size * 1.55, size, { bold: sg.style === "page" }); }); });
    yy += L.height * size * 1.55 + 40;
    P.type(ctx, "INTRODUCTION", lx + 40, yy, 20, { bold: true });
    P.wrap(d.intro, meas).forEach(function (l, i) { P.type(ctx, l, lx + 40, yy + 36 + i * 31, 20); });
  };

  /* Page turn over the rings. p: 0..1. drawCur draws the outgoing right page. */
  P.turn = function (ctx, p, drawCur) {
    if (p <= 0) { drawCur(); return; }
    if (p >= 1) return;
    var c = Math.cos(Math.PI * p), x = R.x;
    if (p < 0.5) {
      // shadow the lifted flap casts on the page beneath
      var edge = x + R.w * c;
      var g = ctx.createLinearGradient(edge, 0, edge + 160 * Math.sin(Math.PI * p), 0);
      g.addColorStop(0, "rgba(20,10,0," + 0.35 * Math.sin(Math.PI * p) + ")"); g.addColorStop(1, "rgba(20,10,0,0)");
      ctx.fillStyle = g; ctx.fillRect(edge, R.y - 20, 180, R.h + 40);
      ctx.save();
      ctx.beginPath(); ctx.rect(x, R.y - 40, R.w * c, R.h + 80); ctx.clip();
      ctx.translate(x, 0); ctx.scale(c, 1); ctx.translate(-x, 0);
      drawCur();
      ctx.restore();
      ctx.fillStyle = "rgba(255,250,240," + 0.25 * Math.sin(Math.PI * p) + ")"; ctx.fillRect(x, R.y, R.w * c, R.h);
    } else {
      var wb = -R.w * c;
      ctx.save();
      ctx.shadowColor = "rgba(20,10,0,0.3)"; ctx.shadowBlur = 20; ctx.shadowOffsetX = -8;
      ctx.drawImage(P.paperSprite(R.w, R.h, "back"), x - wb, R.y, wb, R.h);
      ctx.restore();
      var g2 = ctx.createLinearGradient(x - wb, 0, x, 0);
      g2.addColorStop(0, "rgba(0,0,0,0)"); g2.addColorStop(1, "rgba(30,20,5," + 0.3 * (1 - p) * 2 + ")");
      ctx.fillStyle = g2; ctx.fillRect(x - wb, R.y, wb, R.h);
    }
  };

  /* Whole-frame render for a cut at time t. */
  P.renderFrame = function (ctx, cut, t, W, H) {
    P.setTime(t);
    var sc = cut.scenes[cut.scenes.length - 1];
    for (var i = 0; i < cut.scenes.length; i++) if (F.t < cut.scenes[i].end) { sc = cut.scenes[i]; break; }
    S.cut = cut; S.scene = sc; S.W = W; S.H = H; S.lt = F.t - sc.start;
    ctx.save();
    var fn = P.scenes[sc.id];
    if (fn) fn(ctx); else { ctx.fillStyle = "#111"; ctx.fillRect(0, 0, W, H); }
    ctx.restore();
    P.post(ctx, W, H);
    return sc;
  };
  P.scenes = {};
})();
