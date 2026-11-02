/* V3D-TO-33-1 — scenes 8–10: abnormal operations, limitations, gates, end, credits. */
(function () {
  "use strict";
  var P = window.P33T, C = P.C, F = P.F, clamp = P.clamp, lerp = P.lerp, E = P.ease;
  var R = P.R, ev = P.ev, prog = P.prog;
  var CT = function () { return window.P33T_CONTENT; };
  function tickP(name) { return prog(name, 0.35, E.out); }
  var STAGE = { x: 60, y: 560, z: 0.92 };

  /* ---------- the status board: a read-only clay panel ---------- */
  function statusBoard(ctx, x, y, s) {
    var w = 660, h = 420;
    P.part("statusboard", w, h, function (r) {
      return [{ path: P.rrect(-w / 2, -h / 2, w, h, 20, r, 1.6), color: "#8E978B", opts: { occ: 0.35 } },
        { path: P.rrect(-w / 2 + 18, -h / 2 + 18, w - 36, h - 36, 12, r, 1), color: "#1B211E", bb: { x: -w / 2 + 18, y: -h / 2 + 18, w: w - 36, h: h - 36 }, opts: { occ: 0.5, rim: 0.12, lit: 0.05 } }];
    }).draw(ctx, x, y, { key: "sb" });
    var x0 = x - w / 2 + 44, y0 = y - h / 2 + 64;
    P.type(ctx, "STATUS BOARD · READ-ONLY · NOT EVIDENCE", x0, y0, 16, { color: C.lime });
    var units = [["LINK", "SEEN"], ["LAUNCHER", "SEEN"], ["UART", s.after ? "SEEN" : "SUSPECT"], ["ROCKET", s.after ? "SEEN" : "SUSPECT"], ["IMU", "SUSPECT"], ["GPS", "SEEN"], ["BARO", "SEEN"], ["COMPASS", "SEEN"]];
    units.forEach(function (u, i) {
      var col = i % 2, row = Math.floor(i / 2), ux = x0 + col * 290, uy = y0 + 44 + row * 34;
      var sus = u[1] === "SUSPECT";
      P.type(ctx, u[0], ux, uy, 16, { color: "#C9D6C2" });
      P.type(ctx, u[1], ux + 140, uy, 16, { color: sus ? "#F3D58A" : "#9FD18B", bold: sus });
      if (s.flash && u[0].match(/UART|ROCKET/)) { ctx.save(); ctx.globalAlpha = s.flash * 0.35; ctx.fillStyle = C.lime; ctx.fillRect(ux + 136, uy - 16, 100, 22); ctx.restore(); }
    });
    // advisory tile, boxed like an equipment alert
    var ty = y0 + 210;
    if (s.tile > 0) {
      ctx.save(); ctx.translate(x0 + 270, ty + 26); ctx.scale(0.85 + 0.15 * s.tile, 0.85 + 0.15 * s.tile);
      ctx.fillStyle = "rgba(199,154,42,0.18)"; ctx.fillRect(-270, -26, 540, 52);
      ctx.strokeStyle = C.mustard; ctx.lineWidth = 4; ctx.strokeRect(-270, -26, 540, 52);
      P.type(ctx, "CAUTION  C-ROCKET-TELEMETRY-LOST", -250, 8, 19, { color: "#F3D58A", bold: true });
      ctx.restore();
    }
    P.type(ctx, "ISOLATION: " + (s.after ? "IMU" : "UART · ROCKET · IMU") + (s.after ? "" : "   NEXT: DUMP LOG"), x0, ty + 92, 15, { color: "#C9D6C2" });
  }

  /* ---------- SCENE 8: Sections III and IV ---------- */
  P.scenes.abnormal = function (ctx) {
    var W = P.S.W, H = P.S.H;
    var cam = P.camLerp(P.CAM_A, STAGE, prog("s8.turn0", 0.9, E.io, 0.1));
    cam = P.camLerp(cam, P.CAM_A, prog("s8.turn", 0.6, E.io, -0.3));
    ctx.save(); P.camera(ctx, cam);
    P.drawMat(ctx);
    P.drawBinder(ctx, { leftPageNo: "2-12" });
    // bench: launcher, rocket, the UART snake between them
    var slack = prog("s8.slack", 0.6, E.back), reply = F.t >= ev("s8.reply") && F.t < ev("s8.reply") + 1.4;
    P.launcherBox(250).draw(ctx, -840, 760, { key: "lb8" });
    P.launcherLive(ctx, -840, 760, 250, 0, 0);
    P.rocket(560).draw(ctx, -560, 1000, { rot: 0.02, key: "r8" });
    var sag = 70 * slack;
    var uart = [[-730, 800], [-700, 880 + sag], [-600, 930 + sag], [-520, 975]];
    P.wire(ctx, uart, C.teal, 12, "uart8");
    if (F.t < ev("s8.slack")) { for (var b = 0; b < 3; b++) { var q = P.bez(uart, (F.t * 0.7 + b / 3) % 1); P.bead(ctx, q[0], q[1], C.lime, 0.9); } }
    else if (!reply) { var q0 = P.bez(uart, 0.55); P.bead(ctx, q0[0], q0[1] + 8, C.lime, 0.9); }
    if (reply) for (b = 0; b < 3; b++) { var u = clamp((F.t - ev("s8.reply") - b * 0.25) / 0.8); if (u > 0 && u < 1) { var qq = P.bez(uart, 1 - u); P.bead(ctx, qq[0], qq[1], C.ivory, 1.1); } }
    // dashboard laptop with DUMP LOG
    var D = { tile: F.t >= ev("s8.tile"), press: F.t >= ev("s8.dump") && F.t < ev("s8.dump") + 0.3 };
    P.drawLaptop(ctx, -260, 760, 380, function (c, sx, sy, sw, sh) {
      P.type(c, "Project 33 telemetry dashboard", sx, sy + 12, 11, { color: C.lime });
      P.type(c, "Rocket telemetry: STALE", sx, sy + 34, 11, { color: D.tile ? "#F3D58A" : "#9FB89A" });
      if (D.tile) P.type(c, "C-ROCKET-TELEMETRY-LOST", sx, sy + 52, 11, { color: "#F3D58A", bold: true });
      if (F.t > ev("s8.reply") + 0.4) P.type(c, "LOG_START … LOG_END", sx, sy + 70, 11, { color: "#9FB89A" });
      ["STATUS BOARD", "DUMP LOG"].forEach(function (lbl, i) {
        var bx = sx + i * (sw / 2), by = sy + sh - 26, bw = sw / 2 - 8, pressed = i === 1 && D.press;
        c.fillStyle = pressed ? "#55604F" : "#2F3A33"; c.beginPath(); c.roundRect(bx, by + (pressed ? 2 : 0), bw, 22, 4); c.fill();
        P.type(c, lbl, bx + bw / 2 - lbl.length * 3.3, by + 15, 11, { color: "#E6F2D5" });
      });
    });
    // the board slides in when opened
    var bo = prog("s8.board", 0.6, E.back);
    if (bo > 0) statusBoard(ctx, -520, lerp(-200, 360, bo), { tile: clamp((F.t - ev("s8.board")) * 3), after: F.t >= ev("s8.update"), flash: clamp(1 - (F.t - ev("s8.update")) * 1.2) * (F.t >= ev("s8.update") ? 1 : 0) });
    // hands: open the board, press DUMP LOG
    if (F.t > ev("s8.board") - 0.6 && F.t < ev("s8.board") + 0.5) P.handTo(ctx, -260 - 95, 760 + 60, { rot: -0.4, scale: 0.8, id: "hR", lift: 20 });
    if (F.t > ev("s8.dump") - 0.6 && F.t < ev("s8.dump") + 0.6) P.handTo(ctx, -260 + 85, 760 + 60, { rot: -0.4, scale: 0.8, id: "hR", lift: 12 + 30 * clamp(Math.abs(F.t - ev("s8.dump")) * 2) });
    // pages: divider → 3-1 → FIGURE 3-1
    var st = { size: 22, ticks: { e1: tickP("s8.tick1"), e2: tickP("s8.tick2"), e3: tickP("s8.tick3") } };
    var sil = clamp((F.t - ev("s8.silence")) * 2) * clamp((ev("s8c.end") + 0.5 - F.t) * 2);
    P.pageWithTurn(ctx, "s8.turn", function (c) {
      var p0 = prog("s8.turn0", 0.75), p1 = prog("s8.tree", 0.75);
      if (p0 < 1) { if (p0 > 0) P.drawPage(c, "p31", st); P.turn(c, p0, function () { P.drawDivider(c, "div3"); }); return; }
      if (p1 > 0) drawTree(c);
      P.turn(c, p1, function () {
        var info = P.drawPage(c, "p31", st);
        if (sil > 0) ["en", "e3a"].forEach(function (id) { var r = info.rows[id]; c.save(); c.globalAlpha = 0.3 * sil; c.fillStyle = C.lime; c.fillRect(info.x0 - 8, r.y0 - 4, info.measure * info.cw + 16, r.y1 - r.y0); c.restore(); });
      });
    }, function (c) { P.drawDivider(c, "div5"); });
    P.drawRings(ctx, false);
    ctx.restore();
    P.lamp(ctx, W, H, 1);
  };
  function drawTree(ctx) {
    var pg = CT().pages.fig31;
    P.drawPage(ctx, "fig31", { size: 22 });
    P.wrap(pg.figure, 66).forEach(function (l, i) { P.type(ctx, l, R.x + 120, R.y + 150 + i * 32, 22, { bold: true }); });
    var cx = R.x + 560, ry = R.y + 270;
    ctx.save(); ctx.strokeStyle = C.ink; ctx.lineWidth = 3; ctx.strokeRect(cx - 360, ry, 720, 70); ctx.restore();
    P.type(ctx, pg.root, cx - pg.root.length * 6.6, ry + 44, 22, { bold: true });
    pg.rows.forEach(function (row, i) {
      var k = prog("s8.row" + i, 0.35, E.out);
      if (k <= 0) return;
      var y = ry + 130 + i * 116, n = parseInt(row[1], 10);
      ctx.save(); ctx.globalAlpha = k;
      ctx.strokeStyle = "rgba(28,32,28,0.8)"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(cx - 400, ry + 35); ctx.lineTo(cx - 430, ry + 35); ctx.lineTo(cx - 430, y + 30); ctx.lineTo(cx - 400, y + 30); ctx.stroke();
      ctx.strokeRect(cx - 400, y, 820, 96);
      P.type(ctx, row[0], cx - 380, y + 38, 21);
      P.type(ctx, row[1], cx + 400 - row[1].length * 12.6 - 18, y + 38, 21, { bold: true });
      for (var j = 0; j < 12; j++) {
        var bx = cx - 380 + j * 52, by = y + 70;
        if (j < n) P.bead(ctx, bx + 10, by, C.lime, 1.05);
        else { ctx.strokeStyle = "rgba(28,32,28,0.5)"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(bx + 10, by, 8, 0, 7); ctx.stroke(); }
      }
      ctx.restore();
    });
    P.type(ctx, pg.source, R.x + 120, R.y + R.h - 110, 18, { color: "#4B5049" });
  }

  /* ---------- SCENE 9: Section V, operating limitations ---------- */
  P.scenes.limits = function (ctx) {
    var W = P.S.W, H = P.S.H;
    if (F.t >= ev("s9.pan") && F.t < ev("s9.back")) { exhibit(ctx); return; }
    var cam = P.camLerp(P.CAM_A, STAGE, prog("s9.turn0", 0.9, E.io, 0.1));
    cam = P.camLerp(cam, P.CAM_A, prog("s9.turn", 0.6, E.io, -0.3));
    ctx.save(); P.camera(ctx, cam);
    P.drawMat(ctx);
    P.drawBinder(ctx, { leftPageNo: "4-2" });
    P.rocket(700).draw(ctx, -560, 520, { rot: -0.05, key: "r9" });
    // the lime sticky note, stamped, lies on the left page after the exhibit
    if (F.t >= ev("s9.back")) stickyNote(ctx, -560, 860, 1, true);
    var hi = F.t >= ev("s9f") ? clamp((F.t - ev("s9f")) * 1.5) : 0;
    P.pageWithTurn(ctx, "s9.turn", function (c) {
      var p0 = prog("s9.turn0", 0.75);
      if (p0 < 1) { if (p0 > 0) P.drawPage(c, "p51", { size: 22 }); P.turn(c, p0, function () { P.drawDivider(c, "div5"); }); return; }
      var info = P.drawPage(c, "p51", { size: 22 });
      if (hi > 0) ["l1", "l6", "l8", "l5"].forEach(function (id, i) {
        var r = info.rows[id], k = clamp(hi * 2 - i * 0.4); if (!r || k <= 0) return;
        c.save(); c.globalAlpha = 0.3 * k; c.fillStyle = C.lime; c.fillRect(info.x0 - 8, r.y0 - 4, info.measure * info.cw * k + 16, r.y1 - r.y0); c.restore();
      });
    }, function (c) { drawCds(c); });
    P.drawRings(ctx, false);
    ctx.restore();
    P.lamp(ctx, W, H, 1);
  };
  /* The bench from the front: four small exhibits, a travelling pool of light. */
  function exhibit(ctx) {
    var W = P.S.W, H = P.S.H;
    var spots = [W * 0.17, W * 0.42, W * 0.66, W * 0.88];
    var idx = F.t < ev("s9c") - 0.2 ? 0 : F.t < ev("s9d") - 0.2 ? 1 : F.t < ev("s9e") - 0.2 ? 2 : 3;
    var prevT = [ev("s9.pan"), ev("s9c") - 0.2, ev("s9d") - 0.2, ev("s9e") - 0.2][idx];
    var from = spots[Math.max(0, idx - 1)], px = lerp(from, spots[idx], P.seg(F.t, prevT, prevT + 0.7));
    P.drawElevation(ctx, { on: 0.72, noLamp: true, draw: function (c) {
      var base = H * 0.86;
      // C1 linkage on an upright test plate
      var th = P.seg(F.t, ev("s9.linkage"), ev("s9.gap"), E.io) * 1.6;
      var lk = P.linkage(c, spots[0] - 110, base - 230, 6.4, th);
      if (F.t >= ev("s9.gap")) {
        c.save(); c.strokeStyle = C.mustard; c.lineWidth = 3; c.setLineDash([5, 5]); c.beginPath(); c.arc(lk.C[0], lk.C[1], 26, 0, 7); c.stroke(); c.restore();
        P.tape(c, lk.C[0] + 60, lk.C[1] - 70, "GAP", { size: 18 });
      }
      P.tape(c, spots[0], base + 40, "C1 · LINKAGE AS SPECIFIED", { size: 17 });
      // C6 gauge on a stand
      var gv = F.t < ev("s9.gauge") ? 0 : 19 * P.seg(F.t, ev("s9.gauge"), ev("s9.needle") + 0.2, E.settle);
      P.part("gaugestand", 60, 150, function (r) { return [{ path: P.rrect(-12, -75, 24, 150, 8, r, 1), color: "#5B635A" }]; }).draw(c, spots[1], base - 70, { shadow: false });
      P.gauge(c, spots[1], base - 250, 130, gv);
      P.tape(c, spots[1], base + 40, "C6 · SPRING MARGIN " + (F.t >= ev("s9.needle") ? "19% · REQUIRED 20%" : ""), { size: 17 });
      // C5 two balances, the same rocket, opposite answers
      var tip = P.seg(F.t, ev("s9.scales"), ev("s9.scales") + 1.2, E.settle) * 0.22;
      P.balance(c, spots[2] - 165, base - 120, 190, tip, "A");
      P.balance(c, spots[2] + 165, base - 120, 190, -tip, "B");
      P.tape(c, spots[2] - 165, base - 290, "REFERENCE 1.55–1.57 cal", { size: 14 });
      P.tape(c, spots[2] + 165, base - 260, "RE-DERIVED 0.74–0.76 cal", { size: 14 });
      P.tape(c, spots[2] + 10, base + 40, "C5 · TWO MODELS DISAGREE", { size: 17 });
      // the daydream: a sticky note, stamped
      stickyNote(c, spots[3], H * 0.47, P.seg(F.t, ev("s9.sticky") - 0.3, ev("s9.sticky") + 0.4, E.back), F.t >= ev("s9.stamp"));
      if (F.t > ev("s9.stamp") - 0.8 && F.t < ev("s9.stamp") + 0.7) {
        var d = F.t < ev("s9.stamp") ? (ev("s9.stamp") - F.t) / 0.8 : 0;
        P.stamp(200).draw(c, spots[3] + d * 60, H * 0.47 - d * 120, { lift: 30 + d * 160, sx: 1 + d * 0.15, key: "st9" });
      }
    } });
    // the travelling pool of light
    ctx.save(); ctx.globalCompositeOperation = "screen";
    var g = ctx.createRadialGradient(px, H * 0.66, 30, px, H * 0.66, W * 0.2);
    g.addColorStop(0, "rgba(255,214,150,0.55)"); g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); ctx.restore();
  }
  function stickyNote(ctx, x, y, k, stamped) {
    if (k <= 0) return;
    ctx.save(); ctx.translate(x, y); ctx.rotate(0.05); ctx.scale(k, k);
    ctx.shadowColor = "rgba(0,0,0,0.3)"; ctx.shadowBlur = 12; ctx.shadowOffsetX = 4; ctx.shadowOffsetY = 6;
    ctx.fillStyle = "#D9EEA6"; ctx.fillRect(-120, -120, 240, 240); ctx.shadowColor = "transparent";
    ctx.fillStyle = "rgba(0,0,0,0.05)"; ctx.fillRect(-120, -120, 240, 30);
    // pencil doodle: a dotted arc and a tiny rocket
    ctx.strokeStyle = "rgba(55,58,54,0.8)"; ctx.lineWidth = 2.5; ctx.setLineDash([3, 7]);
    ctx.beginPath(); ctx.moveTo(-95, 85); ctx.quadraticCurveTo(-10, -150, 90, 40); ctx.stroke(); ctx.setLineDash([]);
    ctx.save(); ctx.translate(-30, -36); ctx.rotate(-0.6);
    ctx.beginPath(); ctx.moveTo(0, -22); ctx.lineTo(7, -8); ctx.lineTo(7, 16); ctx.lineTo(-7, 16); ctx.lineTo(-7, -8); ctx.closePath(); ctx.stroke();
    ctx.restore();
    ctx.restore();
    if (stamped) P.inkStamp(ctx, x, y + 40, ["NOT MEASURED"], { size: 26 * k, rot: -0.12, color: C.teal });
  }
  P.stickyNote = stickyNote;

  /* ---------- SCENE 10: change data summary, close, end card ---------- */
  function drawCds(ctx) {
    var pg = CT().pages.cds;
    P.drawPage(ctx, "cds", { size: 22 });
    P.cond(ctx, pg.title, R.x + 120, R.y + 170, 38, { color: C.ink });
    var x = R.x + 200, y0 = R.y + 240, gh = 92, gap = 26;
    pg.gates.forEach(function (gname, i) {
      var y = y0 + i * (gh + gap), human = i >= pg.humanFrom;
      ctx.save();
      ctx.strokeStyle = human ? C.teal : C.ink; ctx.lineWidth = human ? 4 : 2.5; ctx.strokeRect(x, y, 560, gh - 20);
      ctx.restore();
      P.type(ctx, gname, x + 24, y + 46, 22, { bold: human });
      if (i < pg.gates.length - 1) { ctx.fillStyle = C.ink; ctx.beginPath(); ctx.moveTo(x + 280, y + gh - 12); ctx.lineTo(x + 270, y + gh - 18); ctx.lineTo(x + 290, y + gh - 18); ctx.fill(); ctx.fillRect(x + 279, y + gh - 20, 2, gap + 14); }
      if (human) P.part("chbar", 10, 80, function (rr) { return [{ path: P.rrect(-4, -40, 8, 80, 4, rr, 0.5), color: C.teal }]; }).draw(ctx, R.x + R.w - 60, y + 36, { sy: 0.9, key: "g" + i });
    });
    // human line between SYNTHETIC TEST and INERT BENCH SETUP
    var hy = y0 + pg.humanFrom * (gh + gap) - gap / 2 - 6;
    ctx.save(); ctx.strokeStyle = C.mustard; ctx.lineWidth = 3; ctx.setLineDash([12, 8]); ctx.beginPath(); ctx.moveTo(x - 40, hy); ctx.lineTo(x + 640, hy); ctx.stroke(); ctx.restore();
    // eight claim beads seated at the gate each one has reached
    var counts = {};
    Object.keys(pg.claims).forEach(function (cid, i) {
      var g = pg.claims[cid], k = prog("s10.bead" + i, 0.7, E.back);
      if (k <= 0 && P.S.scene.id === "gates") return;
      if (P.S.scene.id !== "gates") k = 1;
      var n = counts[g] = (counts[g] || 0) + 1;
      var bx = x + 560 + n * 44, by = lerp(y0 - 140, y0 + g * (gh + gap) + 36, k);
      P.bead(ctx, bx, by, C.lime, 1.6);
      P.type(ctx, cid, bx - 12, by + 36, 15, { bold: true });
    });
    P.wrap(pg.note, 70).forEach(function (l, i) { P.type(ctx, l, R.x + 120, R.y + 1110 + i * 30, 19); });
    var tg = prog("s10.tag", 0.6, E.out);
    if (tg > 0) P.tape(ctx, lerp(R.x + 1400, x + 300, tg), hy - 2, "FROM HERE ON: A NAMED HUMAN", { size: 18 });
  }
  P.drawCds = drawCds;
  P.scenes.gates = function (ctx) {
    var W = P.S.W, H = P.S.H;
    var close = P.seg(F.t, ev("s10.close"), ev("s10.coverShut"), E.io);
    var camCover = { x: 560, y: 725, z: 0.7 };
    var cam = P.camLerp({ x: 600, y: 680, z: 0.82 }, camCover, P.seg(F.t, ev("s10.close") - 0.4, ev("s10.close") + 0.6));
    ctx.save(); P.camera(ctx, cam);
    P.drawMat(ctx);
    P.drawBinder(ctx, { leftPageNo: "5-2" });
    P.rocket(760).draw(ctx, -620, 760, { rot: -0.08 });
    drawCds(ctx);
    P.drawRings(ctx, F.t > ev("s10.rings") && F.t < ev("s10.rings") + 0.17);
    if (close > 0) {
      // the cover comes back over: the reverse of the opening swing
      if (close < 1) P.drawCoverSwing(ctx, 1 - close);
      else P.drawCover(ctx);
    }
    if (F.t > ev("s10.close") - 0.4 && F.t < ev("s10.coverShut") + 0.4) {
      var hk = P.track(F.t, [[ev("s10.close") - 0.4, { x: -1300, y: 1400, rot: 1.3, lift: 140 }], [ev("s10.close") + 0.2, { x: -700, y: 950, rot: 1.6, lift: 140 }], [ev("s10.coverShut"), { x: 1150, y: 900, rot: 1.2, lift: 30 }], [ev("s10.coverShut") + 0.4, { x: 1500, y: 1500, rot: 0.8, lift: 60 }]]);
      P.hand(ctx, Object.assign(hk, { pose: "flat", scale: 1.0, id: "hL", mirror: true }));
    }
    ctx.restore();
    P.lamp(ctx, W, H, 1);
  };
  /* Binder standing upright, cover to camera, rocket beside it (also the poster). */
  P.drawPosterSet = function (ctx, on) {
    var W = P.S.W, H = P.S.H;
    P.drawElevation(ctx, { on: on, draw: function (c) {
      var bx = W * 0.47, by = H * 0.86, s = 0.36;
      c.save(); c.filter = "blur(12px)"; c.fillStyle = "rgba(10,5,0,0.5)"; c.fillRect(bx - 230, by - 10, 480, 26); c.restore();
      c.save(); c.translate(bx, by - 1530 * s / 2 - 4); c.scale(s, s); c.translate(-560, -725); P.drawCover(c); c.restore();
      P.standingRocket(c, W * 0.7, by, 560);
    } });
  };
  function endCard(ctx, W, H, k, vertical) {
    var L = CT().pages.endcard.lines;
    ctx.save(); ctx.globalAlpha = k;
    var cw = vertical ? 900 : 1240, ch = vertical ? 900 : 520, x = (W - cw) / 2, y = vertical ? H * 0.5 - ch / 2 : H * 0.52 - ch / 2;
    P.sheet(ctx, x, y, cw, ch, { key: "endcard" + (vertical ? "v" : ""), shadow: 0.45 });
    ctx.strokeStyle = C.ink; ctx.lineWidth = 2; ctx.strokeRect(x + 22, y + 22, cw - 44, ch - 44);
    var cx = W / 2, yy = y + (vertical ? 120 : 110);
    if (vertical) {
      P.cond(ctx, "THE ROCKET IS THE SPECIMEN.", cx, yy, 54, { color: C.ink, align: "center" });
      P.cond(ctx, "THE RECORD IS THE EXPERIMENT.", cx, yy + 66, 54, { color: C.ink, align: "center" });
      yy += 190;
    } else {
      P.cond(ctx, L[0], cx, yy, 50, { color: C.ink, align: "center" });
      yy += 110;
    }
    P.cond(ctx, L[1], cx, yy, vertical ? 96 : 88, { color: C.teal, align: "center", track: 4 });
    var cmd = L[2], sz = vertical ? 40 : 38;
    P.type(ctx, cmd, cx - cmd.length * sz * 0.3, yy + (vertical ? 92 : 84), sz, { bold: true, color: C.tealDeep });
    var links = vertical ? ["github.com/topherchris420/33", "topherchris420.github.io/33"] : [L[3]];
    links.forEach(function (l, i) { var fs = vertical ? 30 : 24; P.type(ctx, l, cx - l.length * fs * 0.3, yy + (vertical ? 170 : 150) + i * 46, fs, {}); });
    P.cond(ctx, L[4], cx, yy + (vertical ? 290 : 210), 30, { color: "#4B5049", align: "center", medium: true });
    ctx.restore();
  }
  P.endCard = endCard;
  P.scenes.end = function (ctx) {
    var W = P.S.W, H = P.S.H, off = ev("s10.lampOff");
    if (F.t < off + 0.25) { P.drawPosterSet(ctx, P.lampLevel(null, "s10.lampOff")); return; }
    // lamp off: a single pool of light on the end card
    ctx.fillStyle = "#070807"; ctx.fillRect(0, 0, W, H);
    ctx.save(); ctx.globalAlpha = 0.5; ctx.drawImage(P.matTexture(), -600, -400); ctx.restore();
    var k = P.seg(F.t, off + 0.25, off + 1.0, E.out);
    endCard(ctx, W, H, k, false);
    ctx.save(); ctx.globalCompositeOperation = "multiply";
    var g = ctx.createRadialGradient(W / 2, H * 0.52, H * 0.25, W / 2, H * 0.52, W * 0.62);
    g.addColorStop(0, "rgba(255,240,215,1)"); g.addColorStop(1, "rgba(8,8,8,1)");
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); ctx.restore();
  };

  /* ---------- credits: glossary, index, disclaimer ---------- */
  function creditsPage(ctx, which) {
    var W = P.S.W, H = P.S.H, ct = CT();
    ctx.fillStyle = "#0A0B0A"; ctx.fillRect(0, 0, W, H);
    var pw = 1500, ph = 980, x = (W - pw) / 2, y = (H - ph) / 2;
    P.sheet(ctx, x, y, pw, ph, { key: "credits", shadow: 0.5 });
    P.type(ctx, ct.pub, x + 60, y + 54, 19, { alpha: 0.8 });
    ctx.fillStyle = "rgba(28,32,28,0.55)"; ctx.fillRect(x + 60, y + 68, pw - 120, 2);
    if (which === 0) {
      P.cond(ctx, "GLOSSARY", x + 60, y + 140, 46, { color: C.ink });
      ct.glossary.forEach(function (g, i) {
        var yy = y + 200 + i * 66;
        P.type(ctx, g[0], x + 60, yy, 22, { bold: true });
        P.type(ctx, g[1], x + 330, yy, 21);
      });
    } else if (which === 1) {
      P.cond(ctx, "INDEX", x + 60, y + 140, 46, { color: C.ink });
      P.type(ctx, "Chapter starts. Asterisk denotes illustration.", x + 60, y + 186, 19, { color: "#4B5049" });
      var ch = P.S.cut.chapters;
      ch.forEach(function (c, i) {
        var yy = y + 250 + i * 54, t = Math.floor(c.start / 60) + ":" + ("0" + Math.floor(c.start % 60)).slice(-2);
        var title = c.title.toUpperCase() + (/Description|Limitations|Abnormal/.test(c.title) ? " *" : "");
        var dots = Math.max(3, 92 - title.length - t.length);
        P.type(ctx, title + " " + ".".repeat(dots) + " " + t, x + 60, yy, 21);
      });
    } else {
      P.cond(ctx, "STANDING DISCLAIMER", x + 60, y + 140, 46, { color: C.ink });
      P.wrap(ct.disclaimer, 62).forEach(function (l, i) { P.type(ctx, l, x + 60, y + 240 + i * 52, 30); });
      P.type(ctx, "Source: github.com/topherchris420/33 at commit " + ct.commit + ". The repository governs.", x + 60, y + 620, 21, { color: "#4B5049" });
      P.type(ctx, "Narration voice: Kokoro-82M (Apache-2.0), synthesized locally. Score and sound: original.", x + 60, y + 680, 19, { color: "#4B5049" });
      P.type(ctx, "Type: Courier Prime and Barlow Condensed (SIL Open Font License).", x + 60, y + 716, 19, { color: "#4B5049" });
      P.cond(ctx, "VERS3DYNAMICS · BUILD A MODEL. MAKE A PREDICTION. MEASURE THE DIFFERENCE. KEEP THE RECORD HONEST.", x + pw / 2, y + ph - 70, 24, { color: C.teal, align: "center", track: 2 });
    }
  }
  P.scenes.credits = function (ctx) {
    var W = P.S.W, H = P.S.H;
    var which = F.t < ev("cr.index") ? 0 : F.t < ev("cr.disclaimer") ? 1 : 2;
    creditsPage(ctx, which);
    var fade = clamp((P.S.scene.end - F.t) / 1.2);
    var fin = clamp((F.t - P.S.scene.start) / 0.5);
    ctx.save(); ctx.globalCompositeOperation = "multiply";
    var g = ctx.createRadialGradient(W / 2, H / 2, H * 0.3, W / 2, H / 2, W * 0.7);
    g.addColorStop(0, "rgba(255,245,228,1)"); g.addColorStop(1, "rgba(30,28,24,1)");
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); ctx.restore();
    if (fade < 1 || fin < 1) { ctx.fillStyle = "rgba(0,0,0," + (1 - Math.min(fade, fin)) + ")"; ctx.fillRect(0, 0, W, H); }
  };
})();
