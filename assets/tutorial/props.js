/* V3D-TO-33-1 claymation engine — props. Every object is hand-shaped from
 * paths and shaded as plasticine; nothing is a photograph or a CG model. */
(function () {
  "use strict";
  var P = window.P33T, C = P.C, clamp = P.clamp, lerp = P.lerp;

  /* ---------- the rocket ---------- */
  // Horizontal profile, nose to the right. L = length.
  function rocketLayers(L, r, v, o) {
    o = o || {};
    var D = L / 8.6, x0 = -L / 2, xn = L * 0.27, layers = [];
    var bb = { x: -L / 2, y: -D * 1.6, w: L, h: D * 3.2 };
    // folding fins (tail), drawn first so the body overlaps their roots
    function fin(sign) {
      var y0 = sign * D * 0.42, tip = sign * D * 1.55;
      return P.poly([[x0 + L * 0.015, y0], [x0 + L * 0.19, y0], [x0 + L * 0.115, tip], [x0 + L * 0.005, tip * 0.97]], D * 0.06, r, D * 0.012);
    }
    if (!o.noFins) {
      [-1, 1].forEach(function (sg) { layers.push({ path: fin(sg), color: "#2A2F2B", bb: bb, opts: { occ: 0.45, rim: 0.3 } }); });
    }
    var body = P.rrect(x0, -D / 2, xn - x0 + D * 0.1, D, D * 0.18, r, D * 0.015);
    layers.push({ path: body, color: C.ivory, bb: { x: x0, y: -D / 2, w: xn - x0, h: D }, opts: { lit: 0.18 } });
    var nose = P.blob([[xn, -D / 2], [xn + L * 0.1, -D * 0.38], [L / 2, -D * 0.04], [L / 2, D * 0.04], [xn + L * 0.1, D * 0.38], [xn, D / 2]], r, D * 0.01);
    layers.push({ path: nose, color: "#F1EEE2", bb: { x: xn, y: -D / 2, w: L / 2 - xn, h: D } });
    var band = P.rrect(L * 0.12, -D / 2 - 1, L * 0.065, D + 2, 4, r, 0.6);
    layers.push({ path: band, color: C.teal, bb: { x: L * 0.12, y: -D / 2, w: L * 0.065, h: D }, opts: { lit: 0.25 } });
    if (!o.noCanards) {
      [-1, 1].forEach(function (sg) {
        var y0 = sg * D * 0.45, tip = sg * D * 0.98;
        layers.push({ path: P.poly([[L * 0.03, y0], [L * 0.1, y0], [L * 0.088, tip], [L * 0.05, tip]], D * 0.05, r, D * 0.01), color: C.tealDeep, bb: bb });
      });
      // the canard seen edge-on across the body
      layers.push({ draw: function (x) { x.fillStyle = "rgba(7,56,60,0.85)"; x.fillRect(L * 0.04, -2.2, L * 0.055, 4.4); } });
    }
    if (!o.noFins) {
      layers.push({ draw: function (x) {
        x.fillStyle = "rgba(42,47,43,0.9)"; x.fillRect(x0 + L * 0.015, -2.5, L * 0.17, 5);
        [-1, 1].forEach(function (sg) { x.fillStyle = C.silver; x.beginPath(); x.arc(x0 + L * 0.11, sg * D * 0.5, 3.4, 0, 7); x.fill(); });
      } });
    }
    // seam lines and the vers3 mark
    layers.push({ draw: function (x) {
      x.strokeStyle = "rgba(60,45,25,0.25)"; x.lineWidth = 1.2;
      [-0.18, 0.03].forEach(function (k) { x.beginPath(); x.moveTo(L * k, -D / 2 + 3); x.lineTo(L * k, D / 2 - 3); x.stroke(); });
      P.font(x, P.FONT.cond, D * 0.34); x.fillStyle = "rgba(11,93,99,0.55)"; x.fillText("33", -L * 0.1, D * 0.13);
    } });
    return layers;
  }
  P.rocket = function (L, o) {
    o = o || {};
    var id = "rocket" + L + (o.noFins ? "nf" : "") + (o.noCanards ? "nc" : "");
    return P.part(id, L, L / 8.6 * 3.3, function (r, v) { return rocketLayers(L, r, v, o); });
  };
  // Upright, for the bench elevation: rotate the drawing, keep the lamp at the top left.
  P.rocketUp = function (L) {
    return P.part("rocketUp" + L, L / 8.6 * 3.3, L, function (r, v, x) {
      var D = L / 8.6, ls = rocketLayers(L, r, v);
      return [{ draw: function (c) {
        c.save(); c.rotate(-Math.PI / 2);
        ls.forEach(function (Lr) {
          if (Lr.draw) Lr.draw(c);
          else P.clayFill(c, Lr.path, Lr.color, Lr.bb || { x: -L / 2, y: -D, w: L, h: D * 2 }, Object.assign({ variant: v, id: "ru" }, Lr.opts || {}));
        });
        c.restore();
      } }];
    });
  };
  // Exploded pieces for FIGURE 1-1 (vertical axis, nose up).
  P.rocketPiece = function (name, L) {
    var D = L / 8.6;
    return P.part("piece-" + name + L, name === "fin" ? D * 1.3 : name === "canard" ? D * 0.75 : D * 1.1, name === "nose" ? L * 0.24 : name === "body" ? L * 0.72 : name === "fin" ? L * 0.2 : D * 0.6, function (r) {
      if (name === "nose") return [{ path: P.blob([[-D / 2, L * 0.12], [-D * 0.38, -L * 0.0], [-D * 0.04, -L * 0.12], [D * 0.04, -L * 0.12], [D * 0.38, 0], [D / 2, L * 0.12]], r, D * 0.01), color: "#F1EEE2" }];
      if (name === "body") return [
        { path: P.rrect(-D / 2, -L * 0.36, D, L * 0.72, D * 0.16, r, D * 0.012), color: C.ivory, bb: { x: -D / 2, y: -L * 0.36, w: D, h: L * 0.72 } },
        { path: P.rrect(-D / 2 - 1, -L * 0.3, D + 2, L * 0.055, 4, r, 0.6), color: C.teal, bb: { x: -D / 2, y: -L * 0.3, w: D, h: L * 0.055 } },
        { draw: function (x) { P.font(x, P.FONT.cond, D * 0.32); x.fillStyle = "rgba(11,93,99,0.5)"; x.save(); x.rotate(-Math.PI / 2); x.fillText("33", -L * 0.05, D * 0.1); x.restore(); } },
      ];
      if (name === "fin") return [{ path: P.poly([[-D * 0.55, -L * 0.09], [-D * 0.55, L * 0.09], [D * 0.6, L * 0.07], [D * 0.55, -L * 0.02]], D * 0.08, r, D * 0.01), color: "#2A2F2B" },
        { draw: function (x) { x.fillStyle = C.silver; x.beginPath(); x.arc(-D * 0.4, -L * 0.06, 3.5, 0, 7); x.fill(); } }];
      return [{ path: P.poly([[-D * 0.3, D * 0.25], [-D * 0.2, -D * 0.25], [D * 0.2, -D * 0.25], [D * 0.32, D * 0.25]], D * 0.06, r, D * 0.01), color: C.tealDeep }];
    });
  };

  /* ---------- electronics ---------- */
  function engrave(x, text, px, py, size, color) {
    P.font(x, P.FONT.cond, size);
    x.fillStyle = "rgba(255,255,255,0.18)"; x.fillText(text, px + 0.8, py + 0.8);
    x.fillStyle = color || "rgba(0,0,0,0.45)"; x.fillText(text, px, py);
  }
  P.engrave = engrave;
  P.esp32 = function (w) {
    var h = w * 0.52;
    return P.part("esp32-" + w, w, h, function (r) {
      var L = [{ path: P.rrect(-w / 2, -h / 2, w, h, 8, r, 1.2), color: "#1E2422" }];
      L.push({ path: P.rrect(w * 0.02, -h * 0.32, w * 0.42, h * 0.64, 5, r, 0.8), color: "#9BA19A", bb: { x: w * 0.02, y: -h * 0.32, w: w * 0.42, h: h * 0.64 }, opts: { sheen: 0.2 } });
      L.push({ path: P.rrect(-w * 0.49, -h * 0.13, w * 0.09, h * 0.26, 3, r, 0.5), color: C.silver, bb: { x: -w * 0.5, y: -h * 0.13, w: w * 0.09, h: h * 0.26 } });
      L.push({ draw: function (x) {
        engrave(x, "ESP32", w * 0.09, h * 0.06, h * 0.2, "rgba(30,34,32,0.55)");
        x.strokeStyle = "rgba(211,238,157,0.5)"; x.lineWidth = 2; x.beginPath();
        for (var i = 0; i < 5; i++) { x.lineTo(w * 0.36 + (i % 2) * 6, -h * 0.26 + i * 5); } x.stroke();
        for (var k = 0; k < 15; k++) {
          [-1, 1].forEach(function (sg) {
            var px = -w * 0.42 + k * (w * 0.84 / 14), py = sg * h * 0.43;
            var g = x.createRadialGradient(px - 1.2, py - 1.2, 0.5, px, py, 3.6);
            g.addColorStop(0, "#F4F5F0"); g.addColorStop(1, "#8E938C"); x.fillStyle = g; x.beginPath(); x.arc(px, py, 3.4, 0, 7); x.fill();
          });
        }
        x.fillStyle = C.lime; x.beginPath(); x.arc(-w * 0.3, 0, 3, 0, 7); x.fill();
      } });
      return L;
    });
  };
  P.mpu = function (w) {
    return P.part("mpu-" + w, w, w * 0.8, function (r) {
      return [
        { path: P.rrect(-w / 2, -w * 0.4, w, w * 0.8, 6, r, 0.8), color: "#2C5F63" },
        { path: P.rrect(-w * 0.17, -w * 0.17, w * 0.34, w * 0.34, 3, r, 0.4), color: "#161917", bb: { x: -w * 0.17, y: -w * 0.17, w: w * 0.34, h: w * 0.34 } },
        { draw: function (x) {
          for (var k = 0; k < 8; k++) { x.fillStyle = C.silver; x.beginPath(); x.arc(-w * 0.38 + k * w * 0.108, w * 0.31, 2.4, 0, 7); x.fill(); }
          engrave(x, "MPU6050", -w * 0.4, -w * 0.24, w * 0.15, "rgba(211,238,157,0.65)");
        } },
      ];
    });
  };
  P.servo = function (w, o) {
    o = o || {};
    var h = w * 0.52, id = "servo-" + w + (o.noHorn ? "nh" : "") + (o.color || "");
    return P.part(id, w * 1.25, h * 1.5, function (r) {
      var L = [
        { path: P.rrect(-w * 0.62, -h * 0.16, w * 1.24, h * 0.32, 5, r, 0.6), color: o.color || "#22272A", bb: { x: -w * 0.62, y: -h * 0.16, w: w * 1.24, h: h * 0.32 } },
        { path: P.rrect(-w / 2, -h / 2, w, h, 7, r, 0.9), color: o.color || "#22272A" },
        { path: P.ellipse(w * 0.24, 0, h * 0.27, h * 0.27, r), color: "#3A3F3C", bb: { x: w * 0.24 - h * 0.27, y: -h * 0.27, w: h * 0.54, h: h * 0.54 } },
      ];
      if (o.noHorn) L.push({ draw: function (x) { x.fillStyle = C.silver; x.beginPath(); x.arc(w * 0.24, 0, h * 0.09, 0, 7); x.fill(); x.fillStyle = "rgba(0,0,0,0.4)"; x.beginPath(); x.arc(w * 0.24, 0, h * 0.04, 0, 7); x.fill(); } });
      else L.push({ path: hornPath(w * 0.24, 0, h * 0.62, r), color: C.ivory, bb: { x: w * 0.24 - h * 0.6, y: -h * 0.6, w: h * 1.2, h: h * 1.2 } });
      L.push({ draw: function (x) { engrave(x, o.label || "SG90", -w * 0.42, h * 0.1, h * 0.26, "rgba(211,238,157,0.5)"); } });
      return L;
    });
  };
  function hornPath(cx, cy, R, r) {
    var p = new Path2D();
    P.capsule(cx - R, cy, cx + R, cy, R * 0.16, R * 0.12, p);
    P.capsule(cx, cy - R * 0.7, cx, cy + R * 0.7, R * 0.15, R * 0.12, p);
    p.addPath(P.ellipse(cx, cy, R * 0.26, R * 0.26, r));
    return p;
  }
  P.horn = function (s) {
    return P.part("horn-" + s, s * 2.1, s * 1.5, function (r) { return [{ path: hornPath(0, 0, s, r), color: C.ivory }]; });
  };
  P.dish = function (w) {
    return P.part("dish-" + w, w, w * 0.8, function (r) {
      return [{ path: P.ellipse(0, 0, w / 2, w * 0.4, r, 1.2), color: "#C9CFC3", opts: { sheen: 0.22 } },
        { path: P.ellipse(1, 2, w * 0.36, w * 0.27, r, 0.8), color: "#B7BEB1", bb: { x: -w * 0.36, y: -w * 0.27, w: w * 0.72, h: w * 0.54 }, opts: { occ: 0.25, rim: 0.2, lit: -0.1 } }];
    });
  };
  P.tile = function (w, label, color) {
    return P.part("tile-" + label + w, w, w * 0.82, function (r) {
      return [{ path: P.rrect(-w / 2, -w * 0.41, w, w * 0.82, 8, r, 0.9), color: color || "#8E9A8E" },
        { draw: function (x) {
          if (label === "GPS") { x.fillStyle = "#D8CFA9"; x.fillRect(-w * 0.26, -w * 0.28, w * 0.52, w * 0.4); x.fillStyle = "#B49A5E"; x.beginPath(); x.arc(0, -w * 0.08, w * 0.07, 0, 7); x.fill(); }
          else if (label === "COMPASS") { x.strokeStyle = "rgba(16,19,16,0.55)"; x.lineWidth = 2; x.beginPath(); x.arc(0, -w * 0.08, w * 0.2, 0, 7); x.stroke(); x.fillStyle = C.red; x.beginPath(); x.moveTo(0, -w * 0.26); x.lineTo(w * 0.04, -w * 0.08); x.lineTo(-w * 0.04, -w * 0.08); x.fill(); }
          else { x.fillStyle = "#1A1D1B"; x.fillRect(-w * 0.16, -w * 0.24, w * 0.32, w * 0.26); x.fillStyle = C.silver; x.beginPath(); x.arc(0, -w * 0.11, w * 0.05, 0, 7); x.fill(); }
        } }];
    });
  };
  /* Launcher box: arm switch, launch button, LED, buzzer. */
  P.launcherBox = function (w) {
    var h = w * 0.62;
    return P.part("launcher-" + w, w, h, function (r) {
      return [
        { path: P.rrect(-w / 2, -h / 2, w, h, 16, r, 1.5), color: "#8F988C" },
        { path: P.rrect(-w * 0.42, -h * 0.36, w * 0.84, h * 0.72, 10, r, 1.0), color: "#9AA396", bb: { x: -w * 0.42, y: -h * 0.36, w: w * 0.84, h: h * 0.72 }, opts: { occ: 0.25, rim: 0.2 } },
        { path: P.ellipse(w * 0.12, 0, w * 0.085, w * 0.085, r), color: C.copper, bb: { x: w * 0.035, y: -w * 0.085, w: w * 0.17, h: w * 0.17 }, opts: { sheen: 0.22 } },
        { path: P.ellipse(w * 0.36, h * 0.18, w * 0.05, w * 0.05, r), color: "#151816", bb: { x: w * 0.31, y: h * 0.18 - w * 0.05, w: w * 0.1, h: w * 0.1 } },
        { path: P.ellipse(-w * 0.26, 0, w * 0.075, w * 0.075, r), color: "#6E756C", bb: { x: -w * 0.335, y: -w * 0.075, w: w * 0.15, h: w * 0.15 } },
        { draw: function (x) {
          x.fillStyle = "rgba(0,0,0,0.6)"; x.beginPath(); x.arc(w * 0.36, h * 0.18, w * 0.012, 0, 7); x.fill();
          engrave(x, "LAUNCHER ESP32", -w * 0.4, h * 0.42, h * 0.08, "rgba(16,19,16,0.55)");
        } },
      ];
    });
  };
  /* Dynamic bits of the launcher: arm lever (armed 0..1), LED (0..1). */
  P.launcherLive = function (ctx, x, y, w, armed, led) {
    var h = w * 0.62, lx = x - w * 0.26, ly = y, a = lerp(0.9, -0.9, armed);
    P.wire(ctx, [[lx, ly], [lx + Math.sin(a) * 4, ly - Math.cos(a) * 10], [lx + Math.sin(a) * 16, ly - Math.cos(a) * 26], [lx + Math.sin(a) * 30, ly - Math.cos(a) * 46]], "#D9DCD5", 11, "lever");
    var gx = x + w * 0.36, gy = y - h * 0.2;
    ctx.save();
    if (led > 0) {
      var g = ctx.createRadialGradient(gx, gy, 2, gx, gy, 44); g.addColorStop(0, "rgba(211,238,157," + 0.8 * led + ")"); g.addColorStop(1, "rgba(211,238,157,0)");
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(gx, gy, 44, 0, 7); ctx.fill();
    }
    var rg = ctx.createRadialGradient(gx - 4, gy - 4, 1, gx, gy, 14);
    rg.addColorStop(0, led > 0 ? "#F7FFE6" : "#9AA48C"); rg.addColorStop(1, led > 0 ? "#BFE27A" : "#4E5649");
    ctx.fillStyle = rg; ctx.beginPath(); ctx.arc(gx, gy, 13, 0, 7); ctx.fill();
    ctx.restore();
  };

  /* Laptop seen from above and in front; screen drawn live via onScreen. */
  P.laptop = function (w) {
    var h = w * 0.98;
    return P.part("laptop-" + w, w, h, function (r) {
      var L = [
        { path: P.rrect(-w / 2, -h / 2, w, h * 0.56, 14, r, 1.4), color: "#2B302D", bb: { x: -w / 2, y: -h / 2, w: w, h: h * 0.56 } },
        { path: P.rrect(-w / 2 - 6, h * 0.06, w + 12, h * 0.44, [10, 10, 24, 24], r, 1.6), color: "#A5ADA2", bb: { x: -w / 2, y: h * 0.06, w: w, h: h * 0.44 } },
        { flat: true, path: P.rrect(-w * 0.465, -h * 0.47, w * 0.93, h * 0.5, 6), color: "#0E1311" },
      ];
      L.push({ draw: function (x) {
        for (var row = 0; row < 4; row++) for (var k = 0; k < 13; k++) {
          var kx = -w * 0.43 + k * w * 0.066, ky = h * 0.1 + row * h * 0.052, kw = w * 0.054, kh = h * 0.04;
          x.fillStyle = "#8C9489"; x.beginPath(); x.roundRect(kx, ky, kw, kh, 3); x.fill();
          x.fillStyle = "rgba(255,255,255,0.18)"; x.fillRect(kx + 2, ky + 1, kw - 4, 2);
        }
        x.fillStyle = "#8C9489"; x.beginPath(); x.roundRect(-w * 0.24, h * 0.32, w * 0.48, h * 0.04, 3); x.fill();
        x.fillStyle = "#97A094"; x.beginPath(); x.roundRect(-w * 0.13, h * 0.385, w * 0.26, h * 0.09, 6); x.fill();
        x.strokeStyle = "rgba(0,0,0,0.25)"; x.lineWidth = 1.5; x.stroke();
      } });
      return L;
    });
  };
  P.laptopScreen = function (w) { var h = w * 0.98; return { x: -w * 0.465, y: -h * 0.47, w: w * 0.93, h: h * 0.5 }; };

  /* ---------- placards, labels, stationery ---------- */
  var PLAC = { WARNING: C.red, CAUTION: C.mustard, NOTE: C.ink };
  P.placard = function (kind, text, w) {
    var lines = P.wrap(text, Math.floor((w - 40) / 11.4)), h = 58 + lines.length * 24 + 34;
    return P.part("plac-" + kind + text.slice(0, 20) + w, w, h, function (r) {
      return [
        { path: P.rrect(-w * 0.28, h * 0.32, w * 0.56, h * 0.2, 6, r, 1), color: "#2A2F2B", bb: { x: -w * 0.28, y: h * 0.32, w: w * 0.56, h: h * 0.2 } },
        { path: P.rrect(-w / 2, -h / 2, w, h * 0.86, 10, r, 1.2), color: C.ivory, bb: { x: -w / 2, y: -h / 2, w: w, h: h * 0.86 }, opts: { lit: 0.12, occ: 0.3 } },
        { draw: function (x) {
          var c = PLAC[kind];
          x.strokeStyle = c; x.lineWidth = kind === "NOTE" ? 2 : 7;
          if (kind === "NOTE") { x.beginPath(); x.moveTo(-w / 2 + 16, -h / 2 + 46); x.lineTo(w / 2 - 16, -h / 2 + 46); x.stroke(); }
          else { x.beginPath(); x.roundRect(-w / 2 + 9, -h / 2 + 9, w - 18, h * 0.86 - 18, 6); x.stroke(); }
          P.font(x, P.FONT.monoB, 22); x.textAlign = "center"; x.fillStyle = kind === "NOTE" ? C.ink : c;
          x.fillText(kind, 0, -h / 2 + 38); x.textAlign = "left";
          lines.forEach(function (l, i) { P.type(x, l, -l.length * 11.4 / 2, -h / 2 + 72 + i * 24, 19, { seed: i * 99 }); });
        } },
      ];
    });
  };
  P.tape = function (ctx, x, y, text, o) {
    o = o || {};
    var size = o.size || 18, w = o.w || text.length * size * 0.6 + 26, h = size * 1.55, r = P.rng(P.hashStr(text) + 3);
    ctx.save(); ctx.translate(x, y); ctx.rotate(o.rot || (P.hash(P.hashStr(text)) - 0.5) * 0.06);
    var p = new Path2D(); p.moveTo(-w / 2, -h / 2);
    for (var i = 0; i <= 5; i++) p.lineTo(-w / 2 + i * w / 5, -h / 2 + (i % 2) * 1.5);
    for (i = 0; i <= 6; i++) p.lineTo(w / 2 + (i % 2 ? 3 : -1), -h / 2 + i * h / 6);
    for (i = 0; i <= 5; i++) p.lineTo(w / 2 - i * w / 5, h / 2 - (i % 2) * 1.5);
    for (i = 0; i <= 6; i++) p.lineTo(-w / 2 + (i % 2 ? -3 : 1), h / 2 - i * h / 6);
    ctx.shadowColor = "rgba(0,0,0,0.25)"; ctx.shadowBlur = 4; ctx.shadowOffsetX = 1.5; ctx.shadowOffsetY = 2;
    ctx.fillStyle = o.color || "rgba(232,221,188,0.96)"; ctx.fill(p); ctx.shadowColor = "transparent";
    ctx.fillStyle = "rgba(255,255,255,0.18)"; ctx.fillRect(-w / 2, -h / 2, w, 3);
    P.type(ctx, text, -text.length * size * 0.3, size * 0.35, size, { color: o.ink || C.ink, seed: P.hashStr(text) % 999 });
    ctx.restore();
  };
  P.pencil = function (L) {
    var d = L * 0.075;
    return P.part("pencil-" + L, L, d * 1.6, function (r) {
      var x0 = -L / 2;
      return [
        { path: P.rrect(x0 + L * 0.13, -d / 2, L * 0.72, d, 3, r, 0.4), color: C.sage, bb: { x: x0, y: -d / 2, w: L, h: d } },
        { path: P.rrect(x0 + L * 0.07, -d * 0.53, L * 0.08, d * 1.06, 2, r, 0.3), color: C.copper, bb: { x: x0 + L * 0.07, y: -d / 2, w: L * 0.08, h: d } },
        { path: P.rrect(x0, -d * 0.5, L * 0.08, d, d * 0.4, r, 0.4), color: C.lime, bb: { x: x0, y: -d / 2, w: L * 0.08, h: d } },
        { path: P.blob([[L * 0.35, -d / 2], [L * 0.47, -d * 0.1], [L * 0.47, d * 0.1], [L * 0.35, d / 2]], r, 0.3), color: "#D9B98C", bb: { x: L * 0.35, y: -d / 2, w: L * 0.12, h: d } },
        { draw: function (x) {
          x.fillStyle = C.graphite; x.beginPath(); x.moveTo(L * 0.44, -d * 0.16); x.lineTo(L / 2, 0); x.lineTo(L * 0.44, d * 0.16); x.fill();
          x.strokeStyle = "rgba(255,255,255,0.18)"; x.lineWidth = 1.5; x.beginPath(); x.moveTo(x0 + L * 0.14, -d * 0.18); x.lineTo(L * 0.34, -d * 0.18); x.stroke();
          x.strokeStyle = "rgba(0,0,0,0.12)"; x.beginPath(); x.moveTo(x0 + L * 0.14, d * 0.2); x.lineTo(L * 0.34, d * 0.2); x.stroke();
        } },
      ];
    });
  };
  /* Pencil held in a pinch; (tx, ty) is the graphite tip. */
  P.pencilInHand = function (ctx, tx, ty, o) {
    o = o || {};
    var L = o.L || 250, ang = o.ang === undefined ? -2.4 : o.ang, ca = Math.cos(ang), sa = Math.sin(ang);
    var cx = tx - ca * L / 2, cy = ty - sa * L / 2, sc = o.scale || 0.85;
    P.pencil(L).draw(ctx, cx, cy, { rot: ang, lift: o.lift || 6, key: "p" });
    // grip a third of the way up: fingertips at the grip, wrist further back along the pencil
    var gx = tx - ca * L * 0.3, gy = ty - sa * L * 0.3, back = 150 * sc * 1.25, side = 150 * sc * 0.18;
    P.hand(ctx, { x: gx - ca * back - sa * side, y: gy - sa * back + ca * side, rot: ang + Math.PI / 2, pose: "pinch", scale: sc, id: "pencilhand", lift: 30 });
  };
  /* Rubber stamp from above: dark base with a teal rubber edge peeking out,
   * a turned wooden handle and a knob. */
  P.stamp = function (s, label) {
    return P.part("stamp-" + s + (label || ""), s, s * 0.7, function (r) {
      return [
        { path: P.rrect(-s * 0.52, -s * 0.33, s * 1.04, s * 0.66, 10, r, 1), color: C.teal, opts: { occ: 0.3, sheen: 0.05 } },
        { path: P.rrect(-s / 2, -s * 0.35, s, s * 0.6, 10, r, 1), color: "#2B3130", bb: { x: -s / 2, y: -s * 0.35, w: s, h: s * 0.6 } },
        { path: P.ellipse(0, -s * 0.06, s * 0.2, s * 0.17, r, 1), color: "#8E5E3E", bb: { x: -s * 0.2, y: -s * 0.23, w: s * 0.4, h: s * 0.34 }, opts: { sheen: 0.18 } },
        { path: P.ellipse(-s * 0.02, -s * 0.09, s * 0.12, s * 0.1, r, 0.6), color: C.copper, bb: { x: -s * 0.14, y: -s * 0.19, w: s * 0.24, h: s * 0.2 }, opts: { sheen: 0.32 } },
        { draw: function (x) { if (label) P.tape(x, 0, s * 0.16, label, { size: Math.max(14, s * 0.085) }); } },
      ];
    });
  };
  /* The impression a stamp leaves: boxed, slightly broken ink. */
  P.inkStamp = function (ctx, x, y, lines, o) {
    o = o || {};
    var size = o.size || 26, w = o.w || Math.max.apply(null, lines.map(function (l) { return l.length; })) * size * 0.62 + 40, h = lines.length * size * 1.25 + 26;
    ctx.save(); ctx.translate(x, y); ctx.rotate(o.rot || -0.04); ctx.globalAlpha = o.alpha === undefined ? 0.88 : o.alpha;
    var col = o.color || C.teal;
    ctx.strokeStyle = col; ctx.lineWidth = 4.5; ctx.beginPath(); ctx.roundRect(-w / 2, -h / 2, w, h, 6); ctx.stroke();
    ctx.lineWidth = 1.5; ctx.beginPath(); ctx.roundRect(-w / 2 + 7, -h / 2 + 7, w - 14, h - 14, 4); ctx.stroke();
    P.font(ctx, P.FONT.monoB, size); ctx.fillStyle = col; ctx.textAlign = "center";
    lines.forEach(function (l, i) { ctx.fillText(l, 0, -h / 2 + 13 + size * 1.02 + i * size * 1.25); });
    ctx.textAlign = "left";
    // broken ink: knock out speckles with the paper colour
    var r = P.rng(P.hashStr(lines[0]) + 4);
    ctx.globalCompositeOperation = "destination-out";
    for (var i = 0; i < 160; i++) { ctx.globalAlpha = 0.4 + r() * 0.5; ctx.beginPath(); ctx.arc((r() - 0.5) * w, (r() - 0.5) * h, 0.6 + r() * 2.2, 0, 7); ctx.fill(); }
    ctx.restore();
  };
  /* A pencil mark that draws itself: pts, progress 0..1 */
  P.pencilLine = function (ctx, pts, prog, o) {
    o = o || {};
    if (prog <= 0) return;
    var n = Math.max(2, Math.floor(pts.length * prog));
    ctx.save(); ctx.lineCap = "round"; ctx.lineJoin = "round";
    ctx.strokeStyle = o.color || "rgba(55,58,54,0.85)"; ctx.lineWidth = o.width || 3;
    ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]);
    for (var i = 1; i < n; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    ctx.stroke();
    ctx.globalAlpha = 0.35; ctx.lineWidth = (o.width || 3) * 0.5; ctx.translate(0.8, 0.6); ctx.stroke();
    ctx.restore();
  };
  P.ellipsePts = function (cx, cy, rx, ry, turns, seed) {
    var r = P.rng(seed || 7), pts = [], N = Math.floor(60 * turns);
    for (var i = 0; i <= N; i++) { var a = -2.4 + (i / 60) * Math.PI * 2, k = 1 + (r() - 0.5) * 0.03 + i * 0.0006; pts.push([cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k]); }
    return pts;
  };
  P.tick = function (ctx, x, y, prog, s) {
    s = s || 1;
    var pts = [[x - 12 * s, y - 2 * s], [x - 7 * s, y + 4 * s], [x - 3 * s, y + 10 * s], [x + 5 * s, y - 4 * s], [x + 13 * s, y - 16 * s], [x + 20 * s, y - 24 * s]];
    var dense = [];
    for (var i = 0; i < pts.length - 1; i++) for (var k = 0; k < 4; k++) dense.push([lerp(pts[i][0], pts[i + 1][0], k / 4), lerp(pts[i][1], pts[i + 1][1], k / 4)]);
    dense.push(pts[pts.length - 1]);
    P.pencilLine(ctx, dense, prog, { width: 4 * s });
  };

  /* ---------- binder, dividers ---------- */
  P.ring = function (ctx, x, y, open) {
    ctx.save(); ctx.translate(x, y); ctx.scale(2, 1.25); ctx.translate(-x, -y);
    ctx.save();
    ctx.lineCap = "round";
    ctx.strokeStyle = "rgba(20,10,0,0.3)"; ctx.lineWidth = 15; ctx.filter = "blur(3px)";
    ctx.beginPath(); ctx.ellipse(x + 6, y + 8, 32, 12, 0, Math.PI * (open ? 1.15 : 0), Math.PI * (open ? 1.85 : 2)); ctx.stroke(); ctx.filter = "none";
    var g = ctx.createLinearGradient(x - 30, y - 14, x + 30, y + 14); g.addColorStop(0, "#F5F6F2"); g.addColorStop(0.5, "#A9ADA7"); g.addColorStop(1, "#5D615C");
    ctx.strokeStyle = g; ctx.lineWidth = 12;
    if (open) { ctx.beginPath(); ctx.ellipse(x - 6, y, 30, 12, 0, Math.PI * 0.55, Math.PI * 1.45); ctx.stroke(); ctx.beginPath(); ctx.ellipse(x + 6, y, 30, 12, 0, -Math.PI * 0.45, Math.PI * 0.45); ctx.stroke(); }
    else { ctx.beginPath(); ctx.ellipse(x, y, 32, 12, 0, 0, Math.PI * 2); ctx.stroke(); }
    ctx.strokeStyle = "rgba(255,255,255,0.6)"; ctx.lineWidth = 3; ctx.beginPath(); ctx.ellipse(x - 2, y - 3, 28, 9, 0, Math.PI * 1.1, Math.PI * 1.6); ctx.stroke();
    ctx.restore(); ctx.restore();
  };
  P.board = function (ctx, x, y, w, h, color) {
    var id = "board" + w + h + (color || "");
    P.part(id, w, h, function (r) {
      return [{ path: P.rrect(-w / 2, -h / 2, w, h, 18, r, 2), color: color || C.teal, opts: { tex: 0.7, occ: 0.35, sheen: 0.06 } }];
    }, { res: 0.75, pad: 30 }).draw(ctx, x + w / 2, y + h / 2, { jitterAmp: 0.3 });
  };

  /* ---------- the bench, seen from the front ---------- */
  var elevCache = {};
  P.elevationSet = function (W, H) {
    var key = W + "x" + H;
    if (elevCache[key]) return elevCache[key];
    var c = P.canvas(W, H), x = c.getContext("2d"), back = H * 0.6;
    var g = x.createLinearGradient(0, 0, 0, back);
    g.addColorStop(0, "#2A2722"); g.addColorStop(1, "#4A4239");
    x.fillStyle = g; x.fillRect(0, 0, W, back + 4);
    var n = P.noise2(5);
    x.globalAlpha = 0.25;
    for (var i = 0; i < 900; i++) { var px = (i * 97) % W, py = (i * 211) % back; x.fillStyle = n(px / 50, py / 50) > 0.5 ? "#5A5045" : "#24201B"; x.fillRect(px, py, 2, 2); }
    x.globalAlpha = 1;
    // pegboard holes on the wall
    x.fillStyle = "rgba(10,8,6,0.35)";
    for (var hy = 40; hy < back - 60; hy += 52) for (var hx = 26 + (hy % 104 ? 26 : 0); hx < W; hx += 52) { x.beginPath(); x.arc(hx, hy, 4, 0, 7); x.fill(); }
    // table top in perspective, sampled from the mat texture row by row
    var mat = P.matTexture(), vx = W / 2, vy = -H * 0.9;
    for (var y = back; y < H; y++) {
      var depth = (y - vy) / (H - vy), z = 1 / depth, rowW = W * 1.25 / (z * 0.75);
      var sy = (mat.height * 0.85) * (1 - (y - back) / (H - back)) + 40;
      x.drawImage(mat, mat.width / 2 - rowW / 2, sy, rowW, 1.5, vx - W * 0.85 / (z * 0.78) - 40, y, W * 1.7 / (z * 0.78) + 80, 1.5);
    }
    var tg = x.createLinearGradient(0, back, 0, back + 40); tg.addColorStop(0, "rgba(0,0,0,0.55)"); tg.addColorStop(1, "rgba(0,0,0,0)");
    x.fillStyle = tg; x.fillRect(0, back, W, 40);
    elevCache[key] = c;
    return c;
  };
  P.deskLamp = function (ctx, x, y, s, on) {
    // base on the table, arm, shade pointing down-right
    var lamp = P.part("desklamp" + s, s * 2.4, s * 2.6, function (r) {
      var L = [];
      L.push({ path: P.ellipse(-s * 0.6, s * 1.15, s * 0.55, s * 0.16, r), color: "#22272A", bb: { x: -s * 1.15, y: s, w: s * 1.1, h: s * 0.32 } });
      var arm = new Path2D(); P.capsule(-s * 0.6, s * 1.1, -s * 0.35, -s * 0.2, s * 0.06, s * 0.06, arm); P.capsule(-s * 0.35, -s * 0.2, s * 0.35, -s * 0.85, s * 0.06, s * 0.055, arm);
      L.push({ path: arm, color: "#2E3433", bb: { x: -s * 0.7, y: -s, w: s * 1.2, h: s * 2.2 } });
      L.push({ path: P.ellipse(s * 0.33, -s * 0.86, s * 0.09, s * 0.09, r), color: "#2E3433", bb: { x: s * 0.24, y: -s * 0.95, w: s * 0.18, h: s * 0.18 } });
      L.push({ path: P.poly([[s * 0.26, -s * 0.99], [s * 0.44, -s * 0.99], [s * 0.94, -s * 0.44], [s * 0.6, -s * 0.16], [s * 0.22, -s * 0.8]], s * 0.06, r, s * 0.004), color: C.teal, bb: { x: s * 0.22, y: -s, w: s * 0.72, h: s * 0.84 }, opts: { sheen: 0.22 } });
      L.push({ path: P.ellipse(s * 0.76, -s * 0.31, s * 0.13, s * 0.06, r), color: "#063B40", bb: { x: s * 0.6, y: -s * 0.4, w: s * 0.3, h: s * 0.16 }, opts: { occ: 0.6 } });
      return L;
    }, { res: 1 });
    lamp.draw(ctx, x, y, { shadow: false, jitterAmp: 0.4 });
    if (on > 0) {
      ctx.save(); ctx.globalAlpha = on;
      var bx = x + s * 0.76, by = y - s * 0.3, g = ctx.createRadialGradient(bx, by, 2, bx, by, s * 0.35);
      g.addColorStop(0, "rgba(255,248,220,1)"); g.addColorStop(1, "rgba(255,230,170,0)");
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(bx, by, s * 0.35, 0, 7); ctx.fill();
      ctx.restore();
    }
  };

  /* ---------- Section V vignettes (front view) ---------- */
  // C1: the specified four-bar (ground 25, coupler 60, input 15, output 15 mm) cannot close.
  P.linkage = function (ctx, x, y, k, theta, o) {
    o = o || {};
    var A = [x, y], D = [x + 25 * k, y];
    var B = [A[0] + 15 * k * Math.cos(-theta), A[1] + 15 * k * Math.sin(-theta)];
    var C2 = [D[0] + 15 * k * Math.cos(-Math.PI / 2 - theta * 0.4), D[1] + 15 * k * Math.sin(-Math.PI / 2 - theta * 0.4)];
    var ang = Math.atan2(C2[1] - B[1], C2[0] - B[0]), E2 = [B[0] + Math.cos(ang) * 60 * k, B[1] + Math.sin(ang) * 60 * k];
    var plate = P.part("linkplate" + k, 70 * k, 52 * k, function (r) { return [{ path: P.rrect(-35 * k, -26 * k, 70 * k, 52 * k, 12, r, 1.5), color: "#8C958A", opts: { occ: 0.35 } }]; });
    plate.draw(ctx, x + 18 * k, y - 8 * k, { shadow: true });
    function bar(p, q, id, col) {
      P.wire(ctx, [p, [lerp(p[0], q[0], 0.33), lerp(p[1], q[1], 0.33)], [lerp(p[0], q[0], 0.66), lerp(p[1], q[1], 0.66)], q], col || C.copper, 3.4 * k, id);
    }
    bar(A, D, "lk-g", "#5C625B"); bar(A, B, "lk-in"); bar(D, C2, "lk-out"); bar(B, E2, "lk-c", "#C08A5E");
    [A, D, B, C2].forEach(function (p) { P.bead(ctx, p[0], p[1], C.silver, k * 0.32); });
    ctx.save(); ctx.strokeStyle = "rgba(16,19,16,0.75)"; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.arc(E2[0], E2[1], 2.2 * k, 0, 7); ctx.stroke(); ctx.restore();
    return { gap: Math.hypot(E2[0] - C2[0], E2[1] - C2[1]) / k, C: C2, E: E2 };
  };
  P.gauge = function (ctx, x, y, R, value) {
    var face = P.part("gaugeface" + R, R * 2.3, R * 2.3, function (r) {
      return [{ path: P.ellipse(0, 0, R * 1.12, R * 1.12, r, 1), color: C.sage }, { path: P.ellipse(0, 0, R, R, r, 0.5), color: C.ivory, bb: { x: -R, y: -R, w: 2 * R, h: 2 * R }, opts: { occ: 0.28, rim: 0.2, lit: 0.1 } }];
    });
    face.draw(ctx, x, y);
    function ang(v) { return Math.PI * (0.8 + (v / 30) * 1.4); }
    ctx.save();
    for (var v = 0; v <= 30; v++) {
      var a = ang(v), r0 = R * (v % 5 ? 0.82 : 0.74);
      ctx.strokeStyle = C.ink; ctx.lineWidth = v % 5 ? 1.5 : 3;
      ctx.beginPath(); ctx.moveTo(x + Math.cos(a) * r0, y + Math.sin(a) * r0); ctx.lineTo(x + Math.cos(a) * R * 0.9, y + Math.sin(a) * R * 0.9); ctx.stroke();
      if (v % 10 === 0) { P.font(ctx, P.FONT.cond, R * 0.16); ctx.fillStyle = C.ink; ctx.textAlign = "center"; ctx.fillText(v + "%", x + Math.cos(a) * R * 0.56, y + Math.sin(a) * R * 0.56 + R * 0.05); }
    }
    ctx.textAlign = "left";
    var a20 = ang(20);
    ctx.strokeStyle = C.mustard; ctx.lineWidth = 7; ctx.beginPath(); ctx.arc(x, y, R * 0.9, a20, ang(30)); ctx.stroke();
    ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(x + Math.cos(a20) * R * 0.6, y + Math.sin(a20) * R * 0.6); ctx.lineTo(x + Math.cos(a20) * R * 0.98, y + Math.sin(a20) * R * 0.98); ctx.stroke();
    ctx.restore();
    var na = ang(value);
    P.wire(ctx, [[x - Math.cos(na) * R * 0.12, y - Math.sin(na) * R * 0.12], [x, y], [x + Math.cos(na) * R * 0.4, y + Math.sin(na) * R * 0.4], [x + Math.cos(na) * R * 0.78, y + Math.sin(na) * R * 0.78]], "#22272A", R * 0.06, "needle");
    P.bead(ctx, x, y, C.copper, R * 0.012);
  };
  P.balance = function (ctx, x, y, s, tilt, id) {
    var post = P.part("balpost" + s, s * 0.5, s * 1.25, function (r) {
      return [{ path: P.rrect(-s * 0.2, s * 0.42, s * 0.4, s * 0.16, 6, r, 0.8), color: "#6F786D", bb: { x: -s * 0.2, y: s * 0.42, w: s * 0.4, h: s * 0.16 } },
        { path: P.rrect(-s * 0.035, -s * 0.5, s * 0.07, s * 0.95, 4, r, 0.4), color: "#7A8378", bb: { x: -s * 0.04, y: -s * 0.5, w: s * 0.08, h: s * 0.95 } }];
    });
    post.draw(ctx, x, y);
    var bx = s * 0.62, ca = Math.cos(tilt), sa = Math.sin(tilt), top = [x, y - s * 0.5];
    var L = [top[0] - bx * ca, top[1] - bx * sa], R2 = [top[0] + bx * ca, top[1] + bx * sa];
    P.wire(ctx, [L, [lerp(L[0], R2[0], 0.33), lerp(L[1], R2[1], 0.33)], [lerp(L[0], R2[0], 0.66), lerp(L[1], R2[1], 0.66)], R2], C.copper, s * 0.05, "beam" + id);
    P.bead(ctx, top[0], top[1], C.silver, s * 0.005);
    [L, R2].forEach(function (p, i) {
      ctx.strokeStyle = "rgba(30,30,28,0.6)"; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.lineTo(p[0] - s * 0.14, p[1] + s * 0.3); ctx.moveTo(p[0], p[1]); ctx.lineTo(p[0] + s * 0.14, p[1] + s * 0.3); ctx.stroke();
      P.part("pan" + s, s * 0.4, s * 0.12, function (r) { return [{ path: P.ellipse(0, 0, s * 0.2, s * 0.05, r, 0.5), color: C.sage }]; }).draw(ctx, p[0], p[1] + s * 0.31, { key: id + i });
      if (i === 0) P.rocket(s * 0.36).draw(ctx, p[0], p[1] + s * 0.25, { key: id, sx: 0.9 });
      else P.part("weight" + s, s * 0.16, s * 0.14, function (r) { return [{ path: P.rrect(-s * 0.08, -s * 0.07, s * 0.16, s * 0.14, 4, r, 0.5), color: "#5B605A" }]; }).draw(ctx, p[0], p[1] + s * 0.24, { key: id });
    });
  };
})();
