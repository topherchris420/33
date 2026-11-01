// Mechanism Lab: the folding-fin investigation (C1) and the model comparison studio.
import { mountShell } from "../core/shell.js";
import { h, $, clear, announce, syncRange, press, reducedMotion, webglAvailable } from "../core/dom.js";
import { lab, canonical, repoLink, docLink, claimLink, discrepancyLink } from "../core/data.js";
import { categoryBadge, assetBadge, statusChip } from "../core/taxonomy.js";
import { eq } from "../core/tex.js";
import { closureResidual, diagonal, grashofCondition, DRIVE_MIN_DEG, DRIVE_MAX_DEG } from "../core/math/fourbar.js";
import { displayPose, MODE_TEXT } from "./pose.js";
import { residualChart } from "./charts.js";
import { linkageSVG } from "./linkage-svg.js";
import { buildMathPanel } from "./math-panel.js";
import { buildSandbox } from "./sandbox.js";
import { buildComparison } from "./comparison.js";

mountShell();

const state = { cfg: null, theta: 46, row: null, baseline: null, playing: false, paused: false };
let stage = null, chart = null, ev = null, sweep = null;

function minResidual(cfg) {
  let best = Infinity, at = 0;
  for (let t = DRIVE_MIN_DEG; t <= DRIVE_MAX_DEG; t += 0.5) {
    const r = closureResidual(cfg.a, cfg.b, cfg.c, cfg.d, t);
    if (r < best) { best = r; at = t; }
  }
  return { best, at };
}

function rowToCfg(r) { return { a: r.ground, b: r.input, c: r.coupler, d: r.output }; }
const isBaseline = (r) => r.ground === sweep.baseline.ground && r.coupler === sweep.baseline.coupler && r.input === sweep.baseline.input && r.output === sweep.baseline.output;

async function init() {
  [ev, sweep] = await Promise.all([lab.evidence(), canonical.fourBarSweep()]);
  state.baseline = sweep.baseline;
  state.row = sweep.baseline;
  state.cfg = rowToCfg(sweep.baseline);

  for (const id of ["inv-badge", "chart-badge", "var-badge", "math-badge", "cmp-badge", "readout-badge"]) $(`#${id}`)?.replaceChildren(categoryBadge("research"));
  $("#sb-badge").replaceChildren(categoryBadge("conceptual"));
  $("#vp-class").replaceChildren(categoryBadge("research"), assetBadge("reconstructed"),
    h("span", { class: "css2d-label dim", style: { position: "static" } }, "Lengths from C1 model · bar section from Project33FourBar.py"));

  renderVerdict();
  renderRequirements();
  buildStage();
  chart = residualChart($("#residual-chart"));
  $("#chart-legend").replaceChildren(
    h("span", {}, h("i", { style: { background: "#f1e9d6" } }), "f(θ) inside the recorded drive range"),
    h("span", {}, h("i", { style: { background: "rgba(207,198,178,0.5)" } }), "f(θ) at other angles"),
    h("span", {}, h("i", { style: { background: "repeating-linear-gradient(45deg,#67d8cf 0 2px,transparent 2px 5px)" } }), "closure band |c − d| … c + d"),
    h("span", {}, h("i", { style: { background: "#e07650" } }), "ε(θ): distance short of closing"),
    h("span", { class: "muted" }, "Curve computed with lab/js/core/math/fourbar.js (port of mechanism/four_bar.py, verified by tests/lab_math.test.mjs)."));
  buildVariants();
  buildMathPanel($("#math-panel"), { ev, sweep });
  buildSandbox($("#sandbox-body"), { baseline: state.cfg, ev });
  buildComparison($("#compare"), { ev }).catch((err) => {
    $("#compare").replaceChildren(h("div", { class: "notice warn" }, `Comparison studio could not load its sources: ${err.message}`));
  });
  update();
}

