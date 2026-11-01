/* V3D-TO-33-1 — the 9:16 social cut, "Preflight in 60 Seconds" (1080 × 1920). */
(function () {
  "use strict";
  var P = window.P33T, C = P.C, F = P.F, clamp = P.clamp, lerp = P.lerp, E = P.ease;
  var R = P.R, ev = P.ev, prog = P.prog;
  var CT = function () { return window.P33T_CONTENT; };
  function tickP(name) { return prog(name, 0.35, E.out); }

  P.scenes.vcover = function (ctx) {
    var W = P.S.W, H = P.S.H;
    ctx.save(); P.camera(ctx, { x: 560, y: 760, z: 0.86 + clamp(F.t / 3) * 0.03 });
    P.drawMat(ctx);
    P.drawCover(ctx, { title: "PREFLIGHT IN 60 SECONDS" });
    P.rocket(760).draw(ctx, 560, 1700, { rot: -0.04, key: "vr" });
    ctx.restore();
    P.lamp(ctx, W, H, P.lampLevel("v.lampOn"), 0.4, 0.3);
  };

  P.scenes.vtoc = function (ctx) {
    var W = P.S.W, H = P.S.H;
    var cam = P.camLerp({ x: 560, y: 620, z: 0.93 }, { x: 560, y: 760, z: 1.0 }, P.seg(F.t, ev("s2a") - 0.6, ev("s2a") + 0.2));
    ctx.save(); P.camera(ctx, cam);
    P.drawMat(ctx);
    P.board(ctx, R.x - 14, R.y - 30, R.w + 44, R.h + 60, C.teal);
    var turnP = prog("v.turn", 0.75), info;
    if (turnP > 0) P.drawPage(ctx, "p23", { size: 30, h: 1980 });
    P.turn(ctx, turnP, function () {
      info = P.drawPage(ctx, "toc", { size: 34, measure: 46, h: 1600 });
      P._tocMarks = P.drawTocMarks(ctx, info, { c6: "v.circle6", c8: "v.circle8" });
    });
    if (turnP === 0 && info) {
      var tip = P.tocPencilTip(info, "v.lead", { c6: "v.circle6", c8: "v.circle8", u7: "v.circle8" }, 0.1);
      if (tip) P.pencilInHand(ctx, tip[0], tip[1], { ang: -2.1, lift: 6, scale: 0.95, L: 280 });
    }
    ctx.restore();
    P.lamp(ctx, W, H, 1, 0.4, 0.28);
  };

  P.scenes.vpreflight = function (ctx) {
    var W = P.S.W, H = P.S.H, split = 830;
    var D = P.preflightState("v");
    // ---- the page, lower part of the frame, following the current step
    var order = ["v.tick0", "v.tick1", "v.tick3", "v.tick5", "v.tick6", "v.tick7", "v.tick8", "v.tick9"];
    var stepY = [180, 420, 560, 760, 880, 960, 1110, 1220], target = 120;
    order.forEach(function (n, i) { if (F.t > ev(n) - 0.2) target = stepY[i] - 380; });
    var camY = 128 + Math.max(0, target);
    var cy0 = P.S.cut.events["v.tick0"] - 0.2;
    ctx.save();
    ctx.fillStyle = C.mat; ctx.fillRect(0, 0, W, H);
    ctx.beginPath(); ctx.rect(0, split, W, H - split); ctx.clip();
    P.camera(ctx, { x: 560, y: lerp(128, camY, 1), z: 0.94 });
    P.drawMat(ctx);
    P.board(ctx, R.x - 14, R.y - 30, R.w + 44, 2040, C.teal);
    var st = { size: 30, ticks: {}, h: 1980 };
    var tk = { b0: "v.tick0", b1: "v.tick1", b2: "v.tick2", b3: "v.tick3", b4: "v.tick4", b4s: "v.tick4", b5: "v.tick5", b6: "v.tick6", b7: "v.tick7", b8: "v.tick8", b9: "v.tick9", b9s: "v.tick9", b10: "v.tick9" };
    Object.keys(tk).forEach(function (k) { st.ticks[k] = k === "b10" ? 0 : tickP(tk[k]); });
    var turnIn = P.seg(F.t, P.S.scene.start - 0.75, P.S.scene.start, E.io);
    P.drawPage(ctx, "p23", st);
    ctx.restore();
    // ---- the bench, upper part, pushing in on the laptop for the refusal
    var push = P.seg(F.t, ev("v.reach") - 0.3, ev("v.press"), E.io) * (1 - P.seg(F.t, ev("v.tick9") - 0.1, ev("v.tick9") + 0.5, E.io));
    var sc = lerp(0.88, 1.35, push), fx = lerp(-520, -330, push), fy = lerp(540, 560, push);
    ctx.save();
    ctx.beginPath(); ctx.rect(0, 0, W, split); ctx.clip();
    ctx.translate(W / 2, split / 2); ctx.scale(sc, sc); ctx.translate(-fx, -fy);
    P.drawMat(ctx);
    P.sheet(ctx, P.LP.x, P.LP.y, P.LP.w, P.LP.h, { key: "Lv" });
    P.drawPreflightBench(ctx, D, "v");
    P.drawPreflightHands(ctx, D, "v");
    ctx.restore();
    // seam between the two halves: the binder ring edge
    var g = ctx.createLinearGradient(0, split - 10, 0, split + 14); g.addColorStop(0, "rgba(0,0,0,0)"); g.addColorStop(0.5, "rgba(0,0,0,0.45)"); g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g; ctx.fillRect(0, split - 10, W, 24);
    P.lamp(ctx, W, H, 1, 0.4, 0.25);
  };

  P.scenes.vend = function (ctx) {
    var W = P.S.W, H = P.S.H;
    ctx.fillStyle = "#070807"; ctx.fillRect(0, 0, W, H);
    ctx.save(); ctx.globalAlpha = 0.5; ctx.drawImage(P.matTexture(), -900, -300); ctx.restore();
    var k = P.seg(F.t, P.S.scene.start, P.S.scene.start + 0.8, E.out);
    P.endCard(ctx, W, H, k, true);
    ctx.save(); ctx.globalAlpha = k;
    P.cond(ctx, "V3D-TO-33-1 · PREFLIGHT IN 60 SECONDS", W / 2, 260, 34, { color: "rgba(211,238,157,0.8)", align: "center", track: 3 });
    var lines = P.wrap(CT().disclaimer, 50);
    lines.forEach(function (l, i) { P.type(ctx, l, W / 2 - l.length * 9, 1560 + i * 34, 18, { color: "rgba(238,238,228,0.75)" }); });
    ctx.restore();
    ctx.save(); ctx.globalCompositeOperation = "multiply";
    var g = ctx.createRadialGradient(W / 2, H * 0.5, H * 0.2, W / 2, H * 0.5, H * 0.62);
    g.addColorStop(0, "rgba(255,240,215,1)"); g.addColorStop(1, "rgba(30,30,30,1)");
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); ctx.restore();
  };
})();
