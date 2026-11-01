/* V3D-TO-33-1 — scenes 3–7: Section I description, Section II procedures. */
(function () {
  "use strict";
  var P = window.P33T, C = P.C, F = P.F, clamp = P.clamp, lerp = P.lerp, E = P.ease;
  var R = P.R, ev = P.ev, prog = P.prog, since = P.since;
  var CT = function () { return window.P33T_CONTENT; };
  function at(name, d) { return F.t >= ev(name) + (d || 0); }
  function tickP(name) { return prog(name, 0.35, E.out); }

  /* draw the right page (or divider) with a turn into the next one */
  P.pageWithTurn = function (ctx, turnEv, cur, next) {
    var p = turnEv ? prog(turnEv, 0.75) : 0;
    if (p > 0 && next) next(ctx);
    var info;
    P.turn(ctx, p, function () { info = cur(ctx); });
    return info;
  };
  P.pg = function (id, st) { return function (ctx) { return /^div/.test(id) ? P.drawDivider(ctx, id) : P.drawPage(ctx, id, st); }; };

  /* ---------- laptop with a live screen ---------- */
  P.drawLaptop = function (ctx, x, y, w, screen, o) {
    o = o || {};
    P.laptop(w).draw(ctx, x, y, { key: "lap", lift: o.lift || 0 });
    var s = P.laptopScreen(w), j = P.jit("laptop" + w, 0.8);
    ctx.save(); ctx.translate(x + j[0], y + j[1]);
    ctx.beginPath(); ctx.rect(s.x + 6, s.y + 6, s.w - 12, s.h - 12); ctx.clip();
    var g = ctx.createLinearGradient(s.x, s.y, s.x, s.y + s.h); g.addColorStop(0, "#14201C"); g.addColorStop(1, "#0B110F");
    ctx.fillStyle = g; ctx.fillRect(s.x, s.y, s.w, s.h);
    if (screen && (o.on === undefined || o.on > 0)) { ctx.globalAlpha = o.on === undefined ? 1 : o.on; screen(ctx, s.x + 18, s.y + 18, s.w - 36, s.h - 36); ctx.globalAlpha = 1; }
    var gl = ctx.createLinearGradient(s.x, s.y, s.x + s.w, s.y + s.h); gl.addColorStop(0, "rgba(255,255,255,0.08)"); gl.addColorStop(0.4, "rgba(255,255,255,0)");
    ctx.fillStyle = gl; ctx.fillRect(s.x, s.y, s.w, s.h);
    ctx.restore();
  };
  /* terminal: lines = [{text, at, dur (typing), out:true}] */
  P.terminal = function (ctx, x, y, w, h, lines, size) {
    size = size || 15; var lh = size * 1.45, rows = [];
    lines.forEach(function (L) {
      if (F.t < L.at) return;
      var n = L.dur ? Math.floor(L.text.length * clamp((F.t - L.at) / L.dur)) : L.text.length;
      rows.push({ text: L.text.slice(0, n), cmd: L.cmd, full: n >= L.text.length });
    });
    var maxRows = Math.floor(h / lh), start = Math.max(0, rows.length - maxRows);
    rows.slice(start).forEach(function (r, i) {
      var yy = y + size + i * lh;
      if (r.cmd) { P.type(ctx, "$ ", x, yy, size, { color: C.lime, alpha: 0.9 }); P.type(ctx, r.text, x + size * 1.2, yy, size, { color: "#E6F2D5" }); }
      else P.type(ctx, r.text, x, yy, size, { color: "#9FB89A", alpha: 0.9 });
      if (i === rows.length - start - 1 && F.drawing % 12 < 6) { ctx.fillStyle = C.lime; ctx.fillRect(x + (r.cmd ? size * 1.2 : 0) + r.text.length * size * 0.6 + 2, yy - size * 0.8, size * 0.55, size * 0.95); }
    });
  };

  /* ---------- SCENE 3: Section I, description ---------- */
  var FIG_L = 760; // rocket length in FIGURE 1-1
  P.scenes.desc = function (ctx) {
    var W = P.S.W, H = P.S.H;
    var unfold = prog("s3.unfold", 0.9, E.io);
    var camFig = { x: 560, y: 700, z: 0.76 }, camFO = { x: 1200, y: 640, z: 0.78 };
    var cam = P.camLerp(P.CAM_A, camFig, P.seg(F.t, ev("s3.turnFig"), ev("s3.turnFig") + 0.9));
    cam = P.camLerp(cam, camFO, unfold);
    cam = P.camLerp(cam, P.CAM_A, prog("s3.turn", 0.6, E.io, -0.3));
    ctx.save(); P.camera(ctx, cam);
    P.drawMat(ctx);
    P.drawBinder(ctx, {});
    P.rocket(760).draw(ctx, -620, 760, { rot: -0.08 });
    var turnFig = prog("s3.turnFig", 0.75), endTurn = prog("s3.turn", 0.75);
    if (endTurn > 0) P.drawDivider(ctx, "div2");
    P.turn(ctx, endTurn, function () {
      if (turnFig > 0) drawFig(ctx);
      P.turn(ctx, turnFig, function () { P.drawDivider(ctx, "div1"); });
      if (unfold > 0) {
        // the panel swings out to the right: reveal the finished foldout behind its moving edge
        ctx.save(); ctx.beginPath(); ctx.rect(R.x - 40, R.y - 60, R.w + 40 + R.w * 1.15 * unfold, R.h + 120); ctx.clip();
        drawFoldout(ctx, 1);
        ctx.restore();
        if (unfold < 1) {
          var ex = R.x + R.w + R.w * 1.15 * unfold, fw = R.w * 1.15 * (1 - unfold) * 0.35;
          ctx.save(); ctx.fillStyle = "#E4E1D3"; ctx.shadowColor = "rgba(20,10,0,0.35)"; ctx.shadowBlur = 20; ctx.shadowOffsetX = 8;
          ctx.fillRect(ex - fw, R.y, fw, R.h); ctx.restore();
          var g = ctx.createLinearGradient(ex - fw, 0, ex, 0); g.addColorStop(0, "rgba(0,0,0,0.25)"); g.addColorStop(1, "rgba(0,0,0,0)");
          ctx.fillStyle = g; ctx.fillRect(ex - fw, R.y, fw, R.h);
        }
      }
    });
    P.drawRings(ctx, false);
    ctx.restore();
    P.lamp(ctx, W, H, 1);
  };
  function drawFig(ctx) {
    var pg = CT().pages.fig11;
    P.drawPage(ctx, "fig11", { size: 22 });
    P.type(ctx, pg.figure, R.x + R.w / 2 - pg.figure.length * 6.6, R.y + R.h - 92, 22, { bold: true });
    var ex = P.seg(F.t, ev("s3.explode"), ev("s3.explode") + 1.4, E.back), cx = R.x + 560, top = R.y + 210;
    var D = FIG_L / 8.6;
    // exploded stack along the axis, parts lifting off the page then settling into place
    var lift = Math.sin(Math.PI * clamp((F.t - ev("s3.explode")) / 1.4)) * 90;
    var items = [
      { n: 1, part: P.rocketPiece("nose", FIG_L), x: cx, y: lerp(top + 150, top + 80, ex) },
      { n: 3, part: P.rocketPiece("canard", FIG_L), x: lerp(cx - D * 0.55, cx - D * 1.6, ex), y: lerp(top + 290, top + 300, ex), rot: Math.PI / 2 },
      { n: 3, part: P.rocketPiece("canard", FIG_L), x: lerp(cx + D * 0.55, cx + D * 1.6, ex), y: lerp(top + 290, top + 300, ex), rot: -Math.PI / 2, label: false },
      { n: 2, part: P.rocketPiece("body", FIG_L), x: cx, y: lerp(top + 470, top + 560, ex) },
      { n: 4, part: P.rocketPiece("fin", FIG_L), x: lerp(cx - D * 0.7, cx - D * 2.3, ex), y: lerp(top + 740, top + 860, ex), rot: Math.PI },
      { n: 4, part: P.rocketPiece("fin", FIG_L), x: lerp(cx + D * 0.7, cx + D * 2.3, ex), y: lerp(top + 740, top + 860, ex), label: false },
      { n: 5, part: P.esp32(190), x: lerp(cx, cx - 330, ex), y: lerp(top + 470, top + 470, ex), rot: Math.PI / 2 },
      { n: 6, part: P.mpu(90), x: lerp(cx, cx - 330, ex), y: lerp(top + 470, top + 640, ex) },
      { n: 7, part: P.servo(96), x: lerp(cx, cx + 330, ex), y: lerp(top + 430, top + 380, ex) },
      { n: 8, part: P.servo(96, { noHorn: true, label: "IGN" }), x: lerp(cx, cx + 330, ex), y: lerp(top + 600, top + 620, ex) },
    ];
    items.forEach(function (it, i) {
      var vis = ex > 0.02 || it.n <= 4;
      if (!vis) return;
      it.part.draw(ctx, it.x, it.y, { rot: it.rot || 0, lift: lift * (0.6 + (i % 3) * 0.2), key: "f" + i, alpha: it.n > 4 ? clamp(ex * 3) : 1 });
    });
    if (ex > 0.2) P.horn(26).draw(ctx, cx + 440, top + 640, { rot: 0.4, key: "fh", alpha: clamp(ex * 3) });
    // ink callouts with numbered leaders, drawn one by one
    var spots = { 1: [cx + 20, top + 60], 2: [cx + 30, top + 600], 3: [cx + D * 1.6, top + 300], 4: [cx + D * 2.4, top + 860], 5: [cx - 330, top + 430], 6: [cx - 330, top + 640], 7: [cx + 330, top + 380], 8: [cx + 330, top + 620] };
    var ends = { 1: [cx + 330, top + 40], 2: [cx + 200, top + 760], 3: [cx + 330, top + 250], 4: [cx + 360, top + 950], 5: [cx - 470, top + 330], 6: [cx - 470, top + 760], 7: [cx + 470, top + 300], 8: [cx + 470, top + 720] };
    for (var n = 1; n <= 8; n++) {
      var k = prog("s3.callout" + (n - 1), 0.45, E.out);
      if (k <= 0) continue;
      var a = spots[n], b = ends[n];
      P.pencilLine(ctx, [a, [lerp(a[0], b[0], k), lerp(a[1], b[1], k)]], 1, { color: "rgba(28,32,28,0.85)", width: 2 });
      if (k > 0.9) {
        ctx.save(); ctx.strokeStyle = C.ink; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(b[0] + (b[0] > cx ? 18 : -18), b[1], 17, 0, 7); ctx.stroke(); ctx.restore();
        P.type(ctx, String(n), b[0] + (b[0] > cx ? 18 : -18) - 6.6, b[1] + 7, 22, { bold: true });
      }
    }
    // legend
    var leg = CT().pages.fig11.callouts, ly = R.y + 1195;
    leg.forEach(function (s, i) {
      if (F.t < ev("s3.callout" + i) + 0.3) return;
      var col = i % 2, row = Math.floor(i / 2);
      P.type(ctx, (i + 1) + "  " + s, R.x + 140 + col * 470, ly + row * 34, 20);
    });
  }
  function drawFoldout(ctx, k) {
    // a second sheet swings out from the right edge of the page
    var x0 = R.x + R.w, w = R.w * 1.15 * k, h = R.h;
    if (w < 4) return;
    var pg = CT().pages.fo1;
    ctx.save();
    ctx.shadowColor = "rgba(20,10,0,0.35)"; ctx.shadowBlur = 24; ctx.shadowOffsetX = 6; ctx.shadowOffsetY = 10;
    ctx.fillStyle = C.paper; ctx.fillRect(R.x, R.y, R.w + w, h); ctx.restore();
    ctx.drawImage(P.paperSprite(R.w * 2, R.h, "fo"), R.x, R.y, R.w + w, h);
    // crease
    ctx.fillStyle = "rgba(60,40,10,0.18)"; ctx.fillRect(x0 - 2, R.y, 4, h);
    if (k < 1) { ctx.fillStyle = "rgba(0,0,0," + 0.25 * (1 - k) + ")"; ctx.fillRect(x0, R.y, w, h); return; }
    P.type(ctx, P33PUB(), R.x + 80, R.y + 54, 19, { alpha: 0.85 });
    P.type(ctx, "FOLDOUT", R.x + 2 * R.w - 120, R.y + 54, 19, { alpha: 0.85 });
    ctx.fillStyle = "rgba(28,32,28,0.55)"; ctx.fillRect(R.x + 80, R.y + 68, 2 * R.w - 120, 2);
    P.type(ctx, pg.figure, R.x + 120, R.y + 150, 26, { bold: true });
    P.type(ctx, "FO-1", R.x + R.w * 1.07 - 24, R.y + R.h - 46, 21);
    // the system laid out on the foldout, with clay wires carrying beads
    var y = R.y + 560, xd = R.x + 330, xl = R.x + 1150, xr = R.x + 1880;
    P.drawLaptop(ctx, xd, y, 330, function (c, sx, sy, sw) {
      P.type(c, "DASHBOARD", sx, sy + 20, 17, { color: C.lime });
      P.type(c, "RAW SESSION (not evidence)", sx, sy + 48, 13, { color: "#9FB89A" });
    });
    P.launcherBox(300).draw(ctx, xl, y, { key: "fl" });
    P.launcherLive(ctx, xl, y, 300, 0, 0);
    P.tile(80, "GPS").draw(ctx, xl - 120, y - 210, { key: "g" }); P.tile(80, "COMPASS").draw(ctx, xl, y - 220, { key: "c" }); P.tile(80, "BARO").draw(ctx, xl + 120, y - 210, { key: "b" });
    P.esp32(190).draw(ctx, xr, y - 60, { key: "fr" });
    P.mpu(80).draw(ctx, xr - 120, y + 120, { key: "fm" });
    for (var i = 0; i < 4; i++) P.servo(64).draw(ctx, xr + 30 + (i % 2) * 110, y + 110 + Math.floor(i / 2) * 80, { key: "fs" + i });
    // UART: a teal clay snake; I2C: lime
    var uart = [[xl + 150, y + 10], [xl + 300, y + 120], [xr - 260, y + 80], [xr - 95, y - 40]];
    P.wire(ctx, uart, C.teal, 14, "uart");
    P.wire(ctx, [[xr - 60, y - 10], [xr - 110, y + 40], [xr - 140, y + 70], [xr - 125, y + 105]], C.lime, 9, "i2c");
    // Wi-Fi: ink arcs, not a wire
    ctx.save(); ctx.setLineDash([10, 9]); ctx.strokeStyle = "rgba(28,32,28,0.75)"; ctx.lineWidth = 2.5;
    for (var a = 0; a < 3; a++) { ctx.beginPath(); ctx.moveTo(xd + 180, y - 40 - a * 18); ctx.quadraticCurveTo((xd + xl) / 2, y - 220 - a * 30, xl - 160, y - 40 - a * 18); ctx.stroke(); }
    ctx.restore();
    // beads travelling
    var tw = F.t - ev("s3.wifi");
    if (tw > 0) for (var b = 0; b < 3; b++) {
      var u = ((tw * 0.6 + b / 3) % 1), dir = b % 2 ? 1 - u : u;
      var px = lerp(xd + 180, xl - 160, dir), py = y - 40 - 4 * Math.sin(Math.PI * dir) * 45 - 18;
      P.bead(ctx, px, py, C.lime, 1.1);
    }
    var tu = F.t - ev("s3.uart");
    if (tu > 0) for (b = 0; b < 4; b++) { var uu = (tu * 0.5 + b / 4) % 1; var q = P.bez(uart, b % 2 ? 1 - uu : uu); P.bead(ctx, q[0], q[1], b % 2 ? C.ivory : C.lime, 1.15); }
    // the three typed lines, exactly as on the record
    pg.lines.forEach(function (l, i) { P.type(ctx, l, R.x + 120, R.y + 900 + i * 40, 25.5); });
    P.type(ctx, "Wi-Fi is drawn as ink: there is no cable. The UART is a wire.", R.x + 120, R.y + 1060, 19, { color: "#4B5049" });
    // VIEW A-A: roll control, looking aft
    var va = prog("s3.viewAA", 0.6, E.back);
    if (va > 0) drawViewAA(ctx, R.x + 1880, R.y + 1110, 150 * va);
    var internals = prog("s3.internals", 0.5);
    if (internals > 0 && internals < 1.01) {
      ctx.save(); ctx.globalAlpha = 0.5 * Math.sin(Math.PI * clamp((F.t - ev("s3.internals")) / 2.4));
      ctx.strokeStyle = C.lime; ctx.lineWidth = 6; ctx.beginPath(); ctx.ellipse(xr - 50, y + 30, 240, 190, 0, 0, 7); ctx.stroke(); ctx.restore();
    }
  }
  function P33PUB() { return CT().pub; }
  /* End view of the body with four canards; roll then steady. */
  function drawViewAA(ctx, x, y, R0) {
    if (R0 < 5) return;
    P.sheet(ctx, x - R0 * 1.9, y - R0 * 1.7, R0 * 3.8, R0 * 3.5, { key: "vaa", shadow: 0.3 });
    P.type(ctx, "VIEW A-A  LOOKING AFT · ROLL ONLY", x - R0 * 1.75, y - R0 * 1.45, 17, { bold: true });
    var tr = F.t - ev("s3.roll"), ts = F.t - ev("s3.steady");
    var roll = tr < 0 ? 0 : 0.6 * Math.sin(tr * 2.6) * Math.exp(-Math.max(0, ts) * 1.6);
    var def = tr < 0 ? 0 : -0.2 * Math.sin(tr * 2.6 + 0.5) * Math.exp(-Math.max(0, ts) * 1.6);
    ctx.save(); ctx.translate(x, y + R0 * 0.15); ctx.rotate(roll);
    for (var i = 0; i < 4; i++) {
      ctx.save(); ctx.rotate(i * Math.PI / 2); ctx.translate(0, -R0 * 0.62); ctx.rotate(def);
      P.part("aacanard", 30, 70, function (r) { return [{ path: P.rrect(-12, -32, 24, 64, 10, r, 1), color: C.tealDeep }]; }).draw(ctx, 0, 0, { key: "c" + i, sx: R0 / 150, shadow: false });
      ctx.restore();
    }
    P.part("aabody", 160, 160, function (r) { return [{ path: P.ellipse(0, 0, 70, 70, r, 1.2), color: C.ivory }]; }).draw(ctx, 0, 0, { sx: R0 / 150, key: "b" });
    ctx.restore();
    ctx.strokeStyle = "rgba(28,32,28,0.7)"; ctx.lineWidth = 2; ctx.setLineDash([6, 6]);
    ctx.beginPath(); ctx.arc(x, y + R0 * 0.15, R0 * 0.95, -2.4, -0.74); ctx.stroke(); ctx.setLineDash([]);
  }
  P.drawViewAA = drawViewAA;

  /* ---------- the hardware cluster used on the bench ---------- */
  P.benchKit = function (ctx, o) {
    // o: {x, y (launcher centre), armed, led, rocket:[x,y,rot], horn: state}
    var lx = o.x, ly = o.y;
    P.launcherBox(280).draw(ctx, lx, ly, { key: "bk" });
    P.launcherLive(ctx, lx, ly, 280, o.armed || 0, o.led || 0);
    P.tape(ctx, lx - 72, ly + 112, o.armed > 0.5 ? "ARM" : "SAFE", { size: 15 });
    P.tile(70, "GPS").draw(ctx, lx - 100, ly - 160, { key: "bg" }); P.tile(70, "COMPASS").draw(ctx, lx, ly - 168, { key: "bc" }); P.tile(70, "BARO").draw(ctx, lx + 100, ly - 160, { key: "bb" });
  };

  /* ---------- SCENE 4: II-A offline review ---------- */
  var termLines = function () {
    return [
      { text: "python -m evidence status", at: ev("s4.type2"), dur: 0.8, cmd: true },
      { text: "Project 33 evidence status", at: ev("s4.out2") },
      { text: "Record state: 8 claims · 3 contradicted · 4 unresolved ·", at: ev("s4.out2") + 0.08 },
      { text: "1 supported within stated limits · 0 accepted physical measurements", at: ev("s4.out2") + 0.16 },
      { text: "python -m evidence check", at: ev("s4.type3"), dur: 0.75, cmd: true },
      { text: "  \"record_consistency\": \"passed\",", at: ev("s4.tick3") - 0.15 },
      { text: "python -m evidence build --output build/review", at: ev("s4.type4"), dur: 1.25, cmd: true },
      { text: "  \"physical_performance\": \"not_established\",", at: ev("s4.tick4") - 0.15 },
      { text: "python -m evidence verify build/review", at: ev("s4.type5"), dur: 1.0, cmd: true },
      { text: "  \"bundle_integrity\": \"verified\",", at: ev("s4.tick5") - 0.15 },
      { text: "  \"not_established\": [\"scientific validity\", \"physical performance\", …", at: ev("s4.tick5") - 0.05 },
    ];
  };
  P.termLines = termLines;
  P.scenes.offline = function (ctx) {
    var W = P.S.W, H = P.S.H;
    var camStage = { x: 60, y: 540, z: 0.92 };
    var cam = P.camLerp(P.CAM_A, camStage, prog("s4.turn0", 0.9, E.io, 0.2));
    cam = P.camLerp(cam, P.CAM_A, prog("s4.turn", 0.6, E.io, -0.4));
    ctx.save(); P.camera(ctx, cam);
    P.drawMat(ctx);
    P.drawBinder(ctx, { leftPageNo: "1-4" });
    // hardware pushed aside, laptop stays
    var push = prog("s4.push", 1.0, E.io);
    ctx.save(); ctx.translate(-push * 900, 0);
    P.benchKit(ctx, { x: -830, y: 330 });
    P.rocket(620).draw(ctx, -720, 900, { rot: 0.04, key: "r" });
    ctx.restore();
    if (push > 0 && push < 1) {
      P.hand(ctx, { x: -560 - push * 900, y: 620, rot: -Math.PI / 2 - 0.1, pose: "flat", scale: 1.0, id: "hR", lift: 25 });
    }
    var lapIn = prog("s4.push", 0.8, E.out, 0.4);
    P.drawLaptop(ctx, -500, 560, 700, function (c, sx, sy, sw, sh) { P.terminal(c, sx, sy, sw, sh, termLines(), 15); }, { lift: 0 });
    // the review packet pops up as a tiny booklet
    var bk = prog("s4.booklet", 0.6, E.back);
    if (bk > 0) drawBooklet(ctx, -830, 980 - bk * 40, bk);
    var st = { size: 22, ticks: {} };
    ["a1", "a2", "a3", "a4", "a5", "a6"].forEach(function (id, i) { st.ticks[id] = tickP("s4.tick" + (i + 1)); });
    var hi = clamp((F.t - ev("s4.note")) * 2) * clamp((ev("s4e.end") + 0.6 - F.t) * 2);
    P.pageWithTurn(ctx, "s4.turn", function (c) {
      var p = prog("s4.turn0", 0.75);
      if (p < 1) { if (p > 0) P.drawPage(c, "p21", st); P.turn(c, p, function () { P.drawDivider(c, "div2"); }); return; }
      var info = P.drawPage(c, "p21", st);
      if (hi > 0) { var r = info.rows.nv; c.save(); c.globalAlpha = 0.28 * hi; c.fillStyle = C.lime; c.fillRect(info.x0 - 8, r.y0 - 8, info.measure * info.cw + 16, r.y1 - r.y0 + 4); c.restore(); }
      return info;
    }, P.pg("p23", { size: 22 }));
    P.drawRings(ctx, false);
    // typing hands at the laptop
    var typing = ["s4.type2", "s4.type3", "s4.type4", "s4.type5"].some(function (n) { return F.t >= ev(n) - 0.1 && F.t < ev(n) + 1.3; });
    if (F.t > ev("s4.push") + 0.9 && F.t < ev("s4.turn") - 0.2) {
      var bob = typing ? (F.drawing % 2) * 8 : 0;
      P.hand(ctx, { x: -640, y: 990 - bob, rot: 0.2, pose: "rest", scale: 0.85, id: "hL", mirror: true, lift: 18 + bob });
      P.hand(ctx, { x: -360, y: 990 - (typing ? ((F.drawing + 1) % 2) * 8 : 0), rot: -0.2, pose: "rest", scale: 0.85, id: "hR", lift: 18 });
    }
    ctx.restore();
    P.lamp(ctx, W, H, 1);
  };
  function drawBooklet(ctx, x, y, k) {
    P.part("booklet", 230, 160, function (r) {
      return [{ path: P.rrect(-115, -80, 230, 160, 10, r, 1), color: C.ivory, opts: { lit: 0.1 } },
        { draw: function (c) {
          c.fillStyle = "rgba(0,0,0,0.15)"; c.fillRect(-2, -78, 4, 156);
          P.type(c, "REVIEW", -100, -40, 17, { bold: true }); P.type(c, "PACKET", -100, -16, 17, { bold: true });
          P.type(c, "index.html", 10, 30, 15, { color: C.tealDeep });
          P.type(c, "build/review/", 10, 8, 13, { color: "#4B5049" });
        } }];
    }).draw(ctx, x, y, { sx: k, lift: 30 * (1 - k) + 6 });
  }

  /* ---------- SCENE 5: II-B inert bench preflight ---------- */
  P.dashboardScreen = function (c, sx, sy, sw, sh, D) {
    // D: {on, raw, tele, ready, abort, calib, reject}
    var sz = 13;
    P.type(c, "Project 33 telemetry dashboard", sx, sy + 14, 14, { color: C.lime });
    P.type(c, "Session: bench_EXAMPLE · RAW SESSION (not evidence) · origin undeclared", sx, sy + 36, 10.5, { color: D.raw ? "#F0F7DD" : "#9FB89A" });
    if (D.raw) { c.save(); c.globalAlpha = 0.25 * D.raw; c.fillStyle = C.lime; c.fillRect(sx + 220, sy + 25, 152, 15); c.restore(); }
    P.type(c, "Data quality: " + (D.tele ? "packets arriving · last packet 0.1s ago" : "no packets yet"), sx, sy + 56, 10.5, { color: "#9FB89A" });
    var y = sy + 84;
    P.type(c, "Rocket State: " + (D.tele ? (D.ready ? "ARMED" : "IDLE") : "---"), sx, y, sz, { color: "#E6F2D5" });
    P.type(c, "GPS: " + (D.tele ? "no fix" : "NO NMEA"), sx, y + 22, sz, { color: "#E6F2D5" });
    P.type(c, "Alt: " + (D.tele ? "not reported" : "—"), sx + 150, y + 22, sz, { color: "#E6F2D5" });
    P.type(c, "Heartbeat: " + (D.tele ? "updating" : "—"), sx, y + 44, sz, { color: "#E6F2D5" });
    var log = [];
    if (D.abort) log.push("ABORT:Arming switch flipped OFF.");
    if (D.calib) log.push("calibrate · sent (no acknowledgement)");
    if (D.reject) log.push("CMD_REJECT:dashboard_launch_disabled");
    log.slice(-2).forEach(function (l, i) { P.type(c, l, sx, y + 68 + i * 17, 12, { color: /^CMD|^ABORT/.test(l) ? "#F3D58A" : "#9FB89A" }); });
    // buttons
    ["CALIBRATE GYRO", "DUMP LOG", "DIGITAL LAUNCH"].forEach(function (b, i) {
      var bx = sx + i * (sw / 3), by = sy + sh - 30, bw = sw / 3 - 10;
      var pressed = (i === 2 && D.press) || (i === 0 && D.calPress);
      c.fillStyle = pressed ? "#55604F" : "#2F3A33"; c.beginPath(); c.roundRect(bx, by + (pressed ? 2 : 0), bw, 26, 4); c.fill();
      P.type(c, b, bx + bw / 2 - b.length * 3.6, by + 18 + (pressed ? 2 : 0), 12, { color: "#E6F2D5" });
    });
  };
  P.preflightState = function (pre) {
    // pre: event prefix ("s5" for the film, "v" for the vertical cut)
    var e = function (n) { return ev(pre + "." + n); };
    return {
      on: F.t >= e("dashOn") ? 1 : 0, raw: clamp((F.t - e("rawGlow")) * 2) * clamp((e("rawGlow") + 2.4 - F.t)),
      tele: F.t >= (pre === "s5" ? e("telemetry") : e("tick5") - 0.6), armed: clamp((F.t - e("armOn")) * 6) * (F.t < e("armOff") ? 1 : 0),
      ready: F.t >= e("ready") && F.t < e("armOff"), abort: F.t >= e("abort"), calib: pre === "s5" ? F.t >= e("calibrate") : F.t >= e("tick8") - 0.2,
      calPress: pre === "s5" && F.t >= e("calibrate") && F.t < e("calibrate") + 0.25,
      press: F.t >= e("press") && F.t < e("press") + 0.3, reject: F.t >= e("press") + 0.2,
    };
  };
  /* The slip that curls out of the laptop with the refusal printed on it. */
  P.rejectSlip = function (ctx, x, y, k) {
    if (k <= 0) return;
    var w = 470, len = 74 * k;
    ctx.save(); ctx.translate(x, y);
    ctx.shadowColor = "rgba(20,10,0,0.3)"; ctx.shadowBlur = 10; ctx.shadowOffsetX = 4; ctx.shadowOffsetY = 6;
    ctx.fillStyle = "#F1EFE3";
    ctx.beginPath(); ctx.moveTo(-w / 2, 0); ctx.lineTo(w / 2, 0); ctx.lineTo(w / 2, len); ctx.quadraticCurveTo(0, len + 14 * k, -w / 2, len); ctx.closePath(); ctx.fill();
    ctx.shadowColor = "transparent";
    var g = ctx.createLinearGradient(0, len - 16, 0, len + 12); g.addColorStop(0, "rgba(0,0,0,0)"); g.addColorStop(1, "rgba(60,40,10,0.18)");
    ctx.fillStyle = g; ctx.fillRect(-w / 2, len - 16, w, 28);
    if (len > 40) P.type(ctx, "CMD_REJECT:dashboard_launch_disabled", -205, len - 22, 19, { color: C.ink });
    ctx.restore();
  };
  P.scenes.preflight = function (ctx) {
    var W = P.S.W, H = P.S.H;
    var camP = { x: 80, y: 560, z: 0.92 };
    var cam = P.camLerp(P.CAM_A, camP, P.seg(F.t, P.S.scene.start, P.S.scene.start + 0.8));
    // push in on the laptop for the refusal, then back
    var lap = { x: -380, y: 520, z: 1.25 };
    cam = P.camLerp(cam, lap, P.seg(F.t, ev("s5g") - 0.2, ev("s5g") + 0.6) * (1 - P.seg(F.t, ev("s5.tick9") - 0.2, ev("s5.tick9") + 0.5)));
    cam = P.camLerp(cam, P.CAM_A, prog("s5.turn", 0.6, E.io, -0.3));
    ctx.save(); P.camera(ctx, cam);
    P.drawMat(ctx);
    P.drawBinder(ctx, { leftPageNo: "2-2" });
    var D = P.preflightState("s5");
    drawPreflightBench(ctx, D, "s5");
    var st = { size: 22, ticks: {} };
    var tk = { b0: "s5.tick0", b1: "s5.tick1", b2: "s5.tick2", b3: "s5.tick3", b4: "s5.tick4", b4s: "s5.tick4s", b5: "s5.tick5", b6: "s5.tick6", b7: "s5.tick7", b8: "s5.tick8", b9: "s5.tick9", b10: "s5.tick10" };
    Object.keys(tk).forEach(function (k) { st.ticks[k] = tickP(tk[k]); });
    P.pageWithTurn(ctx, "s5.turn", P.pg("p23", st), P.pg("p26", { size: 22 }));
    P.drawRings(ctx, false);
    drawPreflightHands(ctx, D, "s5");
    ctx.restore();
    P.lamp(ctx, W, H, 1);
  };
  /* Bench layout shared by the film and the vertical cut. */
  function drawPreflightBench(ctx, D, pre, o) {
    o = o || {};
    var e = function (n) { return ev(pre + "." + n); };
    var ox = o.ox || 0, oy = o.oy || 0;
    ctx.save(); ctx.translate(ox, oy);
    // placards land before their steps
    var pw = prog(pre === "s5" ? "s5.warning" : "v.warning", 0.4, E.back), pc = prog(pre === "s5" ? "s5.caution" : "v.caution", 0.4, E.back);
    if (pw > 0) P.placard("WARNING", "No energetic material is present during any repository test.", 330).draw(ctx, -800, 150, { sx: 1.25 - pw * 0.25, lift: (1 - pw) * 140, key: "pw" });
    if (pc > 0) P.placard("CAUTION", "Power servos from a supply sized for stall current.", 330).draw(ctx, -440, 150, { sx: 1.25 - pc * 0.25, lift: (1 - pc) * 140, key: "pc" });
    // rocket, ignition servo and the dish
    P.rocket(640).draw(ctx, -560, 930, { rot: 0.03, key: "r5" });
    P.servo(84, { noHorn: true, label: "IGN" }).draw(ctx, -880, 780, { key: "ign" });
    P.dish(150).draw(ctx, -700, 780, { key: "dish" });
    P.tape(ctx, -700, 862, "HORN · REMOVED", { size: 14 });
    var hl = prog(pre + ".hornLift", 0.9, E.io), hd = F.t >= e("hornDish");
    var hx = lerp(-856, -700, hl), hy = lerp(780, 772, hl) - Math.sin(Math.PI * hl) * 0;
    if (!hd) P.horn(30).draw(ctx, hx, hy, { rot: hl * 0.8, lift: Math.sin(Math.PI * hl) * 120, key: "horn" });
    else P.horn(30).draw(ctx, -700, 772, { rot: 0.8, key: "horn" });
    // launcher and sensors
    P.benchKit(ctx, { x: -810, y: 470, armed: D.armed, led: D.ready ? 1 : 0 });
    // UART wire launcher → rocket
    P.wire(ctx, [[-680, 520], [-620, 640], [-560, 760], [-520, 890]], C.teal, 12, "uart5");
    if (D.tele) { var tt = F.t * 0.7; for (var b = 0; b < 3; b++) { var q = P.bez([[-680, 520], [-620, 640], [-560, 760], [-520, 890]], (tt + b / 3) % 1); P.bead(ctx, q[0], q[1], C.lime, 0.9); } }
    // laptop with the dashboard
    var lw = 520;
    P.drawLaptop(ctx, -330, 520, lw, function (c, sx, sy, sw, sh) { P.dashboardScreen(c, sx, sy, sw, sh, D); }, { on: D.on });
    if (!D.on) P.tape(ctx, -330, 420, "DASHBOARD", { size: 16 });
    // Wi-Fi beads hop between laptop and launcher when connected
    if (F.t >= (pre === "s5" ? e("wifi") : e("tick3") - 0.3) && (pre !== "s5" || F.t < e("lid"))) {
      ctx.save(); ctx.setLineDash([8, 8]); ctx.strokeStyle = "rgba(220,240,226,0.45)"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(-590, 400); ctx.quadraticCurveTo(-640, 300, -700, 380); ctx.stroke(); ctx.restore();
      var u = (F.t * 0.8) % 1; P.bead(ctx, lerp(-590, -700, u), 390 - Math.sin(Math.PI * u) * 60, C.lime, 0.8);
    }
    // the refusal slip
    var sk = prog(pre + ".slip", 0.9, E.out);
    P.rejectSlip(ctx, -330, 772, sk);
    ctx.restore();
  }
  P.drawPreflightBench = drawPreflightBench;
  function drawPreflightHands(ctx, D, pre) {
    var e = function (n) { return ev(pre + "." + n); };
    // horn lift
    var hl = P.seg(F.t, e("hornLift") - 0.4, e("hornDish") + 0.5, E.io);
    if (hl > 0 && hl < 1) {
      var k = P.seg(F.t, e("hornLift"), e("hornLift") + 0.9, E.io);
      P.hand(ctx, { x: lerp(-850, -690, k) + 40, y: lerp(870, 862, k) + 140, rot: -0.35, pose: "pinch", scale: 0.85, id: "hR", lift: 20 + Math.sin(Math.PI * k) * 80 });
    }
    // arm switch flips
    [e("armOn"), e("armOff")].forEach(function (t0) {
      if (F.t > t0 - 0.5 && F.t < t0 + 0.6) P.hand(ctx, { x: -870 + 60, y: 560 + 150, rot: -0.3, pose: "point", scale: 0.85, id: "hL", mirror: true, lift: 20 + 40 * clamp(Math.abs(F.t - t0) * 2) });
    });
    // finger to the launch button; nod after the refusal
    var reach = e("reach"), press = e("press");
    if (F.t > reach && F.t < e("nod") + 1.0) {
      var k2 = P.seg(F.t, reach, press, E.io), nod = F.t > e("nod") ? Math.sin(clamp((F.t - e("nod")) / 0.6) * Math.PI * 2) * 14 : 0;
      P.handTo(ctx, lerp(-60, -186, k2), lerp(760, 500, k2) + nod, { rot: -0.45, pose: "point", scale: 0.85, id: "hR", lift: F.t < press ? 50 * (1 - k2) + 10 : 10 + Math.abs(nod) });
    }
    if (pre === "s5" && F.t > e("calibrate") - 0.5 && F.t < e("calibrate") + 0.6) P.handTo(ctx, -480, 500, { rot: -0.3, scale: 0.85, id: "hR", lift: 15 });
  }
  P.drawPreflightHands = drawPreflightHands;

  /* ---------- SCENE 6: II-C canards and gain windows ---------- */
  P.scenes.canards = function (ctx) {
    var W = P.S.W, H = P.S.H;
    var cam = P.camLerp(P.CAM_A, { x: 60, y: 560, z: 0.92 }, P.seg(F.t, P.S.scene.start, P.S.scene.start + 0.8));
    cam = P.camLerp(cam, P.CAM_A, prog("s6.turn", 0.6, E.io, -0.3));
    ctx.save(); P.camera(ctx, cam);
    P.drawMat(ctx);
    P.drawBinder(ctx, { leftPageNo: "2-5" });
    // FIGURE 2-2 in clay: looking aft, four canards on protractors
    var cx = -560, cy = 400, names = [["UP", "27", "80°"], ["RIGHT", "25", "80°"], ["DOWN", "14", "115°"], ["LEFT", "26", "115°"]];
    P.sheet(ctx, cx - 340, cy - 330, 680, 640, { key: "fig22", shadow: 0.3 });
    P.type(ctx, "FIGURE 2-2 · LOOKING AFT", cx - 310, cy - 290, 18, { bold: true });
    var rolling = 0;
    for (var i = 0; i < 4; i++) { var t0 = ev("s6.rock" + i); if (F.t >= t0 && F.t < t0 + 1.0) rolling = Math.sin((F.t - t0) / 1.0 * Math.PI * 2) * 0.32; }
    ctx.save(); ctx.translate(cx, cy + 20); ctx.rotate(rolling);
    for (i = 0; i < 4; i++) {
      var settle = P.seg(F.t, ev("s6.center" + i), ev("s6.center" + i) + 0.8, E.settle), off = (1 - settle) * (i % 2 ? -0.35 : 0.3) * (F.t < ev("s6.center0") ? 1 : 1);
      ctx.save(); ctx.rotate(i * Math.PI / 2);
      // protractor
      ctx.strokeStyle = "rgba(28,32,28,0.6)"; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(0, -150, 70, -Math.PI * 0.95, -Math.PI * 0.05); ctx.stroke();
      for (var a = -0.21; a <= 0.211; a += 0.0698) { var aa = -Math.PI / 2 + a; ctx.beginPath(); ctx.moveTo(Math.cos(aa) * 60, -150 + Math.sin(aa) * 60); ctx.lineTo(Math.cos(aa) * 72, -150 + Math.sin(aa) * 72); ctx.stroke(); }
      ctx.translate(0, -128); ctx.rotate(off);
      P.part("c22", 34, 96, function (r) { return [{ path: P.rrect(-14, -46, 28, 92, 12, r, 1), color: C.tealDeep }]; }).draw(ctx, 0, 0, { key: "c" + i });
      ctx.restore();
    }
    P.part("b22", 200, 200, function (r) { return [{ path: P.ellipse(0, 0, 92, 92, r, 1.4), color: C.ivory }]; }).draw(ctx, 0, 0, { key: "b" });
    ctx.restore();
    names.forEach(function (n, k) {
      var pos = [[cx, cy - 210], [cx + 210, cy + 30], [cx, cy + 270], [cx - 210, cy + 30]][k];
      if (F.t < ev("s6.center" + k) + 0.3) return;
      P.tape(ctx, pos[0], pos[1], n[0] + " " + n[1] + " · " + n[2], { size: 15 });
    });
    // calibrate: hold still, the dashboard records only that it was sent
    if (F.t > ev("s6.hold") && F.t < ev("s6.card")) {
      P.hand(ctx, { x: cx - 120, y: cy + 250, rot: 0.5, pose: "flat", scale: 0.85, id: "hL", mirror: true, lift: 15 });
      if (F.t > ev("s6.calibrate")) P.tape(ctx, cx + 120, cy + 300, "CALIBRATE · SENT · NOT ACKNOWLEDGED", { size: 14 });
    }
    // gain-window card, the same motion for each row
    var ck = prog("s6.card", 0.5, E.back);
    if (ck > 0) {
      var gx = -560, gy = 900;
      P.sheet(ctx, gx - 300, gy - 120 + (1 - ck) * 60, 600, 230, { key: "gcard", shadow: 0.3, tint: "#EFEBDC" });
      P.type(ctx, "GAIN WINDOWS · ONE SESSION EACH", gx - 280, gy - 82, 16, { bold: true });
      var rows = [["Baseline", "0.50", "0.20"], ["Higher damping", "0.50", "0.30"], ["More proportional authority", "0.80", "0.20"], ["Conservative", "0.35", "0.15"]];
      rows.forEach(function (r, k) {
        var yy = gy - 46 + k * 34;
        P.type(ctx, r[0], gx - 260, yy, 16); P.type(ctx, "Kp " + r[1], gx + 90, yy, 16); P.type(ctx, "Kd " + r[2], gx + 190, yy, 16);
        P.tick(ctx, gx - 280, yy - 6, tickP("s6.row" + k), 0.6);
      });
      for (i = 0; i < 4; i++) { var r0 = ev("s6.rock" + i); if (F.t >= r0 - 0.2 && F.t < r0 + 1.1) P.hand(ctx, { x: cx + 60 + Math.sin(rolling) * 60, y: cy - 250, rot: Math.PI + rolling, pose: "grip", scale: 0.85, id: "hR", lift: 15 }); }
    }
    P.pageWithTurn(ctx, "s6.turn", P.pg("p26", { size: 22 }), P.pg("p28", { size: 22 }));
    P.drawRings(ctx, false);
    ctx.restore();
    P.lamp(ctx, W, H, 1);
  };

  /* ---------- SCENE 7: II-D session passport ---------- */
  P.scenes.passport = function (ctx) {
    var W = P.S.W, H = P.S.H;
    var cam = P.camLerp(P.CAM_A, { x: 60, y: 560, z: 0.92 }, P.seg(F.t, P.S.scene.start, P.S.scene.start + 0.8));
    cam = P.camLerp(cam, P.CAM_A, prog("s7.turn", 0.6, E.io, -0.3));
    ctx.save(); P.camera(ctx, cam);
    P.drawMat(ctx);
    P.drawBinder(ctx, { leftPageNo: "2-7" });
    // the session folder as a little file box
    var bx = -760, by = 330, lid = prog("s7.box", 0.5, E.io);
    P.part("filebox", 380, 300, function (r) {
      return [{ path: P.rrect(-190, -150, 380, 300, 14, r, 1.4), color: C.kraft, opts: { tex: 0.7 } },
        { path: P.rrect(-170, -130, 340, 260, 10, r, 1), color: "#9A774F", bb: { x: -170, y: -130, w: 340, h: 260 }, opts: { occ: 0.6, rim: 0.15 } }];
    }).draw(ctx, bx, by, { key: "fb" });
    ["telemetry.csv", "session.json", "commands.csv"].forEach(function (n, i) {
      P.sheet(ctx, bx - 150, by - 110 + i * 70, 300, 120, { key: "card" + i, shadow: 0.25 });
      P.type(ctx, n, bx - 130, by - 82 + i * 70, 17);
    });
    if (lid > 0) {
      ctx.save(); ctx.globalAlpha = lid;
      P.part("filelid", 400, 320, function (r) { return [{ path: P.rrect(-200, -160, 400, 320, 16, r, 1.4), color: "#C49A69", opts: { tex: 0.7 } }]; }).draw(ctx, bx, by - (1 - lid) * 60, { key: "fl", lift: (1 - lid) * 80 });
      ctx.restore();
      if (lid > 0.9) P.tape(ctx, bx, by, "RAW · DO NOT EDIT", { size: 18 });
    }
    // declaration card filled in by pencil
    var dk = prog("s7.declare", 1.1, E.io), dx = -380, dy = 340;
    P.sheet(ctx, dx - 150, dy - 120, 300, 240, { key: "decl", shadow: 0.25, tint: "#F0ECDD" });
    P.type(ctx, "DECLARATION", dx - 130, dy - 84, 17, { bold: true });
    ["operator", "origin  bench", "purpose", "inert configuration"].forEach(function (l, i) { P.type(ctx, l, dx - 130, dy - 46 + i * 34, 14, { color: "#4B5049" }); });
    for (var i = 0; i < 4; i++) {
      var pts = [], k = clamp(dk * 4 - i);
      for (var j = 0; j <= 20; j++) pts.push([dx - 10 + j * 6.5, dy - 50 + i * 34 + Math.sin(j * 1.7 + i) * 3]);
      if (i !== 1) P.pencilLine(ctx, pts, k, { width: 2 });
    }
    if (dk > 0 && dk < 1) P.pencilInHand(ctx, dx - 10 + 130 * ((dk * 4) % 1), dy - 50 + Math.floor(dk * 4) * 34, { ang: -2.0, scale: 0.8 });
    // the passport, stamped with its digests
    var pk = prog("s7.passport", 0.5, E.back), px = -560, py = 760;
    if (pk > 0) {
      P.part("passport", 300, 210, function (r) {
        return [{ path: P.rrect(-150, -105, 300, 210, 12, r, 1.2), color: C.teal },
          { draw: function (c) { c.fillStyle = "rgba(0,0,0,0.25)"; c.fillRect(-2, -103, 4, 206); P.cond(c, "SESSION", -130, -50, 30, { color: "rgba(211,238,157,0.85)", track: 2 }); P.cond(c, "PASSPORT", -130, -16, 30, { color: "rgba(211,238,157,0.85)", track: 2 }); } }];
      }).draw(ctx, px, py, { sx: pk, key: "pp", lift: (1 - pk) * 60 });
      if (F.t > ev("s7.passport") + 0.25) P.inkStamp(ctx, px + 66, py + 50, ["SHA-256 DIGESTS", "RECORDED"], { size: 14, color: C.lime, rot: -0.08, alpha: 0.9 });
    }
    // ACCEPTED hovers and never comes down
    var hv = prog("s7.hover", 0.8, E.io);
    if (hv > 0) {
      var tremble = (P.hash(F.drawing * 17) - 0.5) * 6 * clamp((F.t - ev("s7.noFall")) * 2);
      var sx = -260, sy = 760 - 30;
      P.stamp(240, "ACCEPTED").draw(ctx, sx + 120 * (1 - hv) + tremble, sy - 40 * (1 - hv), { sx: 1.18, lift: 150, key: "acc" });
      ctx.save(); ctx.setLineDash([6, 8]); ctx.strokeStyle = "rgba(220,240,226,0.5)"; ctx.lineWidth = 2; ctx.strokeRect(sx - 130, sy + 110, 260, 90); ctx.restore();
    }
    var tg = prog("s7.tag", 0.7, E.out);
    if (tg > 0) {
      var tx = lerp(-1150, -330, tg), ty = 1000;
      ctx.save(); ctx.strokeStyle = "rgba(240,236,220,0.8)"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(tx - 160, ty); ctx.quadraticCurveTo(tx - 260, ty + 40, tx - 380, ty - 10); ctx.stroke(); ctx.restore();
      P.part("nametag", 300, 100, function (r) { return [{ path: P.blob([[-150, -50], [130, -50], [150, 0], [130, 50], [-150, 50]], r, 1), color: "#F0ECDD", opts: { lit: 0.1, occ: 0.3 } }, { draw: function (c) { c.fillStyle = "#2A2F2B"; c.beginPath(); c.arc(-125, 0, 9, 0, 7); c.fill(); P.type(c, "NAMED REVIEWER", -100, 8, 21, { bold: true }); } }]; }).draw(ctx, tx, ty, { key: "nt" });
    }
    var st = { size: 22, ticks: { d1: tickP("s7.tick1"), d2: tickP("s7.tick2"), d3: tickP("s7.tick34"), d4: tickP("s7.tick34") } };
    P.pageWithTurn(ctx, "s7.turn", P.pg("p28", st), function (c) { P.drawDivider(c, "div3"); });
    P.drawRings(ctx, false);
    ctx.restore();
    P.lamp(ctx, W, H, 1);
  };
})();