function renderVerdict() {
  const c1 = ev.claims.find((c) => c.id === "C1");
  const closure = ev.requirements.find((r) => r.id === "R-C1-CLOSURE");
  const mr = minResidual(state.cfg);
  const maxR = closureResidual(state.cfg.a, state.cfg.b, state.cfg.c, state.cfg.d, 0);
  clear($("#mx-verdict"),
    h("div", { class: "cluster" }, categoryBadge("research"), h("span", { class: "label" }, "The record says")),
    h("div", { class: "row" }, h("span", {}, "Claim C1 · ", c1.title, h("small", {}, `support: ${c1.support_label} · gate: ${c1.gate_label}`)), statusChip(c1.status, c1.status_label)),
    h("div", { class: "row" }, h("span", {}, "R-C1-CLOSURE", h("small", {}, closure.text)), h("span", { class: "big bad" }, closure.label)),
    h("div", { class: "row" }, h("span", {}, "Baseline poses that close", h("small", {}, "docs/EVIDENCE/C1_four_bar_sweep.json · baseline.poses_closed")), h("span", { class: "big bad" }, `${sweep.baseline.poses_closed} / ${sweep.baseline.poses_evaluated}`)),
    h("div", { class: "row" }, h("span", {}, "Variants closing at any pose", h("small", {}, "summary.closing_at_any_pose of summary.configurations")), h("span", { class: "big bad" }, `${sweep.summary.closing_at_any_pose} / ${sweep.summary.configurations}`)),
    h("div", { class: "row" }, h("span", {}, "Closure residual over 0–92°", h("small", {}, "derived here with the tested port of four_bar.py")), h("span", { class: "big" }, `${mr.best.toFixed(1)}–${maxR.toFixed(1)} mm`)),
  );
}

function renderRequirements() {
  const ids = ["R-C1-CLOSURE", "R-C1-TRANSMISSION", "R-C1-LOCK"];
  $("#reqs").replaceChildren(...ids.map((id) => {
    const r = ev.requirements.find((x) => x.id === id);
    const cls = r.evidence_class ? ` (${r.evidence_class})` : "";
    return h("div", { class: "req" }, h("b", {}, r.id), h("span", { class: `res ${r.result}` }, r.label + cls), h("span", {}, r.text));
  }));
}

function buildStage() {
  const vp = $("#linkage-vp");
  const tools = $("#vp-tools");
  if (webglAvailable()) {
    try {
      // dynamic import keeps the page usable if WebGL setup fails
      return import("./linkage-scene.js").then(({ createLinkageScene }) => {
        stage = createLinkageScene(vp, { onAttemptDone: openTechPanel });
        const canvas = vp.querySelector("canvas");
        canvas?.setAttribute("role", "img");
        canvas?.setAttribute("aria-label", "3D linkage view: the coupler and output pins do not meet");
        stage.setConfig(state.cfg);
        stage.setTheta(state.theta);
        stage.viewTop(false);
        tools.replaceChildren(
          h("button", { class: "btn", type: "button", onclick: () => { stage.viewTop(); announce("Top orthographic view"); } }, "Top · ortho"),
          h("button", { class: "btn", type: "button", onclick: () => { stage.view34(); announce("Three-quarter perspective view"); } }, "3/4 · persp"),
          h("button", { class: "btn", type: "button", onclick: () => { stage.resetGuides(); stage.viewTop(); } }, "Reset view"));
      }).catch((err) => fallback2D(vp, err));
    } catch (err) { fallback2D(vp, err); }
  } else fallback2D(vp);
  return null;
}

function fallback2D(vp, err) {
  const svg = linkageSVG({ width: 640, height: 460, label: "Plan view of the baseline linkage in its closest-approach configuration" });
  vp.querySelector("canvas")?.remove();
  vp.prepend(h("div", { class: "fallback-2d" }, svg.root,
    h("p", { class: "muted", style: { position: "absolute", top: "74px", left: "14px", fontSize: "12px", margin: 0 } }, err ? `3D view unavailable (${err.message}); showing the 2D plan view.` : "WebGL is not available; showing the 2D plan view.")));
  stage = {
    setConfig() { svg.draw(state.cfg, state.theta); }, setTheta() { svg.draw(state.cfg, state.theta); },
    setLabels() {}, viewTop() {}, view34() {}, resetGuides() {},
    attempt: async () => openTechPanel(displayPose(state.cfg, state.theta)),
  };
  stage.setConfig();
}

