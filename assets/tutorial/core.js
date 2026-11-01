/* V3D-TO-33-1 claymation engine — core.
 * Canvas 2D only. Deterministic: every picture is a pure function of time t,
 * quantized to 12 drawings per second (animation on twos in a 24 fps film).
 * No network, no external fonts, no libraries. */
(function () {
  "use strict";
  var P = (window.P33T = window.P33T || {});

  /* ---------- palette ---------- */
  var C = (P.C = {
    teal: "#0B5D63", tealHi: "#2F8B8E", tealDeep: "#07383C",
    black: "#101310", ivory: "#EEEEE4", lime: "#D3EE9D", sage: "#A3AA9D",
    copper: "#A9714D", mustard: "#C79A2A", red: "#B23A2E",
    ink: "#1C201C", paper: "#ECEBE0", kraft: "#B48B5C",
    mat: "#24423A", skin: "#D6A27F", silver: "#C9CCC6", graphite: "#3E403D",
    felt: "#4F5E57",
  });

  /* ---------- math ---------- */
  var clamp = (P.clamp = function (x, a, b) { a = a === undefined ? 0 : a; b = b === undefined ? 1 : b; return x < a ? a : x > b ? b : x; });
  var lerp = (P.lerp = function (a, b, t) { return a + (b - a) * t; });
  var E = (P.ease = {
    lin: function (t) { return t; },
    io: function (t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; },
    out: function (t) { return 1 - Math.pow(1 - t, 3); },
    in: function (t) { return t * t * t; },
    back: function (t) { var s = 1.6; t -= 1; return 1 + (s + 1) * t * t * t + s * t * t; },
    settle: function (t) { return 1 - Math.exp(-6 * t) * Math.cos(t * 9.5); },
  });
  P.seg = function (t, a, b, ease) { return (ease || E.io)(clamp((t - a) / (b - a))); };
  P.hash = function (n) {
    n = (n ^ 61) ^ (n >>> 16); n = (n + (n << 3)) | 0; n ^= n >>> 4;
    n = Math.imul(n, 0x27d4eb2d); n ^= n >>> 15; return (n >>> 0) / 4294967296;
  };
  P.hashStr = function (s) {
    var h = 2166136261;
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  };
  P.rng = function (seed) {
    var a = seed >>> 0 || 1;
    return function () {
      a = (a + 0x6d2b79f5) | 0; var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };
  function noise2(seed) {
    var r = P.rng(seed), N = 256, g = new Float32Array(N * N);
    for (var i = 0; i < N * N; i++) g[i] = r();
    return function (x, y) {
      var xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
      var u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
      var x0 = xi & 255, y0 = yi & 255, x1 = (x0 + 1) & 255, y1 = (y0 + 1) & 255;
      var a = g[y0 * N + x0], b = g[y0 * N + x1], c = g[y1 * N + x0], d = g[y1 * N + x1];
      return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
    };
  }
  P.noise2 = noise2;
  function hexRgb(h) { var n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
  P.mix = function (a, b, t) {
    var x = hexRgb(a), y = hexRgb(b);
    return "rgb(" + Math.round(lerp(x[0], y[0], t)) + "," + Math.round(lerp(x[1], y[1], t)) + "," + Math.round(lerp(x[2], y[2], t)) + ")";
  };
  P.shade = function (h, f) { // f>0 lighten toward white, f<0 darken toward black
    return f >= 0 ? P.mix(h, "#ffffff", f) : P.mix(h, "#000000", -f);
  };

  /* ---------- the frame clock ---------- */
  var F = (P.F = { t: 0, drawing: 0 });
  P.setTime = function (t) {
    F.drawing = Math.floor(t * 12 + 1e-6);
    F.t = F.drawing / 12;
    return F.t;
  };
  P.variant = function (id) { return (F.drawing + (P.hashStr(id) % 3)) % 3; };
  P.jit = function (id, amp) {
    var h = P.hashStr(id) + F.drawing * 7919;
    return [(P.hash(h) - 0.5) * (amp || 0.7), (P.hash(h + 31) - 0.5) * (amp || 0.7)];
  };

  function canvas(w, h) {
    var c = document.createElement("canvas");
    c.width = Math.max(1, Math.ceil(w)); c.height = Math.max(1, Math.ceil(h));
    return c;
  }
  P.canvas = canvas;

  /* ---------- procedural textures (generated once) ---------- */
  var TEX = (P.TEX = {});
  function makeTextures() {
    var n1 = noise2(11), n2 = noise2(23), n3 = noise2(37);
    // clay surface: soft lumps, fine pits, tool drags; mid-grey for soft-light
    var S = 512, c = canvas(S, S), x = c.getContext("2d"), img = x.createImageData(S, S), d = img.data, r = P.rng(5);
    for (var j = 0; j < S; j++) for (var i = 0; i < S; i++) {
      var u = i / S, v = j / S;
      var lump = n1(u * 6, v * 6) * 0.55 + n1(u * 13, v * 13) * 0.3 + n2(u * 29, v * 29) * 0.15;
      var drag = n3(u * 3 + v * 22, v * 3) * 0.35;
      var pit = r() < 0.012 ? -0.35 * r() : 0;
      var val = 128 + (lump - 0.5) * 70 + (drag - 0.17) * 40 + pit * 255 + (r() - 0.5) * 10;
      var k = (j * S + i) * 4; d[k] = d[k + 1] = d[k + 2] = clamp(val, 0, 255); d[k + 3] = 255;
    }
    x.putImageData(img, 0, 0);
    // thumbprint ridges
    for (var p = 0; p < 9; p++) {
      var cx = r() * S, cy = r() * S, rr = 18 + r() * 26, rot = r() * Math.PI;
      for (var q = 0; q < 9; q++) {
        var rq = Math.max(1, rr - q * 2.4); x.beginPath(); x.ellipse(cx, cy, rq, rq * 0.72, rot, 0, Math.PI * 2);
        x.strokeStyle = q % 2 ? "rgba(255,255,255,0.10)" : "rgba(0,0,0,0.12)"; x.lineWidth = 1.1; x.stroke();
      }
    }
    TEX.clay = c;
    // paper: ivory fibres
    S = 1024; c = canvas(S, S); x = c.getContext("2d"); img = x.createImageData(S, S); d = img.data;
    for (j = 0; j < S; j++) for (i = 0; i < S; i++) {
      u = i / S; v = j / S;
      var f = n2(u * 40, v * 9) * 0.5 + n1(u * 120, v * 120) * 0.3 + n3(u * 8, v * 8) * 0.2;
      val = 236 + (f - 0.5) * 16 + (r() - 0.5) * 6;
      k = (j * S + i) * 4; d[k] = val; d[k + 1] = val - 1; d[k + 2] = val - 9; d[k + 3] = 255;
    }
    x.putImageData(img, 0, 0);
    for (p = 0; p < 140; p++) { x.fillStyle = "rgba(90,80,60," + (0.05 + r() * 0.12) + ")"; x.fillRect(r() * S, r() * S, 1 + r() * 1.6, 1 + r() * 1.6); }
    TEX.paper = c;
    // film grain: four frames, coarse (drawn at 2x), cycled per drawing
    TEX.grain = [];
    for (var g = 0; g < 4; g++) {
      c = canvas(480, 270); x = c.getContext("2d"); img = x.createImageData(480, 270); d = img.data; var rg = P.rng(100 + g);
      for (k = 0; k < d.length; k += 4) { var gv = 128 + (rg() + rg() + rg() - 1.5) * 70; d[k] = d[k + 1] = d[k + 2] = gv; d[k + 3] = 255; }
      x.putImageData(img, 0, 0); TEX.grain.push(c);
    }
  }

  /* ---------- fonts ---------- */
  P.FONT = { mono: "P33Mono", monoB: "P33MonoBold", cond: "P33Cond", condM: "P33CondMedium" };
  P.loadFonts = function () {
    var data = window.P33T_FONTS || {}, jobs = [];
    Object.keys(data).forEach(function (name) {
      try {
        var bin = atob(data[name]), buf = new Uint8Array(bin.length);
        for (var i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
        var face = new FontFace(name, buf.buffer);
        jobs.push(face.load().then(function (f) { document.fonts.add(f); }));
      } catch (e) { /* fall back to system fonts */ }
    });
    return Promise.all(jobs).catch(function () {});
  };
  P.fontStack = function (name) {
    if (name === "P33Cond" || name === "P33CondMedium") return '"' + name + '","Arial Narrow","Roboto Condensed",sans-serif';
    return '"' + name + '","Courier New","Nimbus Mono PS",Courier,monospace';
  };
  P.font = function (ctx, name, size) { ctx.font = size.toFixed(2) + "px " + P.fontStack(name); };

  /* ---------- clay shading ---------- */
  function totalScale(ctx) { var m = ctx.getTransform(); return Math.hypot(m.a, m.b); }
  function innerShadow(ctx, path, bb, dx, dy, blur, color) {
    var k = totalScale(ctx), BIG = 20000;
    ctx.save();
    ctx.clip(path);
    ctx.shadowColor = color; ctx.shadowBlur = blur * k;
    var m = ctx.getTransform();
    // offset the hole far away in device space and bring only its shadow back
    ctx.shadowOffsetX = BIG + dx * k; ctx.shadowOffsetY = dy * k;
    ctx.setTransform(1, 0, 0, 1, -BIG, 0);
    ctx.transform(m.a, m.b, m.c, m.d, m.e, m.f);
    var hole = new Path2D();
    hole.rect(bb.x - bb.w - 200, bb.y - bb.h - 200, bb.w * 3 + 400, bb.h * 3 + 400);
    hole.addPath(path);
    ctx.fillStyle = "#000";
    ctx.fill(hole, "evenodd");
    ctx.restore();
  }
  P.innerShadow = innerShadow;
  var patCache = new WeakMap();
  function clayPattern(ctx) {
    var p = patCache.get(ctx);
    if (!p) { p = ctx.createPattern(TEX.clay, "repeat"); patCache.set(ctx, p); }
    return p;
  }
  /* Fill a path as plasticine: base colour, lamp gradient, occlusion and rim,
   * thumb-worked texture, a matte sheen and a soft crease line. */
  P.clayFill = function (ctx, path, color, bb, o) {
    o = o || {};
    var s = Math.max(6, Math.min(bb.w, bb.h)), v = o.variant || 0;
    ctx.save();
    ctx.fillStyle = color; ctx.fill(path);
    ctx.save();
    ctx.clip(path);
    var g = ctx.createLinearGradient(bb.x, bb.y, bb.x + bb.w * 0.8, bb.y + bb.h);
    g.addColorStop(0, "rgba(255,243,222," + (o.lit === undefined ? 0.22 : o.lit) + ")");
    g.addColorStop(0.55, "rgba(255,255,255,0)");
    g.addColorStop(1, "rgba(30,14,0,0.26)");
    ctx.fillStyle = g; ctx.fillRect(bb.x, bb.y, bb.w, bb.h);
    var off = clamp(s * 0.09, 1.5, 14), blur = clamp(s * 0.22, 3, 34);
    innerShadow(ctx, path, bb, -off, -off * 1.15, blur, "rgba(40,20,4," + (o.occ || 0.5) + ")");
    innerShadow(ctx, path, bb, off * 0.8, off * 0.9, blur * 0.8, "rgba(255,250,238," + (o.rim || 0.34) + ")");
    var pat = clayPattern(ctx);
    if (pat && pat.setTransform) {
      var m = new DOMMatrix();
      var sc = o.texScale || clamp(s / 220, 0.35, 1.4);
      m.translateSelf(bb.x + v * 97 + (P.hashStr(o.id || "x") % 300), bb.y + v * 53).scaleSelf(sc, sc);
      pat.setTransform(m);
    }
    ctx.globalCompositeOperation = "soft-light";
    ctx.globalAlpha = o.tex === undefined ? 0.95 : o.tex;
    ctx.fillStyle = pat; ctx.fillRect(bb.x, bb.y, bb.w, bb.h);
    ctx.globalCompositeOperation = "source-over"; ctx.globalAlpha = 1;
    var rg = ctx.createRadialGradient(bb.x + bb.w * 0.32, bb.y + bb.h * 0.26, 0, bb.x + bb.w * 0.32, bb.y + bb.h * 0.26, s * 0.6);
    rg.addColorStop(0, "rgba(255,255,250," + (o.sheen === undefined ? 0.12 : o.sheen) + ")"); rg.addColorStop(1, "rgba(255,255,250,0)");
    ctx.fillStyle = rg; ctx.fillRect(bb.x, bb.y, bb.w, bb.h);
    ctx.restore();
    ctx.strokeStyle = "rgba(25,12,0," + (o.edge === undefined ? 0.22 : o.edge) + ")"; ctx.lineWidth = o.edgeW || 1.1;
    ctx.stroke(path);
    ctx.restore();
  };

  /* Sprite parts: a clay object rendered once per boil variant (3), cached,
   * then drawn with transforms. build(r, v) returns [{path, color, bb, opts}]
   * in local coordinates centred on the part. */
  var parts = {};
  P.part = function (id, w, h, build, opt) {
    opt = opt || {};
    if (parts[id]) return parts[id];
    var pad = opt.pad === undefined ? Math.max(12, Math.min(w, h) * 0.12) : opt.pad;
    var res = opt.res || 1.5, sprites = [], shadow = null;
    function sprite(v) {
      if (sprites[v]) return sprites[v];
      var c = canvas((w + pad * 2) * res, (h + pad * 2) * res), x = c.getContext("2d");
      x.scale(res, res); x.translate(pad + w / 2, pad + h / 2);
      var layers = build(P.rng(P.hashStr(id) + v * 7717), v, x);
      layers.forEach(function (L) {
        if (L.draw) { L.draw(x); return; }
        if (L.flat) { x.fillStyle = L.color; x.fill(L.path); return; }
        P.clayFill(x, L.path, L.color, L.bb || { x: -w / 2, y: -h / 2, w: w, h: h }, Object.assign({ variant: v, id: id }, L.opts || {}));
      });
      sprites[v] = { c: c, res: res, pad: pad, w: w, h: h, layers: layers };
      return sprites[v];
    }
    function shadowSprite() {
      if (shadow) return shadow;
      var s0 = sprite(0), blur = Math.max(4, Math.min(w, h) * 0.08);
      var c = canvas(s0.c.width + blur * 4 * res, s0.c.height + blur * 4 * res), x = c.getContext("2d");
      x.filter = "blur(" + (blur * res).toFixed(1) + "px)";
      x.drawImage(s0.c, blur * 2 * res, blur * 2 * res);
      x.filter = "none"; x.globalCompositeOperation = "source-in"; x.fillStyle = "#1a0f05"; x.fillRect(0, 0, c.width, c.height);
      shadow = { c: c, extra: blur * 2 };
      return shadow;
    }
    var api = {
      id: id, w: w, h: h,
      sprite: sprite,
      /* o: {rot, sx, sy, alpha, lift (0 = resting), shadow (true), jitter} */
      draw: function (ctx, cx, cy, o) {
        o = o || {};
        var v = o.variant === undefined ? P.variant(id) : o.variant, s = sprite(v);
        var j = o.jitter === false ? [0, 0] : P.jit(id + (o.key || ""), o.jitterAmp || 0.8);
        var rot = o.rot || 0, sx = o.sx === undefined ? 1 : o.sx, sy = o.sy === undefined ? sx : o.sy;
        if (o.shadow !== false) {
          var sh = shadowSprite(), lift = o.lift || 0;
          ctx.save();
          ctx.globalAlpha = (o.alpha === undefined ? 1 : o.alpha) * (o.shadowAlpha || 0.42) * (1 - clamp(lift / 160) * 0.55);
          ctx.translate(cx + 3 + lift * 0.35 + j[0], cy + 5 + lift * 0.45 + j[1]);
          ctx.rotate(rot); ctx.scale(sx * (1 + lift * 0.0008), sy * (1 + lift * 0.0008));
          ctx.drawImage(sh.c, -(w / 2 + pad + sh.extra), -(h / 2 + pad + sh.extra), sh.c.width / res, sh.c.height / res);
          ctx.restore();
        }
        ctx.save();
        if (o.alpha !== undefined) ctx.globalAlpha = o.alpha;
        ctx.translate(cx + j[0], cy + j[1]); ctx.rotate(rot); ctx.scale(sx, sy);
        ctx.drawImage(s.c, -(w / 2 + pad), -(h / 2 + pad), s.c.width / res, s.c.height / res);
        ctx.restore();
      },
    };
    parts[id] = api;
    return api;
  };

  /* ---------- path helpers ---------- */
  P.wob = function (r, a) { return (r() - 0.5) * 2 * (a || 1); };
  P.rrect = function (x, y, w, h, rad, r, wob) {
    var p = new Path2D(), k = wob || 0, R = typeof rad === "number" ? [rad, rad, rad, rad] : rad;
    function q() { return r ? P.wob(r, k) : 0; }
    p.moveTo(x + R[0] + q(), y + q());
    p.lineTo(x + w - R[1] + q(), y + q());
    p.quadraticCurveTo(x + w + q(), y + q(), x + w + q(), y + R[1] + q());
    p.lineTo(x + w + q(), y + h - R[2] + q());
    p.quadraticCurveTo(x + w + q(), y + h + q(), x + w - R[2] + q(), y + h + q());
    p.lineTo(x + R[3] + q(), y + h + q());
    p.quadraticCurveTo(x + q(), y + h + q(), x + q(), y + h - R[3] + q());
    p.lineTo(x + q(), y + R[0] + q());
    p.quadraticCurveTo(x + q(), y + q(), x + R[0] + q(), y + q());
    p.closePath();
    return p;
  };
  /* smooth closed blob through points (Catmull-Rom) */
  P.blob = function (pts, r, wob) {
    var p = new Path2D(), n = pts.length, q = pts.map(function (a) { return [a[0] + (r ? P.wob(r, wob || 0) : 0), a[1] + (r ? P.wob(r, wob || 0) : 0)]; });
    // one winding direction everywhere (the same as capsules), so unions never cancel into holes
    var area = 0;
    for (var s = 0; s < n; s++) area += q[s][0] * q[(s + 1) % n][1] - q[(s + 1) % n][0] * q[s][1];
    if (area > 0) q.reverse();
    p.moveTo(q[0][0], q[0][1]);
    for (var i = 0; i < n; i++) {
      var p0 = q[(i - 1 + n) % n], p1 = q[i], p2 = q[(i + 1) % n], p3 = q[(i + 2) % n];
      p.bezierCurveTo(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6, p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, p2[0], p2[1]);
    }
    p.closePath();
    return p;
  };
  /* Polygon with softly rounded corners (keeps straight edges straight). */
  P.poly = function (pts, rad, r, wob) {
    var q = pts.map(function (a) { return [a[0] + (r ? P.wob(r, wob || 0) : 0), a[1] + (r ? P.wob(r, wob || 0) : 0)]; });
    var area = 0, n = q.length, i;
    for (i = 0; i < n; i++) area += q[i][0] * q[(i + 1) % n][1] - q[(i + 1) % n][0] * q[i][1];
    if (area > 0) q.reverse();
    var p = new Path2D(), m0 = [(q[n - 1][0] + q[0][0]) / 2, (q[n - 1][1] + q[0][1]) / 2];
    p.moveTo(m0[0], m0[1]);
    for (i = 0; i < n; i++) { var a = q[i], b = q[(i + 1) % n]; p.arcTo(a[0], a[1], (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, rad); }
    p.closePath();
    return p;
  };
  /* Place a hand so that its index fingertip lands on (tx, ty). */
  P.handTo = function (ctx, tx, ty, h) {
    var s = (h.scale || 1) * 150, m = h.mirror ? -1 : 1, rot = h.rot || 0;
    var lx = -0.263 * s * m, ly = -1.348 * s, c = Math.cos(rot), sn = Math.sin(rot);
    return P.hand(ctx, Object.assign({}, h, { pose: h.pose || "point", x: tx - (lx * c - ly * sn), y: ty - (lx * sn + ly * c) }));
  };
  P.capsule = function (x0, y0, x1, y1, r0, r1, path) {
    var p = path || new Path2D(), a = Math.atan2(y1 - y0, x1 - x0), n = a + Math.PI / 2;
    r1 = r1 === undefined ? r0 : r1;
    p.moveTo(x0 + Math.cos(n) * r0, y0 + Math.sin(n) * r0);
    p.lineTo(x1 + Math.cos(n) * r1, y1 + Math.sin(n) * r1);
    p.arc(x1, y1, r1, n, n - Math.PI, true);
    p.lineTo(x0 - Math.cos(n) * r0, y0 - Math.sin(n) * r0);
    p.arc(x0, y0, r0, n + Math.PI, n, true);
    p.closePath();
    return p;
  };
  P.ellipse = function (x, y, rx, ry, r, wob) {
    var pts = [], n = 10;
    for (var i = 0; i < n; i++) { var a = (i / n) * Math.PI * 2; pts.push([x + Math.cos(a) * rx, y + Math.sin(a) * ry]); }
    return P.blob(pts, r, wob === undefined ? Math.min(rx, ry) * 0.04 : wob);
  };

  /* ---------- clay snakes (wires) ---------- */
  P.bez = function (p, t) {
    var u = 1 - t;
    return [u * u * u * p[0][0] + 3 * u * u * t * p[1][0] + 3 * u * t * t * p[2][0] + t * t * t * p[3][0],
      u * u * u * p[0][1] + 3 * u * u * t * p[1][1] + 3 * u * t * t * p[2][1] + t * t * t * p[3][1]];
  };
  P.wire = function (ctx, pts, color, width, id) {
    var j = P.jit(id || "wire", 0.6);
    ctx.save(); ctx.translate(j[0], j[1]); ctx.lineCap = "round"; ctx.lineJoin = "round";
    function path(dx, dy) { ctx.beginPath(); ctx.moveTo(pts[0][0] + dx, pts[0][1] + dy); ctx.bezierCurveTo(pts[1][0] + dx, pts[1][1] + dy, pts[2][0] + dx, pts[2][1] + dy, pts[3][0] + dx, pts[3][1] + dy); }
    path(4, 6); ctx.strokeStyle = "rgba(20,10,0,0.28)"; ctx.lineWidth = width * 1.05; ctx.filter = "blur(3px)"; ctx.stroke(); ctx.filter = "none";
    path(0, 0); ctx.strokeStyle = P.shade(color, -0.35); ctx.lineWidth = width; ctx.stroke();
    path(-width * 0.08, -width * 0.1); ctx.strokeStyle = color; ctx.lineWidth = width * 0.8; ctx.stroke();
    path(-width * 0.2, -width * 0.24); ctx.strokeStyle = P.shade(color, 0.3); ctx.lineWidth = width * 0.3; ctx.globalAlpha = 0.55; ctx.stroke();
    ctx.globalAlpha = 1;
    // rolled-clay unevenness: soft bumps along the snake
    var r = P.rng(P.hashStr(id || "w") + P.variant(id || "w"));
    for (var i = 1; i < 14; i++) {
      var q = P.bez(pts, i / 14);
      ctx.fillStyle = "rgba(255,245,230," + (0.06 + r() * 0.06) + ")";
      ctx.beginPath(); ctx.ellipse(q[0] - width * 0.15, q[1] - width * 0.15, width * 0.25, width * 0.18, r() * 3, 0, 7); ctx.fill();
    }
    ctx.restore();
  };
  var beadPart = function (color) {
    return P.part("bead-" + color, 18, 18, function (r) {
      return [{ path: P.ellipse(0, 0, 8.4, 8.2, r, 0.3), color: color, opts: { occ: 0.45, rim: 0.4, sheen: 0.25 } }];
    }, { pad: 8 });
  };
  P.bead = function (ctx, x, y, color, scale) { beadPart(color || C.lime).draw(ctx, x, y, { sx: scale || 1, key: x.toFixed(0) }); };

  /* ---------- typewriter text ---------- */
  P.cw = function (size) { return size * 0.6; };
  /* Draw a string one character at a time with typewriter irregularity. */
  P.type = function (ctx, str, x, y, size, o) {
    o = o || {};
    var font = o.bold ? P.FONT.monoB : P.FONT.mono, cw = size * 0.6, n = Math.min(str.length, o.upto === undefined ? 1e9 : o.upto);
    P.font(ctx, font, size);
    ctx.textBaseline = "alphabetic";
    var col = o.color || C.ink, seed = o.seed || 0, a0 = o.alpha === undefined ? 1 : o.alpha;
    ctx.fillStyle = col;
    for (var i = 0; i < n; i++) {
      var ch = str[i];
      if (ch === " ") continue;
      var h = seed + i * 131 + ch.charCodeAt(0) * 7;
      ctx.globalAlpha = a0 * (0.8 + P.hash(h) * 0.2);
      ctx.fillText(ch, x + i * cw + (P.hash(h + 1) - 0.5) * size * 0.03, y + (P.hash(h + 2) - 0.5) * size * 0.05);
    }
    ctx.globalAlpha = 1;
    return n * cw;
  };
  P.cond = function (ctx, str, x, y, size, o) {
    o = o || {};
    P.font(ctx, o.medium ? P.FONT.condM : P.FONT.cond, size);
    ctx.fillStyle = o.color || C.ink; ctx.textBaseline = "alphabetic";
    if (o.track) { try { ctx.letterSpacing = o.track + "px"; } catch (e) {} }
    ctx.textAlign = o.align || "left";
    ctx.fillText(str, x, y);
    ctx.textAlign = "left";
    if (o.track) { try { ctx.letterSpacing = "0px"; } catch (e) {} }
    return ctx.measureText(str).width;
  };

  /* ---------- typesetting a manual page ---------- */
  function wrap(text, width) {
    var words = text.split(" "), lines = [], cur = "";
    words.forEach(function (w) {
      if (!cur.length) cur = w;
      else if ((cur + " " + w).length <= width) cur += " " + w;
      else { lines.push(cur); cur = w; }
    });
    if (cur.length) lines.push(cur);
    return lines;
  }
  P.wrap = wrap;
  /* Returns rows: [{segs:[{col,text,style}], block, kind, box}] and block row spans. */
  P.layout = function (blocks, measure) {
    var rows = [], spans = {}, i;
    function push(row) { rows.push(row); return rows.length - 1; }
    var cmdCol = 0;
    blocks.forEach(function (b) { if (b.t === "step" && b.cmd) cmdCol = Math.max(cmdCol, 4 + b.cmd.length + 1); });
    blocks.forEach(function (b, bi) {
      var id = b.id || "_b" + bi, start = rows.length;
      if (b.t === "h") { push({ kind: "h", text: b.text, block: id }); push({ kind: "gap", block: id }); }
      else if (b.t === "h2") { push({ kind: "h2", text: b.text, block: id }); }
      else if (b.t === "gap") { push({ kind: "gap", block: id }); }
      else if (b.t === "text" || b.t === "small") {
        wrap(b.text, b.t === "small" ? Math.floor(measure * 1.15) : measure).forEach(function (l) { push({ kind: b.t, segs: [{ col: 0, text: l }], block: id }); });
        if (b.t === "text") push({ kind: "gap", block: id, half: true });
      } else if (b.t === "toc") {
        var lw0 = b.labelW || Math.max(12, (b.label || "").length + 2), lab = b.label ? (b.label + "                    ").slice(0, lw0) : "";
        var left = lab + b.title, right = b.page, room = measure - left.length - right.length - 2;
        if (room >= 2) push({ kind: "toc", segs: [{ col: 0, text: left + " " + ".".repeat(room) + " " }, { col: measure - right.length, text: right, style: "page" }], block: id });
        else {
          push({ kind: "toc", segs: [{ col: 0, text: left }], block: id });
          var lead = Math.max(2, measure - lab.length - right.length - 1);
          push({ kind: "toc", segs: [{ col: lab.length, text: ".".repeat(lead - lab.length > 2 ? lead - lab.length : 2) + " " }, { col: measure - right.length, text: right, style: "page" }], block: id, cont: true });
        }
      } else if (b.t === "step") {
        var head = b.cmd || b.item, num = b.n ? (b.n.length < 3 ? " " + b.n : b.n) : "";
        num = (num + "    ").slice(0, 4);
        var col0 = 4;
        if (b.cmd) {
          var pad = Math.max(head.length + 1, cmdCol - col0);
          var line = head + " ".repeat(Math.max(1, pad - head.length)) + "– " + b.state;
          if (col0 + line.length <= measure) push({ kind: "step", segs: [{ col: 0, text: num }, { col: col0, text: head, style: "cmd" }, { col: col0 + pad, text: "– " + b.state }], block: id });
          else { push({ kind: "step", segs: [{ col: 0, text: num }, { col: col0, text: head, style: "cmd" }], block: id }); push({ kind: "step", segs: [{ col: col0 + 2, text: "– " + b.state }], block: id, cont: true }); }
        } else {
          var full = head + " – " + b.state, ls = wrap(full, measure - col0);
          ls.forEach(function (l, k) { push({ kind: "step", segs: k === 0 ? [{ col: 0, text: num }, { col: col0, text: l, item: head.length }] : [{ col: col0 + 2, text: l }], block: id, cont: k > 0 }); });
        }
      } else if (b.t === "sub") {
        wrap(b.text, measure - 7).forEach(function (l) { push({ kind: "sub", segs: [{ col: 7, text: l }], block: id }); });
      } else if (b.t === "cond") {
        push({ kind: "cond", segs: [{ col: 2, text: b.text }], block: id });
      } else if (b.t === "note" || b.t === "caution" || b.t === "warning") {
        var inner = measure - 8, label = b.t.toUpperCase(), tl = wrap(b.text, inner), top = rows.length;
        push({ kind: "boxpad", block: id });
        push({ kind: "boxlabel", text: label, block: id });
        tl.forEach(function (l) { push({ kind: "boxtext", segs: [{ col: Math.floor((measure - l.length) / 2), text: l }], block: id }); });
        push({ kind: "boxpad", block: id });
        rows[top].box = { type: b.t, rows: rows.length - top };
        push({ kind: "gap", block: id, half: true });
      } else if (b.t === "table") {
        if (b.caption) wrap(b.caption, measure).forEach(function (l) { push({ kind: "caption", segs: [{ col: 0, text: l }], block: id }); });
        var c = 2, hs = [];
        b.cols.forEach(function (h, k) { hs.push({ col: c, text: h, style: "th" }); c += b.widths[k]; });
        push({ kind: "th", segs: hs, block: id, rule: c });
        b.rows.forEach(function (rw, ri) {
          var cc = 2, ss = [];
          rw.forEach(function (cell, k) { ss.push({ col: cc, text: cell }); cc += b.widths[k]; });
          push({ kind: "tr", segs: ss, block: id, ri: ri });
        });
        push({ kind: "gap", block: id, half: true });
      }
      spans[id] = [start, rows.length - 1];
    });
    // y offsets in "row units"; half gaps are 0.5
    var y = 0;
    for (i = 0; i < rows.length; i++) {
      rows[i].y = y;
      var k = rows[i].kind;
      y += k === "gap" ? (rows[i].half ? 0.5 : 0.8) : k === "h" ? 1.25 : k === "boxpad" ? 0.55 : 1;
    }
    return { rows: rows, spans: spans, height: y };
  };

  /* ---------- paper and pages ---------- */
  var paperCache = {};
  P.paperSprite = function (w, h, key, tint) {
    var id = key + w + "x" + h + (tint || "");
    if (paperCache[id]) return paperCache[id];
    var c = canvas(w, h), x = c.getContext("2d");
    x.fillStyle = tint || C.paper; x.fillRect(0, 0, w, h);
    x.globalCompositeOperation = "multiply"; x.globalAlpha = 0.9;
    var pat = x.createPattern(TEX.paper, "repeat"); x.fillStyle = pat; x.fillRect(0, 0, w, h);
    x.globalAlpha = 1; x.globalCompositeOperation = "source-over";
    var g = x.createRadialGradient(w * 0.45, h * 0.4, Math.min(w, h) * 0.3, w * 0.5, h * 0.5, Math.max(w, h) * 0.75);
    g.addColorStop(0, "rgba(0,0,0,0)"); g.addColorStop(1, "rgba(90,70,40,0.10)");
    x.fillStyle = g; x.fillRect(0, 0, w, h);
    paperCache[id] = c;
    return c;
  };
  /* Paper sheet with a soft shadow; holes = array of y positions on the left edge. */
  P.sheet = function (ctx, x, y, w, h, o) {
    o = o || {};
    ctx.save();
    ctx.shadowColor = "rgba(20,10,0," + (o.shadow === undefined ? 0.35 : o.shadow) + ")"; ctx.shadowBlur = 18; ctx.shadowOffsetX = 5; ctx.shadowOffsetY = 8;
    ctx.fillStyle = o.tint || C.paper; ctx.fillRect(x, y, w, h);
    ctx.restore();
    ctx.drawImage(P.paperSprite(Math.round(w), Math.round(h), o.key || "p", o.tint), x, y, w, h);
    (o.holes || []).forEach(function (hy) {
      var hx = o.holesRight ? x + w - 34 : x + 34;
      ctx.save();
      ctx.beginPath(); ctx.arc(hx, y + hy, 13, 0, 7); ctx.fillStyle = o.holeColor || "#2a2f2a"; ctx.fill();
      ctx.beginPath(); ctx.arc(hx, y + hy, 13, 0, 7); ctx.clip();
      ctx.beginPath(); ctx.arc(hx - 3, y + hy - 3, 13, 0, 7); ctx.lineWidth = 5; ctx.strokeStyle = "rgba(0,0,0,0.35)"; ctx.stroke();
      ctx.restore();
    });
  };

  /* ---------- background: the cutting mat ---------- */
  var matCache = null;
  P.matTexture = function () {
    if (matCache) return matCache;
    var W = 3600, H = 2400, c = canvas(W, H), x = c.getContext("2d"), n = noise2(71), r = P.rng(9);
    x.fillStyle = C.mat; x.fillRect(0, 0, W, H);
    var img = x.getImageData(0, 0, W, H), d = img.data;
    for (var j = 0; j < H; j += 2) for (var i = 0; i < W; i += 2) {
      var m = (n(i / 300, j / 300) - 0.5) * 18 + (n(i / 40, j / 40) - 0.5) * 6;
      for (var dy = 0; dy < 2; dy++) for (var dx = 0; dx < 2; dx++) { var k = ((j + dy) * W + i + dx) * 4; d[k] += m; d[k + 1] += m; d[k + 2] += m * 0.8; }
    }
    x.putImageData(img, 0, 0);
    var step = 36;
    for (var gx = 0; gx < W; gx += step) {
      var major = Math.round(gx / step) % 5 === 0;
      x.fillStyle = major ? "rgba(214,236,220,0.30)" : "rgba(200,226,210,0.13)";
      x.fillRect(gx, 0, major ? 2 : 1, H);
    }
    for (var gy = 0; gy < H; gy += step) {
      var mj = Math.round(gy / step) % 5 === 0;
      x.fillStyle = mj ? "rgba(214,236,220,0.30)" : "rgba(200,226,210,0.13)";
      x.fillRect(0, gy, W, mj ? 2 : 1);
    }
    x.strokeStyle = "rgba(214,236,220,0.16)"; x.lineWidth = 1.5;
    for (var a = -H; a < W; a += step * 10) { x.beginPath(); x.moveTo(a, H); x.lineTo(a + H, 0); x.stroke(); }
    P.font(x, P.FONT.cond, 22); x.fillStyle = "rgba(220,240,226,0.55)";
    for (gx = step * 5, i = 1; gx < W; gx += step * 5, i++) x.fillText(String(i), gx + 4, 24);
    for (gy = step * 5, i = 1; gy < H; gy += step * 5, i++) x.fillText(String(i), 6, gy - 4);
    for (i = 0; i < 26; i++) {
      var sx = r() * W, sy = r() * H, len = 40 + r() * 220, ang = r() * Math.PI;
      x.strokeStyle = "rgba(10,25,18,0.35)"; x.lineWidth = 1; x.beginPath(); x.moveTo(sx, sy); x.lineTo(sx + Math.cos(ang) * len, sy + Math.sin(ang) * len); x.stroke();
    }
    for (i = 0; i < 70; i++) { x.fillStyle = ["rgba(211,238,157,0.35)", "rgba(238,238,228,0.3)", "rgba(169,113,77,0.35)"][i % 3]; x.beginPath(); x.ellipse(r() * W, r() * H, 1.5 + r() * 3, 1 + r() * 2.5, r() * 3, 0, 7); x.fill(); }
    matCache = c;
    return c;
  };

  /* ---------- lamp light, grain, vignette ---------- */
  var lightCache = {};
  P.lamp = function (ctx, W, H, on, cx, cy) {
    var key = W + "x" + H + "_" + (cx || 0.36) + "_" + (cy || 0.3);
    var L = lightCache[key];
    if (!L) {
      L = canvas(W, H); var x = L.getContext("2d");
      var px = W * (cx || 0.36), py = H * (cy || 0.3), R = Math.hypot(W, H) * 0.78;
      var g = x.createRadialGradient(px, py, R * 0.05, px, py, R);
      g.addColorStop(0, "#fff6e4"); g.addColorStop(0.35, "#f4e4cc"); g.addColorStop(0.75, "#a99c88"); g.addColorStop(1, "#4d4740");
      x.fillStyle = g; x.fillRect(0, 0, W, H);
      lightCache[key] = L;
    }
    ctx.save();
    ctx.globalCompositeOperation = "multiply"; ctx.drawImage(L, 0, 0);
    if (on < 1) { ctx.globalCompositeOperation = "source-over"; ctx.fillStyle = "rgba(6,7,6," + (1 - on) * 0.94 + ")"; ctx.fillRect(0, 0, W, H); }
    ctx.restore();
  };
  P.post = function (ctx, W, H) {
    var g = TEX.grain[F.drawing % 4];
    ctx.save();
    ctx.globalCompositeOperation = "overlay"; ctx.globalAlpha = 0.085;
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(g, 0, 0, W, H);
    ctx.restore();
  };

  /* ---------- the hands ---------- */
  var POSES = {
    flat: { e: [1, 1, 1, 1], th: -0.55, spread: 0.06 },
    rest: { e: [0.8, 0.85, 0.8, 0.75], th: -0.45, spread: 0.04 },
    point: { e: [1, 0.22, 0.18, 0.15], th: -0.15, spread: 0.02 },
    pinch: { e: [0.62, 0.42, 0.38, 0.35], th: -0.05, spread: 0.0 },
    grip: { e: [0.42, 0.4, 0.38, 0.36], th: 0.05, spread: 0 },
    press: { e: [0.85, 0.3, 0.26, 0.24], th: -0.2, spread: 0.02 },
  };
  P.POSES = POSES;
  function poseOf(p) {
    if (typeof p === "string") return POSES[p];
    if (p && p.from) { var a = poseOf(p.from), b = poseOf(p.to), k = p.k;
      return { e: a.e.map(function (v, i) { return lerp(v, b.e[i], k); }), th: lerp(a.th, b.th, k), spread: lerp(a.spread, b.spread, k) }; }
    return p || POSES.rest;
  }
  /* A right hand seen from above, wrist at (x, y), fingers pointing along rot
   * (0 = up the screen). mirror for the left hand. scale 1 = palm ~150 px. */
  P.hand = function (ctx, h) {
    var pose = poseOf(h.pose), s = (h.scale || 1) * 150, id = h.id || "hand", m = h.mirror ? -1 : 1;
    var r = P.rng(P.hashStr(id) + P.variant(id) * 31), w = function (a) { return (r() - 0.5) * a; };
    var path = new Path2D();
    // forearm and palm
    P.capsule(0, 0.1 * s, 0, 3.6 * s, 0.27 * s, 0.34 * s, path);
    path.addPath(P.blob([[-0.30 * s, 0.05 * s], [-0.36 * s, -0.42 * s], [-0.18 * s, -0.86 * s], [0.18 * s, -0.88 * s], [0.38 * s, -0.74 * s], [0.33 * s, -0.2 * s], [0.25 * s, 0.08 * s]].map(function (q) { return [q[0] + w(s * 0.02), q[1] + w(s * 0.02)]; })));
    var fx = [-0.245, -0.083, 0.08, 0.235], fl = [0.6, 0.68, 0.63, 0.5], fw = [0.098, 0.104, 0.097, 0.084];
    var tips = [];
    for (var i = 0; i < 4; i++) {
      var e = pose.e[i], len = fl[i] * s * (0.32 + 0.68 * e), ang = (i - 1.5) * pose.spread;
      var bx = fx[i] * s, by = -0.8 * s + Math.abs(i - 1.3) * 0.04 * s;
      var tx = bx + Math.sin(ang) * len, ty = by - Math.cos(ang) * len;
      P.capsule(bx, by, tx, ty, fw[i] * s * 1.02, fw[i] * s * (0.82 + 0.18 * (1 - e)), path);
      tips.push([tx, ty, e, fw[i] * s]);
    }
    var ta = pose.th - 0.75, tl = 0.5 * s, tbx = -0.3 * s, tby = -0.28 * s;
    var ttx = tbx + Math.sin(ta) * tl, tty = tby - Math.cos(ta) * tl;
    P.capsule(tbx, tby, ttx, tty, 0.12 * s, 0.095 * s, path);
    ctx.save();
    ctx.translate(h.x, h.y); ctx.rotate(h.rot || 0); ctx.scale(m, 1);
    // cast shadow (lifted hands cast softer, offset shadows)
    var lift = h.lift === undefined ? 40 : h.lift;
    ctx.save();
    ctx.translate(10 + lift * 0.4, 14 + lift * 0.5);
    ctx.filter = "blur(" + (8 + lift * 0.12).toFixed(1) + "px)";
    ctx.fillStyle = "rgba(25,12,0," + (0.3 - clamp(lift / 400) * 0.12) + ")"; ctx.fill(path);
    ctx.filter = "none";
    ctx.restore();
    var bb = { x: -0.55 * s, y: -1.6 * s, w: 1.1 * s, h: 2.2 * s };
    P.clayFill(ctx, path, h.color || C.skin, bb, { variant: P.variant(id), id: id, occ: 0.42, rim: 0.3, texScale: 0.7, sheen: 0.1, edge: 0 });
    // knuckle creases and nails
    tips.forEach(function (tp, i) {
      var bx = fx[i] * s, by = -0.8 * s;
      ctx.strokeStyle = "rgba(90,40,20,0.22)"; ctx.lineWidth = 1.4;
      var mx = lerp(bx, tp[0], 0.45), my = lerp(by, tp[1], 0.45);
      ctx.beginPath(); ctx.moveTo(mx - tp[3] * 0.5, my + 2); ctx.quadraticCurveTo(mx, my - 3, mx + tp[3] * 0.5, my + 2); ctx.stroke();
      if (tp[2] > 0.55) {
        var a = Math.atan2(tp[1] - by, tp[0] - bx) + Math.PI / 2;
        ctx.save(); ctx.translate(tp[0] - Math.sin(a) * -tp[3] * 0.25, tp[1] + Math.cos(a) * -tp[3] * 0.25 + tp[3] * 0.45); ctx.rotate(a);
        ctx.fillStyle = "rgba(255,232,218,0.28)"; ctx.beginPath(); ctx.ellipse(0, 0, tp[3] * 0.42, tp[3] * 0.5, 0, 0, 7); ctx.fill();
        ctx.restore();
      }
    });
    // knuckle ridge
    ctx.strokeStyle = "rgba(255,240,225,0.22)"; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(-0.28 * s, -0.74 * s); ctx.quadraticCurveTo(0, -0.84 * s, 0.3 * s, -0.7 * s); ctx.stroke();
    // felt cuff
    var cuff = P.rrect(-0.42 * s, 1.15 * s, 0.84 * s, 2.8 * s, 0.18 * s, r, s * 0.01);
    P.clayFill(ctx, cuff, h.cuff || C.felt, { x: -0.42 * s, y: 1.15 * s, w: 0.84 * s, h: 0.9 * s }, { variant: P.variant(id + "c"), id: id + "c", tex: 0.7, sheen: 0.04, occ: 0.4 });
    ctx.strokeStyle = "rgba(0,0,0,0.2)"; ctx.lineWidth = 2; ctx.setLineDash([5, 6]);
    ctx.beginPath(); ctx.moveTo(-0.36 * s, 1.27 * s); ctx.lineTo(0.36 * s, 1.27 * s); ctx.stroke(); ctx.setLineDash([]);
    ctx.restore();
    // return fingertip of index in world coords for interaction
    var tip = tips[0], c = Math.cos(h.rot || 0), sn = Math.sin(h.rot || 0), lx = tip[0] * m, ly = tip[1];
    return { index: [h.x + lx * c - ly * sn, h.y + lx * sn + ly * c] };
  };
  /* Keyframe interpolation: keys = [[t, {x, y, rot, scale, lift}], ...] */
  P.track = function (t, keys, ease) {
    if (t <= keys[0][0]) return Object.assign({}, keys[0][1]);
    for (var i = 0; i < keys.length - 1; i++) {
      var a = keys[i], b = keys[i + 1];
      if (t < b[0]) {
        var k = (ease || E.io)((t - a[0]) / (b[0] - a[0])), o = {};
        Object.keys(b[1]).forEach(function (n) { var va = a[1][n], vb = b[1][n]; o[n] = typeof vb === "number" && typeof va === "number" ? lerp(va, vb, k) : k < 0.5 ? (va === undefined ? vb : va) : vb; });
        Object.keys(a[1]).forEach(function (n) { if (!(n in o)) o[n] = a[1][n]; });
        return o;
      }
    }
    return Object.assign({}, keys[keys.length - 1][1]);
  };

  P.init = function () {
    if (P.ready) return P.ready;
    P.ready = P.loadFonts().then(function () { makeTextures(); P.matTexture(); });
    return P.ready;
  };
})();
