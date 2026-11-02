// 2D drawing of a planar four-bar in plan view: used as the WebGL fallback for the
// investigation stage and as the sandbox's live sketch.
import { s, svgRoot, C } from "./svg.js";
import { displayPose } from "./pose.js";

export function linkageSVG({ width = 520, height = 420, label = "Four-bar linkage plan view" } = {}) {
  const root = svgRoot(width, height, label);
  const g = s("g");
  root.append(g);
  function draw(cfg, theta, { fit = null } = {}) {
    const p = displayPose(cfg, theta);
    const R = Math.max(cfg.c, cfg.d) + Math.max(cfg.a, cfg.b);
    const span = fit ?? (2 * R + 12);
    const scale = Math.min(width, height) / span;
    const cx = width / 2 - (cfg.a / 2) * scale, cy = height / 2;
    const X = (pt) => cx + pt[0] * scale, Y = (pt) => cy - pt[1] * scale;
    const line = (p1, p2, color, w, extra = {}) => s("line", { x1: X(p1), y1: Y(p1), x2: X(p2), y2: Y(p2), stroke: color, "stroke-width": w, "stroke-linecap": "round", ...extra });
    const pin = (pt, color, r = 4.5) => s("circle", { cx: X(pt), cy: Y(pt), r, fill: "#09111a", stroke: color, "stroke-width": 2 });
    g.replaceChildren(...[
      s("circle", { cx: X(p.B), cy: Y(p.B), r: cfg.c * scale, fill: "none", stroke: C.teal3, "stroke-width": 1.2, "stroke-opacity": 0.75, "stroke-dasharray": "4 4" }),
      s("circle", { cx: X(p.D), cy: Y(p.D), r: cfg.d * scale, fill: "none", stroke: C.copper3, "stroke-width": 1.2, "stroke-opacity": 0.85, "stroke-dasharray": "4 4" }),
      line(p.A, p.D, C.muted, 7, { "stroke-opacity": 0.65 }),
      line(p.B, p.P, "#4f9db8", 7, { "stroke-opacity": 0.85 }),
      line(p.A, p.B, "#c86b4e", 7),
      line(p.D, p.Q, "#7fae8a", 4.5),
      pin(p.A, C.ivory), pin(p.D, C.ivory), pin(p.B, C.ivory),
      p.closed ? pin(p.P, C.ok, 5) : [pin(p.P, C.bad, 5), pin(p.Q, C.bad, 5),
        line(p.P, p.Q, C.bad, 1.6, { "stroke-dasharray": "3 3" })],
      s("text", { x: X(p.A) - 14, y: Y(p.A) + 18, fill: C.ivoryDim, "font-size": 12, text: "A" }),
      s("text", { x: X(p.D) + 8, y: Y(p.D) + 18, fill: C.ivoryDim, "font-size": 12, text: "D" }),
      s("text", { x: X(p.B) - 16, y: Y(p.B) - 8, fill: C.ivoryDim, "font-size": 12, text: "B" }),
      p.closed
        ? s("text", { x: X(p.P) + 8, y: Y(p.P) - 8, fill: C.ok, "font-size": 12, text: "C (closed)" })
        : s("text", { x: (X(p.P) + X(p.Q)) / 2 + 12, y: (Y(p.P) + Y(p.Q)) / 2 + 22, fill: C.bad, "font-size": 12, text: `ε = ${p.gap.toFixed(2)} mm` }),
    ].flat(Infinity));
    return p;
  }
  return { root, draw };
}