function update() {
  const { cfg, theta } = state;
  const p = displayPose(cfg, theta);
  stage?.setTheta(theta);
  chart?.draw(cfg, theta);
  const lo = Math.abs(cfg.c - cfg.d), hi = cfg.c + cfg.d;
  const eps = p.closed ? 0 : p.gap;
  $("#gap-value").textContent = `${eps.toFixed(2)} mm`;
  $("#gap-sub").textContent = p.closed ? "loop closed" : `loop open · ${p.mode === "nested" ? "nested circles" : "circles apart"}`;
  $("#theta-out").textContent = `${theta.toFixed(1)}°`;
  const mr = minResidual(cfg);
  const row = state.row;
  const fromJson = row && row.ground === cfg.a && row.coupler === cfg.c && row.input === cfg.b && row.output === cfg.d;
  $("#live").replaceChildren(
    h("dt", {}, "Configuration"), h("dd", {}, `a ${cfg.a} · c ${cfg.c} · b ${cfg.b} · d ${cfg.d} mm`),
    h("dt", {}, "Grashof"), h("dd", {}, fromJson ? row.grashof : grashofCondition(cfg.a, cfg.b, cfg.c, cfg.d)),
    h("dt", {}, "Drive angle θ"), h("dd", {}, `${theta.toFixed(1)}°`),
    h("dt", {}, "Diagonal |BD|"), h("dd", {}, `${diagonal(cfg.a, cfg.b, theta).toFixed(2)} mm`),
    h("dt", {}, "Loop needs"), h("dd", {}, `${lo.toFixed(2)} – ${hi.toFixed(2)} mm`),
    h("dt", {}, "Closure gap"), h("dd", { class: eps > 0 ? "bad" : "ok" }, `${eps.toFixed(2)} mm`),
    h("dt", {}, "Failure mode"), h("dd", {}, p.closed ? "none — closes" : (MODE_TEXT[p.mode] || "—").split(" — ")[0]),
    h("dt", {}, "Poses closing 0–92°"), h("dd", { class: fromJson && row.poses_closed === 0 ? "bad" : "" }, fromJson ? `${row.poses_closed} / ${row.poses_evaluated} (JSON)` : "—"),
    h("dt", {}, "Smallest gap 0–92°"), h("dd", {}, `${mr.best.toFixed(2)} mm at ${mr.at}°`),
  );
  const theta$ = $("#theta");
  if (Number(theta$.value) !== theta) { theta$.value = String(theta); theta$.dispatchEvent(new Event("input")); }
}

