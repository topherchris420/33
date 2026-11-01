/* V3D-TO-33-1 — scenes 1–3: cover and scope, contents, Section I. */
(function () {
  "use strict";
  var P = window.P33T, C = P.C, F = P.F, clamp = P.clamp, lerp = P.lerp, E = P.ease;
  var R = P.R, ev = P.ev, prog = P.prog, since = P.since;
  var CT = function () { return window.P33T_CONTENT; };

  /* Lamp switching on, stop-motion style: a stutter across a few drawings. */
  P.lampLevel = function (onName, offName) {
    var on = 0, d;
    if (onName) { d = (F.t - ev(onName)) * 12; on = d < 0 ? 0 : d < 1 ? 0.35 : d < 2 ? 0.9 : d < 3 ? 0.7 : 1; }
    else on = 1;
    if (offName) { d = (F.t - ev(offName)) * 12; if (d >= 0) on = d < 1 ? 0.55 : d < 2 ? 0.25 : 0; }
    return on;
  };

  /* ---------- the bench from the front (opening and closing shots) ---------- */
  P.drawElevation = function (ctx, o) {
    var W = P.S.W, H = P.S.H, on = o.on;
    ctx.drawImage(P.elevationSet(W, H), 0, 0);
    // warm pool from the lamp on the wall and table
    var px = W * 0.47, py = H * 0.72;
    ctx.save();
    ctx.globalCompositeOperation = "screen";
    var g = ctx.createRadialGradient(px, py, 20, px, py, W * 0.55);
    g.addColorStop(0, "rgba(255,214,150," + 0.42 * on + ")"); g.addColorStop(0.5, "rgba(200,140,70," + 0.16 * on + ")"); g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ctx.restore();
    if (o.draw) o.draw(ctx);
    if (!o.noLamp) P.deskLamp(ctx, W * 0.16, H * 0.8, H * 0.3, on);
    ctx.save(); ctx.globalCompositeOperation = "multiply";
    var v = ctx.createRadialGradient(px, py * 0.95, H * 0.3, px, py, W * 0.85);
    v.addColorStop(0, "rgba(255,255,255,1)"); v.addColorStop(1, "rgba(60,50,40,1)");
    ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
    ctx.restore();
    if (on < 1) { ctx.fillStyle = "rgba(5,6,5," + (1 - on) * 0.93 + ")"; ctx.fillRect(0, 0, W, H); }
  };
  /* Rocket standing on a little clay stand. (x, base y) */
  P.standingRocket = function (ctx, x, by, L) {
    P.part("rstand" + L, L * 0.34, L * 0.12, function (r) {
      return [{ path: P.ellipse(0, 0, L * 0.16, L * 0.045, r, 1), color: "#30363A" }];
    }).draw(ctx, x, by, { shadow: false });
    ctx.save(); ctx.filter = "blur(10px)"; ctx.fillStyle = "rgba(10,5,0,0.4)"; ctx.beginPath(); ctx.ellipse(x + 30, by + 6, L * 0.2, L * 0.03, 0, 0, 7); ctx.fill(); ctx.restore();
    P.rocketUp(L).draw(ctx, x, by - L * 0.5 - 4, { shadow: false });
  };
  /* Binder lying flat on the bench, seen from the front: boards and page edges. */
  P.binderSlab = function (ctx, x, by, w) {
    P.part("slab" + w, w, w * 0.17, function (r) {
      var h = w * 0.17;
      return [
        { path: P.rrect(-w / 2, h * 0.15, w, h * 0.32, 8, r, 1.2), color: C.teal, bb: { x: -w / 2, y: h * 0.15, w: w, h: h * 0.32 } },
        { path: P.rrect(-w / 2 + 8, -h * 0.12, w - 16, h * 0.3, 4, r, 0.8), color: C.ivory, bb: { x: -w / 2, y: -h * 0.12, w: w, h: h * 0.3 }, opts: { lit: 0.1 } },
        { path: P.rrect(-w / 2, -h * 0.5, w, h * 0.4, 8, r, 1.2), color: "#0E6A70", bb: { x: -w / 2, y: -h * 0.5, w: w, h: h * 0.4 } },
        { draw: function (c) { c.strokeStyle = "rgba(80,70,50,0.25)"; for (var i = 0; i < 9; i++) { c.beginPath(); c.moveTo(-w / 2 + 12, -h * 0.1 + i * h * 0.033); c.lineTo(w / 2 - 12, -h * 0.1 + i * h * 0.033); c.stroke(); } } },
      ];
    }).draw(ctx, x, by - w * 0.085, { shadow: false });
    ctx.save(); ctx.filter = "blur(9px)"; ctx.fillStyle = "rgba(10,5,0,0.45)"; ctx.fillRect(x - w / 2 + 20, by - 6, w, 16); ctx.restore();
  };

  /* Binder cover, top-down: board, spine, typed label card. */
  P.drawCover = function (ctx, o) {
    o = o || {};
    var cv = CT().pages.cover, x = -40, y = -40, w = 1210, h = 1530;
    P.part("coverboard", w, h, function (r) {
      return [{ path: P.rrect(-w / 2, -h / 2, w, h, 22, r, 2.2), color: C.teal, opts: { tex: 0.65, occ: 0.38, sheen: 0.06 } },
        { path: P.rrect(-w / 2, -h / 2, 70, h, [22, 0, 0, 22], r, 1.5), color: "#084A4F", bb: { x: -w / 2, y: -h / 2, w: 70, h: h }, opts: { tex: 0.6 } }];
    }, { res: 0.75, pad: 30 }).draw(ctx, x + w / 2, y + h / 2, { jitterAmp: 0.3 });
    ctx.save(); ctx.translate(x + 35, y + h / 2); ctx.rotate(-Math.PI / 2);
    P.cond(ctx, "VERS3DYNAMICS · V3D-TO-33-1 · PROJECT 33", 0, 12, 30, { color: "rgba(211,238,157,0.75)", align: "center", track: 4 });
    ctx.restore();
    var lx = x + 190, ly = y + 260, lw = 900, lh = 860;
    P.sheet(ctx, lx, ly, lw, lh, { key: "coverlabel", shadow: 0.3 });
    ctx.strokeStyle = C.ink; ctx.lineWidth = 3; ctx.strokeRect(lx + 26, ly + 26, lw - 52, lh - 52);
    ctx.lineWidth = 1.2; ctx.strokeRect(lx + 36, ly + 36, lw - 72, lh - 72);
    P.cond(ctx, cv.lines[0], lx + lw / 2, ly + 175, 112, { color: C.ink, align: "center", track: 6 });
    ctx.fillStyle = C.teal; ctx.fillRect(lx + 120, ly + 210, lw - 240, 5);
    P.cond(ctx, cv.lines[1], lx + lw / 2, ly + 300, 64, { color: C.ink, align: "center", track: 2 });
    P.cond(ctx, cv.lines[2], lx + lw / 2, ly + 372, 44, { color: C.ink, align: "center", medium: true, track: 1 });
    P.cond(ctx, cv.lines[3], lx + lw / 2, ly + 440, 44, { color: C.teal, align: "center", track: 3 });
    P.type(ctx, cv.lines[5], lx + lw / 2 - cv.lines[5].length * 15.6 / 2, ly + 600, 26, { bold: true });
    P.type(ctx, cv.lines[6], lx + lw / 2 - cv.lines[6].length * 14.4 / 2, ly + 648, 24);
    P.cond(ctx, cv.footer, lx + lw / 2, ly + lh - 80, 26, { color: "rgba(28,32,28,0.75)", align: "center", track: 5 });
    // corner tape
    P.tape(ctx, lx + 20, ly + 12, "          ", { rot: -0.6, w: 120 });
    P.tape(ctx, lx + lw - 20, ly + lh - 10, "          ", { rot: -0.6, w: 120 });
    if (o.title) { // extra title for the vertical cut
      P.cond(ctx, o.title, lx + lw / 2, ly + 520, 40, { color: C.red, align: "center", track: 3 });
    }
  };
  /* Cover swinging open about the spine (top-down). p 0..1 */
  P.drawCoverSwing = function (ctx, p) {
    var c = Math.cos(Math.PI * p), x = -40;
    if (p < 0.5) {
      ctx.save(); ctx.translate(x, 0); ctx.scale(c, 1); ctx.translate(-x, 0); P.drawCover(ctx); ctx.restore();
      ctx.fillStyle = "rgba(0,0,0," + 0.3 * Math.sin(Math.PI * p) + ")"; ctx.fillRect(x, -40, 1210 * c, 1530);
    } else {
      var w = -1210 * c;
      P.board(ctx, x - w, -40, w, 1530, "#0A555B");
      ctx.fillStyle = "rgba(0,0,0," + 0.3 * (1 - p) + ")"; ctx.fillRect(x - w, -40, w, 1530);
    }
  };

  /* ---------- SCENE 1: cover and scope ---------- */
  P.scenes.cover = function (ctx) {
    var W = P.S.W, H = P.S.H;
    if (F.t < ev("s1.cut")) {
      var on = P.lampLevel("s1.lampOn");
      P.drawElevation(ctx, { on: on, draw: function (c) {
        P.standingRocket(c, W * 0.74, H * 0.83, 520);
        var k = prog("s1.slide0", ev("s1.slide1") - ev("s1.slide0"), E.out);
        var bx = lerp(W + 520, W * 0.44, k), by = H * 0.86;
        P.binderSlab(c, bx, by, 760);
        var push = since("s1.slide1") > 0 ? clamp(1 - since("s1.slide1") * 2) : 1;
        P.hand(c, { x: bx + 470 + (1 - push) * 260, y: by - 70 - (1 - push) * 60, rot: -Math.PI / 2 - 0.15, pose: "flat", scale: 0.9, id: "hR", lift: 20 });
      } });
      return;
    }
    // rostrum: cover, then the scope page
    var tOpen = ev("s1.coverOpen"), opened = ev("s1.coverOpened");
    var camCover = { x: 560, y: 725, z: 0.7 + clamp((F.t - ev("s1.cut")) / 10) * 0.05 };
    var camScope = { x: 300, y: 520, z: 0.95 };
    var camStamp = { x: 300, y: 820, z: 0.95 };
    var cam = F.t < tOpen ? camCover : P.camLerp(camCover, camScope, P.seg(F.t, tOpen, opened + 0.6));
    cam = P.camLerp(cam, camStamp, P.seg(F.t, ev("s1.stampDown") - 1.2, ev("s1.stampDown") - 0.2));
    cam = P.camLerp(cam, P.CAM_PAGE, P.seg(F.t, ev("s1.turn"), ev("s1.turn") + 0.75));
    ctx.save();
    P.camera(ctx, cam);
    P.drawMat(ctx);
    P.rocket(760).draw(ctx, -620, 760, { rot: -0.08 });
    if (F.t < tOpen) {
      P.drawCover(ctx);
    } else {
      var turnP = prog("s1.turn", 0.75, E.io);
      P.board(ctx, R.x - 14, R.y - 30, R.w + 44, R.h + 60, C.teal);
      if (turnP > 0) P.drawPage(ctx, "toc", { size: 21 });
      P.turn(ctx, turnP, function () { drawScope(ctx); });
      var swing = P.seg(F.t, tOpen, opened, E.io);
      if (swing < 1) P.drawCoverSwing(ctx, swing);
      else P.board(ctx, -1250, -40, 1210, 1530, "#0A555B");
      if (swing >= 0.5) P.rocket(760).draw(ctx, -620, 760, { rot: -0.08 });
      var ringsOpen = F.t < tOpen + 0.17;
      P.drawRings(ctx, ringsOpen);
    }
    // hands: resting at the edges, then opening the cover
    var reach = ev("s1.reach");
    if (F.t > reach - 0.1 && F.t < opened + 1.5) {
      var hk = P.track(F.t, [[reach, { x: 1500, y: 1500, rot: -0.6, lift: 60 }], [tOpen, { x: 1150, y: 900, rot: -1.2, lift: 30 }], [opened, { x: -700, y: 950, rot: -1.6, lift: 140 }], [opened + 1.4, { x: -1400, y: 1600, rot: -1.6, lift: 140 }]]);
      P.hand(ctx, Object.assign(hk, { pose: F.t < tOpen ? "flat" : "grip", scale: 1.0, id: "hR" }));
    }
    // the stamp
    var sd = ev("s1.stampDown"), hit = ev("s1.stampHit"), up = ev("s1.stampUp");
    var sx = 600, sy = 1210;
    if (F.t > sd - 0.6 && F.t < up + 1.4) {
      var desc = P.seg(F.t, sd - 0.6, hit, E.in), rise = P.seg(F.t, up, up + 1.2, E.io);
      var hgt = F.t < hit ? (1 - desc) * 260 : rise * 300;
      var squash = F.t >= hit && F.t < hit + 0.17 ? 1 : 0;
      var scl = 1 + hgt / 900;
      P.stamp(320).draw(ctx, sx + hgt * 0.5, sy - hgt * 0.35, { sx: scl * (1 + squash * 0.05), sy: scl * (1 - squash * 0.06), lift: hgt, key: "s" });
      P.hand(ctx, { x: sx + 190 + hgt * 0.5, y: sy + 150 - hgt * 0.35, rot: -0.95, pose: "grip", scale: 0.95 * scl, id: "hS", lift: 60 + hgt });
    }
    ctx.restore();
    P.lamp(ctx, W, H, 1);
  };
  function drawScope(ctx) {
    P.drawPage(ctx, "scope", { size: 21 });
    if (F.t >= ev("s1.stampHit")) P.inkStamp(ctx, 600, 1210, ["THIS MANUAL AUTHORIZES NO", "IGNITION, PROPULSION OR FLIGHT."], { size: 30, rot: -0.035 });
  }

  /* ---------- SCENE 2: table of contents ---------- */
  P.drawTocMarks = function (ctx, info, names) {
    var lh = info.lh;
    function circ(id, ev0, seed) {
      var g = info.segs[id]; if (!g) return null;
      var pts = P.ellipsePts(g.x + g.w / 2, g.y + lh * 0.42, g.w / 2 + info.cw * 1.1, lh * 0.62, 1.15, seed);
      P.pencilLine(ctx, pts, P.prog(ev0, 0.9, E.io), { width: 3.2 });
      return pts;
    }
    var out = { c6: circ("t6", names.c6, 3), c8: circ("t8", names.c8, 5) };
    if (names.u7 && info.segs.t7) {
      var g = info.segs.t7, u = P.prog(names.u7, 0.6, E.io), pts = [];
      for (var i = 0; i <= 30; i++) pts.push([g.x + i * g.w / 30, g.y + lh * 0.92 + Math.sin(i * 0.9) * 1.2]);
      P.pencilLine(ctx, pts, u, { width: 3 });
      out.u7 = pts;
    }
    return out;
  };
  /* Where the pencil tip is during the contents page. */
  P.tocPencilTip = function (info, leadPrefix, mk, leadDur) {
    leadDur = leadDur || 0.42;
    var tip = null, i;
    for (i = 0; i < 9; i++) {
      var a = ev(leadPrefix + i), g = info.segs["t" + (i + 1)], r = info.rows["t" + (i + 1)];
      if (F.t >= a && F.t < a + leadDur + 0.05 && g) { var k = clamp((F.t - a) / leadDur); tip = [lerp(g.x - 20 * info.cw, g.x - 4, k), r.y1 - info.lh * 0.12]; }
    }
    function along(pts, t0, d) { return pts[Math.min(pts.length - 1, Math.floor(pts.length * clamp((F.t - t0) / d)))]; }
    var marks = P._tocMarks;
    if (marks) {
      if (marks.c6 && F.t >= ev(mk.c6) - 0.3 && F.t < ev(mk.c6) + 0.9) tip = along(marks.c6, ev(mk.c6), 0.9);
      if (marks.c8 && F.t >= ev(mk.c8) - 0.3 && F.t < ev(mk.c8) + 0.9) tip = along(marks.c8, ev(mk.c8), 0.9);
      if (marks.u7 && F.t >= ev(mk.u7) && F.t < ev(mk.u7) + 0.6) tip = along(marks.u7, ev(mk.u7), 0.6);
    }
    if (!tip) {
      var g6 = info.segs.t6, g8 = info.segs.t8;
      if (g6 && g8) tip = F.t < ev(mk.c6) ? [g6.x - 60, g6.y - info.lh * 0.8] : F.t < ev(mk.c8) ? [g6.x + g6.w + 40, g6.y + info.lh * 1.4] : [g8.x + g8.w + 40, g8.y + info.lh * 1.6];
    }
    return tip;
  };
  P.scenes.toc = function (ctx) {
    var W = P.S.W, H = P.S.H;
    var cam0 = P.CAM_PAGE, cam1 = { x: 660, y: 390, z: 1.22 };
    var cam = P.camLerp(cam0, cam1, P.seg(F.t, ev("s2a") - 0.8, ev("s2a") + 0.2));
    cam = P.camLerp(cam, P.CAM_A, prog("s2.turn", 0.75));
    ctx.save(); P.camera(ctx, cam);
    P.drawMat(ctx);
    P.drawBinder(ctx, { leftPageNo: "A" });
    P.rocket(760).draw(ctx, -620, 760, { rot: -0.08 });
    var turnP = prog("s2.turn", 0.75);
    if (turnP > 0) P.drawDivider(ctx, "div1");
    var info;
    P.turn(ctx, turnP, function () {
      info = P.drawPage(ctx, "toc", { size: 21 });
      P._tocMarks = P.drawTocMarks(ctx, info, { c6: "s2.circle6", c8: "s2.circle8", u7: "s2.underline7" });
    });
    P.drawRings(ctx, false);
    // pencil gliding down the leaders, then circling
    if (turnP === 0 && info) {
      var tip = P.tocPencilTip(info, "s2.lead", { c6: "s2.circle6", c8: "s2.circle8", u7: "s2.underline7" });
      if (tip) P.pencilInHand(ctx, tip[0], tip[1], { ang: -2.2, lift: F.t % 1 < 0.5 ? 4 : 8 });
    }
    ctx.restore();
    P.lamp(ctx, W, H, 1);
  };
})();
