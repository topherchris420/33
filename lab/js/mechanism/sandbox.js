// CONCEPTUAL sandbox: a free planar four-bar to build intuition. Not a Project 33 design.
import { h, announce, syncRange } from "../core/dom.js";
import { categoryBadge } from "../core/taxonomy.js";
import { grashofCondition, transmissionAngle, couplerClosureBand } from "../core/math/fourbar.js";
import { linkageSVG } from "./linkage-svg.js";
import { transmissionChart, designHeatmap, classify, HEAT } from "./charts.js";

const LIMITS = { a: [5, 50], b: [5, 40], c: [5, 90], d: [5, 40] };
const NAMES = { a: "ground a", b: "input b", c: "coupler c", d: "output d" };

export function buildSandbox(root, { baseline }) {
  const cfg = { ...baseline };
  let theta = 46;
  const inputs = {};
  const outs = {};
  const controls = h("div", {},
    h("div", { class: "cluster", style: { marginBottom: "12px" } }, categoryBadge("conceptual"), h("span", { class: "label" }, "Free model · not a design")),
    ...Object.keys(LIMITS).map((k) => {
      const id = `sb-${k}`;
      const input = h("input", { id, type: "range", min: LIMITS[k][0], max: LIMITS[k][1], step: 0.5, value: cfg[k] });
      outs[k] = h("output", { for: id }, `${cfg[k]} mm`);
      inputs[k] = input;
      return h("div", { class: "field" }, h("div", { class: "field-row" }, h("label", { for: id }, NAMES[k]), outs[k]), input);
    }),
    (() => {
      const input = h("input", { id: "sb-theta", type: "range", min: 0, max: 92, step: 0.5, value: theta });
      inputs.theta = input; outs.theta = h("output", { for: "sb-theta" }, `${theta}°`);
      return h("div", { class: "field" }, h("div", { class: "field-row" }, h("label", { for: "sb-theta" }, "drive angle θ"), outs.theta), input);
    })(),
    h("div", { class: "btn-row", style: { marginBottom: "14px" } },
      h("button", { class: "btn", type: "button", "data-preset": "baseline" }, "Recorded 25/60/15/15"),
      h("button", { class: "btn", type: "button", "data-preset": "fusion" }, "Fusion sketch c = 25 (D-005)")),
    h("div", { class: "mx-sb-out", id: "sb-out", "aria-live": "polite" }));

  const sketch = linkageSVG({ width: 520, height: 360, label: "Sandbox linkage sketch" });
  const muWrap = h("div");
  const mu = transmissionChart(muWrap);
  const canvas = h("canvas", { width: 600, height: 338, role: "img", "aria-label": "Design-space map: closure and transmission-angle class over coupler and output length for the current ground and input links. Click to pick a point." });
  const heat = designHeatmap(canvas);
  const legend = h("div", { class: "mx-legend" },
    ...[["none", "never closes 0–92°"], ["partial", "closes at some angles"], ["outside", "closes everywhere; μ leaves 40–140°"], ["within", "closes everywhere; μ within 40–140°"]]
      .map(([k, t]) => h("span", {}, h("i", { style: { background: `rgb(${HEAT[k].join(",")})` } }), t)));
  const bandText = h("div", { class: "mx-band-text" });

  root.replaceChildren(h("div", { class: "mx-sb-grid" },
    controls,
    h("div", {}, h("h4", {}, "Plan view at the drive angle"), sketch.root, h("h4", { style: { marginTop: "10px" } }, "Transmission angle over 0–92°"), muWrap),
    h("div", { class: "mx-heat" }, h("h4", {}, "Design space: coupler c × output d (a, b fixed)"), canvas, legend,
      h("p", { class: "muted", style: { fontSize: "12px", marginTop: "6px" } }, "Each cell evaluates the 47 poses of the recorded 0–92° drive range in 2° steps, as mechanism/four_bar.py does. Click to move c and d."),
      h("p", { class: "mx-note", id: "sb-within", "aria-live": "polite" }))),
  bandText);

  function render() {
    for (const k of Object.keys(LIMITS)) outs[k].textContent = `${cfg[k]} mm`;
    outs.theta.textContent = `${theta}°`;
    const p = sketch.draw(cfg, theta, { fit: 2 * (Math.max(cfg.c, cfg.d) + Math.max(cfg.a, cfg.b)) + 12 });
    mu.draw(cfg);
    const cl = classify(cfg.a, cfg.b, cfg.c, cfg.d);
    const band = couplerClosureBand(cfg.a, cfg.b, cfg.d);
    heat.draw(cfg, [
      { c: 60, d: 15, color: "#e07650", label: "recorded 60/15", align: "left", dy: 20 },
      { c: 25, d: 15, color: "#e0a274", label: "Fusion sketch 25/15", align: "left", dy: 20 },
      { c: cfg.c, d: cfg.d, color: "#f1e9d6", label: "current", cross: true, align: "left", dy: -10 },
    ]);
    const muNow = transmissionAngle(cfg.a, cfg.c, cfg.b, cfg.d, theta);
    const within = heat.count("within");
    root.querySelector("#sb-within").textContent = within
      ? `For a = ${cfg.a} mm and b = ${cfg.b} mm, ${within} map cells close everywhere with μ inside 40–140°.`
      : `For a = ${cfg.a} mm and b = ${cfg.b} mm, no cell in this window closes everywhere with μ inside 40–140°: the diagonal f swings too far over 0–92° for any coupler/output pair shown.`;
    const out = root.querySelector("#sb-out");
    const row = (k, v, cls = "") => [h("span", { class: "k" }, k), h("span", { class: `v ${cls}` }, v)];
    out.replaceChildren(
      ...row("Grashof class", grashofCondition(cfg.a, cfg.b, cfg.c, cfg.d)),
      ...row("Poses closing (0–92°, 2° steps)", `${cl.closed} / 47`, cl.closed === 47 ? "ok" : cl.closed ? "warn" : "bad"),
      ...row("Transmission angle range (closed poses)", cl.closed ? `${cl.mMin.toFixed(1)}° – ${cl.mMax.toFixed(1)}°` : "undefined — no closed pose", cl.k === "within" ? "ok" : cl.closed ? "warn" : "bad"),
      ...row("Transmission angle at current θ", muNow === null ? "no real angle (open)" : `${muNow.toFixed(1)}°`),
      ...row("Gap at current θ", p.closed ? "0 — closes" : `${p.gap.toFixed(2)} mm`, p.closed ? "ok" : "bad"),
      ...row("Closing coupler band for this a, b, d", band ? `${band.low.toFixed(1)} ≤ c ≤ ${band.high.toFixed(1)} mm` : "none — no single c closes all 0–92°", band ? "" : "bad"),
    );
  }

  // Fixed statement about the recorded dimensions, computed rather than typed.
  const rec = couplerClosureBand(baseline.a, baseline.b, baseline.d);
  const muFusion0 = transmissionAngle(baseline.a, 25, baseline.b, baseline.d, 0);
  // Exhaustive check over a wider window for the recorded a and b (1-200 mm, 1 mm steps).
  let recWithin = 0;
  for (let c = 1; c <= 200; c += 1) for (let d = 1; d <= 200; d += 1) if (classify(baseline.a, baseline.b, c, d).k === "within") recWithin++;
  bandText.replaceChildren(
    h("div", { class: "cluster", style: { marginBottom: "6px" } }, categoryBadge("conceptual"), h("span", { class: "label" }, "Arithmetic on recorded dimensions — not a recommendation")),
    h("p", { class: "mb0" },
      `For the recorded a = ${baseline.a} mm, b = ${baseline.b} mm, d = ${baseline.d} mm, the closure inequality |c − d| ≤ f(θ) ≤ c + d holds across 0–92° only for `,
      h("b", {}, `${rec.low.toFixed(1)} mm ≤ c ≤ ${rec.high.toFixed(1)} mm`),
      `. This is arithmetic on recorded dimensions, not a design proposal: D-002 remains open, and the intended topology needs human review. The Fusion sketch's 25 mm coupler (D-005) sits at the band's upper edge, where μ = ${muFusion0.toFixed(0)}° at θ = 0° — a dead-centre pose — so it would not satisfy R-C1-TRANSMISSION (40–140°) either.`),
    h("p", { class: "mb0", style: { marginTop: "8px" } }, recWithin
      ? `With a = ${baseline.a} mm and b = ${baseline.b} mm, ${recWithin} coupler/output pairs between 1 and 200 mm (1 mm steps) close over 0–92° with μ inside 40–140°.`
      : `Going further: with a = ${baseline.a} mm and b = ${baseline.b} mm, no coupler/output pair between 1 and 200 mm (checked in 1 mm steps) closes over 0–92° with μ inside 40–140°. If the 40–140° guidance applies, the recorded ground and input links would also need review — again arithmetic, not a finding of the record.`));

  for (const [k, input] of Object.entries(inputs)) {
    syncRange(input);
    input.addEventListener("input", () => {
      if (k === "theta") theta = Number(input.value); else cfg[k] = Number(input.value);
      render();
    });
    input.addEventListener("change", () => announce(`${k === "theta" ? "Drive angle" : NAMES[k]} ${input.value}`));
  }
  const setCfg = (next, label) => {
    Object.assign(cfg, next);
    for (const k of Object.keys(LIMITS)) { inputs[k].value = String(cfg[k]); inputs[k].dispatchEvent(new Event("input")); }
    render();
    announce(label);
  };
  root.querySelectorAll("[data-preset]").forEach((btn) => btn.addEventListener("click", () => {
    if (btn.dataset.preset === "baseline") setCfg({ ...baseline }, "Recorded baseline loaded");
    else setCfg({ ...baseline, c: 25 }, "Fusion sketch coupler of 25 millimetres loaded");
  }));
  canvas.addEventListener("click", (e) => {
    const pick = heat.pick(e);
    if (!pick) return;
    setCfg({ c: pick.c, d: pick.d }, `Coupler ${pick.c}, output ${pick.d} millimetres`);
  });
  render();
}