function bindControls() {
  const theta = syncRange($("#theta"));
  theta.addEventListener("input", () => {
    const v = Number(theta.value);
    if (v !== state.theta) { state.theta = v; update(); }
  });
  theta.addEventListener("change", () => announce(`Drive angle ${state.theta} degrees, residual ${closureResidual(state.cfg.a, state.cfg.b, state.cfg.c, state.cfg.d, state.theta).toFixed(2)} millimetres`));

  const play = $("#play");
  let raf = 0, dir = 1, lastStep = 0;
  const stop = () => { state.playing = false; press(play, false); play.textContent = "▶ Sweep 0–92°"; cancelAnimationFrame(raf); };
  play.addEventListener("click", () => {
    if (state.playing) { stop(); announce("Sweep paused"); return; }
    state.playing = true; press(play, true); play.textContent = "❚❚ Pause sweep";
    announce("Sweeping the drive angle from 0 to 92 degrees");
    let last = performance.now();
    const step = (now) => {
      if (!state.playing) return;
      const dt = Math.min((now - last) / 1000, 0.1); last = now;
      if (reducedMotion()) {
        // discrete steps instead of continuous motion
        if (now - lastStep > 700) { lastStep = now; state.theta = state.theta >= 92 ? 0 : Math.min(92, state.theta + 23); update(); }
      } else {
        let t = state.theta + dir * dt * 26;
        if (t >= 92) { t = 92; dir = -1; } else if (t <= 0) { t = 0; dir = 1; }
        state.theta = Math.round(t * 2) / 2;
        update();
      }
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
  });

  $("#attempt").addEventListener("click", async () => {
    stop();
    const btn = $("#attempt");
    btn.disabled = true;
    announce("Attempting to assemble the linkage");
    await stage.attempt();
    btn.disabled = false;
  });

  const labels = $("#labels");
  labels.addEventListener("click", () => { const on = press(labels); stage?.setLabels(on); });
  return { stop };
}

function openTechPanel(p) {
  state.paused = true;
  $("#paused").hidden = false;
  const tech = $("#tech");
  const { cfg, theta } = state;
  const lo = Math.abs(cfg.c - cfg.d), hi = cfg.c + cfg.d;
  let fMax = 0;
  for (let t = 0; t <= 92; t += 0.5) fMax = Math.max(fMax, diagonal(cfg.a, cfg.b, t));
  const fMin = Math.min(diagonal(cfg.a, cfg.b, 0), diagonal(cfg.a, cfg.b, 92));
  const closure = ev.requirements.find((r) => r.id === "R-C1-CLOSURE");
  const disc = (id) => ev.discrepancies.find((d) => d.id === id);
  const link = (href, id, text) => h("a", { href }, h("b", {}, id), h("span", {}, text));
  clear(tech,
    h("div", { class: "panel-head" }, h("h4", { id: "tech-title" }, "Why the pieces refuse — the constraint, not the effort"), h("span", { class: "cluster" }, categoryBadge("research"), statusChip("contradicted", "Not repaired"))),
    h("div", { class: "panel-body mx-tech-grid" },
      h("div", {},
        h("p", {}, p.closed
          ? "This configuration closes: both links meet at C."
          : `At θ = ${theta.toFixed(1)}° the attempt left the pins ${p.gap.toFixed(2)} mm apart. No force changes that; only a different geometry could.`),
        eq(String.raw`\lvert c-d\rvert \;\le\; f(\theta_2) \;\le\; c+d`),
        eq(String.raw`\underbrace{\lvert ${cfg.c}-${cfg.d}\rvert = ${lo}\ \text{mm}}_{\text{needed}} \;>\; \underbrace{${fMax.toFixed(1)}\ \text{mm}}_{\max f,\ 0\le\theta_2\le 92^\circ}`),
        h("ul", {},
          h("li", {}, h("b", {}, "Constraint. "), `The coupler pin must lie on a circle of radius c = ${cfg.c} mm about B, and the output pin on a circle of radius d = ${cfg.d} mm about D. Over the drive range B and D are ${fMin.toFixed(1)}–${fMax.toFixed(1)} mm apart, so the output circle sits wholly inside the coupler circle.`),
          h("li", {}, h("b", {}, "Assumption. "), (closure.assumptions || []).join(" "), " Drive angle measured from the folded position."),
          h("li", {}, h("b", {}, "Recorded result. "), `${closure.id}: ${closure.label} (${closure.evidence_class}). R-C1-TRANSMISSION is not evaluable — no closed pose has a transmission angle. R-C1-LOCK needs a physical measurement.`),
          h("li", {}, h("b", {}, "What it does not say. "), "Loop geometry says nothing about loads, clearance, compliance, or locking torque. The intended topology is a human decision."),
        ),
        h("div", { class: "btn-row" },
          h("button", { class: "btn", type: "button", onclick: () => { state.paused = false; $("#paused").hidden = true; tech.hidden = true; stage.resetGuides?.(); stage.viewTop(); announce("Resumed exploring. The linkage is still open."); } }, "Resume exploring (still open)"),
          h("a", { class: "btn ghost", href: "#mathematics" }, "See the mathematics"))),
      h("div", {},
        h("h4", {}, "Follow the evidence"),
        h("div", { class: "mx-link-list" },
          link(claimLink("C1"), "C1", "Claim passport — folding-fin mechanism model"),
          link(docLink("docs/TRACEABILITY.md"), "R-C1-CLOSURE", closure.text),
          ...["D-002", "D-004", "D-005"].map((id) => link(discrepancyLink(id), id, `${disc(id).title} (${disc(id).status})`)),
          link(repoLink("docs/EVIDENCE/C1_four_bar_sweep.json"), "JSON", "Committed sweep: baseline + 81 variants, null where no value exists"),
          link(repoLink("mechanism/four_bar.py"), "MODEL", "mechanism/four_bar.py — circle-intersection closure, revision 2")))));
  tech.hidden = false;
  tech.focus({ preventScroll: true });
  tech.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "nearest" });
  announce(`The geometry cannot close. Gap ${p.gap.toFixed(2)} millimetres. Technical panel opened.`);
}

function buildVariants() {
  const rows = sweep.rows;
  const grounds = [...new Set(rows.map((r) => r.ground))].sort((a, b) => a - b);
  const couplers = [...new Set(rows.map((r) => r.coupler))].sort((a, b) => a - b);
  const inputs = [...new Set(rows.map((r) => r.input))].sort((a, b) => a - b);
  const outputs = [...new Set(rows.map((r) => r.output))].sort((a, b) => a - b);
  const allMin = rows.map((r) => minResidual(rowToCfg(r)).best);
  const hi = Math.max(...allMin), lo = Math.min(...allMin);
  const sum = sweep.summary;
  $("#var-summary").replaceChildren(
    h("span", {}, h("b", {}, sum.configurations), "configurations swept"),
    h("span", {}, h("b", {}, sum.assemblable_over_range), "assemble over 0–92°"),
    h("span", {}, h("b", {}, sum.closing_at_any_pose), "close at any pose"),
    h("span", { class: "muted" }, `ground ∈ {${grounds}} · coupler ∈ {${couplers}} · input ∈ {${inputs}} · output ∈ {${outputs}} mm`));
  const grid = h("div", { class: "mx-vgrid", role: "group", "aria-label": "81 committed configurations" });
  grid.append(h("span", { class: "axis-label corner" }, "ground ↓ · coupler →"), ...couplers.map((c) => h("span", { class: "axis-label" }, `coupler ${c} mm`)));
  const buttons = [];
  for (const g of grounds) {
    grid.append(h("span", { class: "axis-label row" }, `ground ${g}`));
    for (const c of couplers) {
      const inner = h("div", { class: "mx-vinner" });
      for (const b of inputs) for (const d of outputs) {
        const r = rows.find((x) => x.ground === g && x.coupler === c && x.input === b && x.output === d);
        const m = minResidual(rowToCfg(r)).best;
        const heat = 0.08 + 0.42 * (1 - (m - lo) / Math.max(hi - lo, 1e-9));
        const btn = h("button", {
          class: `mx-vbtn${isBaseline(r) ? " baseline" : ""}`, type: "button", "aria-pressed": String(isBaseline(r)),
          title: `ground ${g}, coupler ${c}, input ${b}, output ${d} mm · ${r.poses_closed}/${r.poses_evaluated} poses close · smallest gap ${m.toFixed(1)} mm`,
          "aria-label": `ground ${g}, coupler ${c}, input ${b}, output ${d} millimetres: ${r.poses_closed} of ${r.poses_evaluated} poses close; smallest gap ${m.toFixed(1)} millimetres`,
          onclick: () => {
            buttons.forEach((x) => x.setAttribute("aria-pressed", "false"));
            btn.setAttribute("aria-pressed", "true");
            state.row = r; state.cfg = rowToCfg(r);
            stage?.setConfig(state.cfg);
            stage?.viewTop?.(false);
            update();
            announce(`Loaded ground ${g}, coupler ${c}, input ${b}, output ${d}. ${r.poses_closed} of ${r.poses_evaluated} poses close.`);
          },
        }, `${r.poses_closed}/${r.poses_evaluated}`, h("small", {}, `b${b} d${d}`));
        btn.style.setProperty("--heat", heat.toFixed(3));
        buttons.push(btn);
        inner.append(btn);
      }
      grid.append(h("div", { class: "mx-vcell" }, h("header", {}, h("span", {}, `a ${g} · c ${c}`), h("span", {}, "rows b · cols d")), inner));
    }
  }
  $("#variant-grid").replaceChildren(grid);
  $("#var-note").replaceChildren("Cell text: poses_closed / poses_evaluated, read from ", h("a", { href: repoLink("docs/EVIDENCE/C1_four_bar_sweep.json") }, "C1_four_bar_sweep.json"),
    ". Shading: smallest closure gap over 0–92°, derived here (darker = farther from closing). The copper frame marks the recorded baseline. Click any cell to load it into the stage.");
}

init().then(bindControls).catch((err) => {
  console.error(err);
  $("#main").prepend(h("div", { class: "wrap notice warn", role: "alert" }, `The Mechanism Lab could not load its data: ${err.message}`));
});
