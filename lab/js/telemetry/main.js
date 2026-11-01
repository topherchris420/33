import { mountShell } from "../core/shell.js";
mountShell();

import { h, $, $$, clear, announce, syncRange, reducedMotion, webglAvailable, fixed } from "../core/dom.js";
import { categoryBadge, notMeasured } from "../core/taxonomy.js";
import { lab, canonical, repoLink, docLink, discrepancyLink } from "../core/data.js";
import { eq } from "../core/tex.js";
import { ema, movingAverage, emaTimeConstant, amplitudeSpectrum } from "../core/math/signal.js";
import { fixtureDataset, generatorDataset, GENERATOR_DEFAULTS, intervals, uniformSeries, NOMINAL_PERIOD_MS } from "./datasets.js";
import { LanePlot, drawSpectrum, PLOT_COLORS as PC } from "./plot.js";
import { mountArchitecture, PACKET_LEGEND, NODES } from "./architecture.js";

const state = {
  dataset: "A",
  stream: "T",        // A only: T | LOG | both
  xAxis: "received",  // received | device
  channels: { roll: true, rate: true, servo: true, dt: true },
  filter: "ema",      // none | ema | ma
  alpha: 0.3,
  window: 5,
  showRaw: true,
  band: true,
  truth: false,
  gen: { ...GENERATOR_DEFAULTS },
  replay: { playing: false, t: null, speed: 1 },
};

let fixture, A, B, plot, evidence;

const LANES = () => [
  { id: "roll", label: "roll_deg", unit: "deg", hidden: !state.channels.roll, weight: 1.5 },
  { id: "rate", label: "rate_deg_s", unit: "deg/s", hidden: !state.channels.rate },
  { id: "servo", label: "servo_output", unit: "deg cmd", hidden: !state.channels.servo, weight: 0.8 },
  { id: "dt", label: "Δt between successive rows (device clock)", unit: "ms", hidden: !state.channels.dt, ref: NOMINAL_PERIOD_MS, refLabel: "firmware period 50 ms", weight: 0.75 },
];

function current() { return state.dataset === "A" ? A : B; }

function rowsInView(ds) {
  if (ds.id === "B") return ds.rows;
  if (state.stream === "both") return [...ds.streams.T, ...ds.streams.LOG].sort((a, b) => a.line - b.line);
  return ds.streams[state.stream];
}

function xOf(row) { return state.xAxis === "device" ? row.time_ms : row.received_s; }

function processed(values) {
  if (state.filter === "ema") return ema(values, state.alpha);
  if (state.filter === "ma") return movingAverage(values, state.window);
  return null;
}

function buildPlotData() {
  const ds = current();
  const series = [], missing = [], bars = [], bands = [], markers = [];
  const keys = [["roll", "roll_deg"], ["rate", "rate_deg_s"], ["servo", "servo_output"]];
  const streams = ds.id === "B" ? [["T", ds.rows]] : state.stream === "both" ? [["T", ds.streams.T], ["LOG", ds.streams.LOG]] : [[state.stream, ds.streams[state.stream]]];
  const colors = { T: PC.teal, LOG: PC.ink };
  for (const [name, rows] of streams) {
    for (const [lane, key] of keys) {
      const pts = rows.map((r) => ({ x: xOf(r), y: r[key], order: r.received_s, row: r }));
      if (state.showRaw) series.push({ lane, color: colors[name], width: 1.1, alpha: state.filter === "none" ? 1 : 0.55, points: pts, label: `${name} raw`, stream: name });
      const proc = processed(rows.map((r) => r[key]));
      if (proc) series.push({ lane, color: PC.copper, width: 2, markers: false, points: rows.map((r, i) => ({ x: xOf(r), y: proc[i], order: r.received_s, row: r })), label: `${name} ${state.filter.toUpperCase()}`, stream: name });
      for (const r of rows) if (r[key] !== null && !Number.isFinite(r[key])) missing.push({ lane, x: xOf(r), order: r.received_s, label: `NaN · line ${r.line}` });
    }
    bars.push({ lane: "dt", points: intervals(rows).map(({ at, dt }) => ({ x: xOf(at), y: dt, order: at.received_s, color: dt === null ? PC.red : dt <= 0 ? PC.red : Math.abs(dt - NOMINAL_PERIOD_MS) > 15 ? PC.amber : name === "LOG" ? PC.ink : PC.teal })) });
  }
  if (ds.id === "B") {
    if (state.band || state.truth) {
      const pts = ds.truth.map((tr) => ({ x: state.xAxis === "device" ? tr.t * 1000 : tr.t + 0.004, lo: tr.roll - ds.params.sigmaRoll, hi: tr.roll + ds.params.sigmaRoll, order: tr.t, y: tr.roll }));
      if (state.band) bands.push({ lane: "roll", points: pts, color: "rgba(180,154,216,0.2)" });
      if (state.truth) series.push({ lane: "roll", color: PC.violet, width: 1.2, dash: [4, 3], markers: false, readout: false, points: pts.map((p) => ({ x: p.x, y: p.y, order: p.order })), label: "generator truth" });
    }
    // Packets the generator dropped: knowable only because the data are synthetic.
    const have = new Set(ds.rows.map((r) => r.k));
    for (let k = 0; k < ds.params.samples; k++) if (!have.has(k)) {
      const t = (k * NOMINAL_PERIOD_MS) / 1000;
      missing.push({ lane: "roll", x: state.xAxis === "device" ? k * NOMINAL_PERIOD_MS : t, order: t, color: PC.violet, label: "dropped" });
    }
    markers.push({ x: state.xAxis === "device" ? ds.params.stepTime * 1000 : ds.params.stepTime, color: PC.violet, tag: "t₀" });
  } else {
    ds.annotations.forEach((a, i) => {
      if (!a.row) return;
      const visible = state.stream === "both" || a.row.type === state.stream;
      if (!visible) return;
      markers.push({ x: xOf(a.row), color: a.severity === "error" ? PC.red : PC.amber, tag: String(i + 1), stack: i % 2 });
    });
    if (state.xAxis === "received") for (const ev of ds.events) markers.push({ x: ev.t, color: PC.ink, tag: "R" });
  }
  return { series, missing, bars, bands, markers };
}

function xLabel() {
  if (state.xAxis === "device") return state.dataset === "B" || state.stream === "T" ? "time_ms — launcher relay clock (ms)" : "time_ms — rocket clock (ms)";
  return "received_at — dashboard reception clock (s)";
}

function redraw({ keepView = false } = {}) {
  plot.xLabel = xLabel();
  plot.setLanes(LANES());
  plot.setData(buildPlotData(), { keepView });
  updateReplayBounds();
}

// ---------- side panels ----------

function renderProvenance() {
  const ds = current();
  const el = $("#tt-provenance");
  const inputs = ds.inputs ? Object.entries(ds.inputs) : [];
  clear(el,
    h("div", { class: "panel-head" }, h("h4", {}, "Where this data came from"), categoryBadge("synthetic")),
    h("div", { class: "panel-body" },
      h("p", { class: "tt-origin" }, ds.origin),
      h("dl", { class: "kv" },
        h("dt", {}, "Generator"), h("dd", {}, h("a", { class: "src", href: repoLink(ds.id === "A" ? "evidence/__main__.py" : "lab/js/telemetry/datasets.js") }, ds.generator)),
        h("dt", {}, "Rows"), h("dd", { class: "num" }, String(ds.rows.length)),
        ds.id === "A" ? [h("dt", {}, "Audit quality"), h("dd", {}, h("span", { class: "status status-contradicted" }, ds.audit.quality.toUpperCase()))] : [
          h("dt", {}, "Delivered / dropped / invalid"), h("dd", { class: "num" }, `${ds.stats.delivered} / ${ds.stats.dropped} / ${ds.stats.invalid}`)],
        h("dt", {}, "Physical meaning"), h("dd", {}, "None. Synthetic data can never support a physical or performance claim.")),
      inputs.length ? h("details", { class: "tt-digests" }, h("summary", { class: "label" }, "Input digests (SHA-256)"),
        h("ul", {}, inputs.map(([p, d]) => h("li", {}, h("span", { class: "src" }, p), h("span", { class: "hash" }, ` ${d.slice(0, 16)}…`))))) : null));
}

function renderSide() {
  const el = $("#tt-detail");
  if (state.dataset === "A") {
    const audit = A.audit;
    clear(el,
      h("div", { class: "panel-head" }, h("h4", {}, "Audit findings · evidence/telemetry.py"), categoryBadge("research")),
      h("div", { class: "panel-body" },
        h("p", { class: "small muted" }, "The repository's own audit ran on this file. Numbered rows match the markers on the plot."),
        h("ol", { class: "tt-annos", id: "tt-annos" }, A.annotations.map((a, i) => h("li", {
          class: `audit-anno sev-${a.severity}`, "data-line": a.line, tabindex: "0", role: "button",
          onclick: () => focusRow(a), onkeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); focusRow(a); } },
        }, h("span", { class: "anno-n" }, String(i + 1)), h("span", {}, h("b", { class: "mono" }, a.code), h("small", { class: "mono" }, ` line ${a.line} · ${a.row?.type ?? "—"}`), h("br"), a.text)))),
        h("div", { class: "divider-label" }, h("span", { class: "label" }, "All findings")),
        h("ul", { class: "tt-findings" }, audit.findings.map((f) => h("li", { class: `sev-${f.severity}` }, h("b", { class: "mono" }, f.code), ` × ${f.count}`,
          A.annotations.some((a) => a.code === f.code) ? null : h("small", { class: "muted" }, " — stream-level, no single row")))),
        h("div", { class: "divider-label" }, h("span", { class: "label" }, "Streams")),
        h("table", { class: "data tt-streams" }, h("thead", {}, h("tr", {}, ["stream", "clock domain", "valid", "median Δt"].map((t) => h("th", {}, t)))),
          h("tbody", {}, audit.streams.map((s) => h("tr", {}, h("td", { class: "mono" }, s.message_type), h("td", { class: "mono small" }, s.clock_domain), h("td", { class: "num" }, String(s.valid_samples)), h("td", { class: "num" }, `${s.median_positive_interval_ms} ms`))))),
        h("p", { class: "small" }, "Log dump: announced ", h("b", {}, String(audit.log_dumps[0].announced)), ", received ", h("b", {}, String(audit.log_dumps[0].received)), `, state ${audit.log_dumps[0].state}.`)));
  } else {
    const p = state.gen;
    const ctl = (id, label, min, max, step, unit, fmt = (v) => v) => {
      const input = h("input", { type: "range", id: `gen-${id}`, min, max, step, value: p[id], "aria-label": label.replace(" | ", " ") });
      const out = h("output", { for: `gen-${id}` }, `${fmt(p[id])} ${unit}`);
      input.addEventListener("input", () => { p[id] = Number(input.value); out.textContent = `${fmt(p[id])} ${unit}`; regenerate(); });
      syncRange(input);
      const [word, sym] = label.split(" | ");
      return h("div", { class: "field" }, h("div", { class: "field-row" }, h("label", { for: `gen-${id}`, class: "label" }, word, sym ? h("span", { class: "nocase" }, ` ${sym}`) : null), out), input);
    };
    const seed = h("input", { type: "number", id: "gen-seed", value: p.seed, min: 0, max: 2 ** 31 - 1, step: 1, "aria-label": "Generator seed" });
    seed.addEventListener("change", () => { p.seed = Math.max(0, Math.floor(Number(seed.value) || 0)); seed.value = p.seed; regenerate(); announce(`Seed ${p.seed}: dataset regenerated`); });
    clear(el,
      h("div", { class: "panel-head" }, h("h4", {}, "Declared generator"), categoryBadge("synthetic")),
      h("div", { class: "panel-body" },
        h("p", { class: "small" }, h("b", {}, "Software-generated test data; models no hardware. "), "Same seed, same rows, in every browser. Gains are illustrative, not firmware values."),
        h("div", { class: "field" }, h("div", { class: "field-row" }, h("label", { for: "gen-seed", class: "label" }, "Seed"), seed)),
        ctl("sigmaRoll", "Roll noise | σφ", 0, 2, 0.05, "deg", (v) => Number(v).toFixed(2)),
        ctl("jitterMs", "Relay jitter | J", 0, 40, 1, "ms"),
        ctl("dropProb", "Drop probability", 0, 0.2, 0.005, "", (v) => Number(v).toFixed(3)),
        ctl("nanProb", "Invalid-value probability", 0, 0.05, 0.001, "", (v) => Number(v).toFixed(3)),
        ctl("quantum", "Roll resolution | q", 0.01, 1, 0.01, "deg", (v) => Number(v).toFixed(2)),
        h("div", { class: "divider-label" }, h("span", { class: "label" }, "Generator equations")),
        eq("\\varphi(t)=A_d\\sin(2\\pi f_d t)+H(t-t_0)\\,A\\,e^{-(t-t_0)/\\tau}\\cos\\!\\big(2\\pi f_1 (t-t_0)\\big)"),
        eq("\\tilde\\varphi_k=q\\,\\operatorname{round}\\!\\left(\\frac{\\varphi(kT)+\\sigma_\\varphi n_k}{q}\\right),\\quad n_k\\sim\\mathcal N(0,1)"),
        eq("t^{\\text{relay}}_k=kT+u_k,\\quad u_k\\sim\\mathcal U(0,J),\\quad T=50\\ \\text{ms}"),
        eq("u^{\\text{servo}}_k=\\operatorname{clamp}\\!\\big(-(K_p\\tilde\\varphi_k+K_d\\tilde p_k),\\ \\pm 12^\\circ\\big)"),
        h("dl", { class: "vars" },
          [["A", `${p.amplitude}° disturbance amplitude`], ["τ", `${p.tau} s decay time constant`], ["f₁", `${p.dampedHz} Hz response oscillation`],
          ["A_d, f_d", `${p.driftAmp}°, ${p.driftHz} Hz slow disturbance`], ["t₀", `${p.stepTime} s onset`], ["σ_p", `${p.sigmaRate} °/s rate noise`],
          ["K_p, K_d", `${p.kp}, ${p.kd} (illustrative)`], ["12°", "max deflection, ground_status_model.json firmware_limits"]].flatMap(([k, v]) => [h("dt", {}, k), h("dd", {}, v)]))));
  }
}

function focusRow(a) {
  if (!a.row) return;
  if (state.stream !== "both" && a.row.type !== state.stream) { state.stream = a.row.type; syncControls(); redraw(); }
  const x = xOf(a.row), span = state.xAxis === "device" ? 400 : 0.16;
  plot.zoomTo(x - span / 2, x + span / 2);
  showReadout([{ series: { label: a.row.type, color: PC.copper }, point: { row: a.row } }]);
  announce(`Zoomed to line ${a.line}: ${a.code}`);
}

function showReadout(samples) {
  const el = $("#tt-readout");
  if (!samples.length) { el.textContent = "Hover the plot for a sample readout. Wheel to zoom, drag to pan, double-click to reset."; return; }
  const row = samples.find((s) => s.point.row)?.point.row;
  if (!row) { el.textContent = ""; return; }
  const v = (x) => (x === null ? "—" : Number.isFinite(x) ? fixed(x, 2) : "NaN (excluded)");
  clear(el, h("span", { class: "mono" }, `line ${row.line}`), " · ", h("b", { class: "mono" }, row.type), ` · time_ms ${row.time_ms ?? "—"} · roll ${v(row.roll_deg)} · rate ${v(row.rate_deg_s)} · servo ${v(row.servo_output)} · `, h("code", {}, row.raw));
}

// ---------- spectrum ----------

function renderSpectrum() {
  const panel = $("#tt-fft");
  const canvas = $("#fft-canvas");
  if (state.dataset !== "B") { panel.dataset.disabled = "true"; $("#fft-note").textContent = "Spectral analysis needs a uniformly sampled record. The 9-row fixture is too short and irregular; switch to dataset B."; canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height); return; }
  panel.dataset.disabled = "false";
  const fs = 1000 / NOMINAL_PERIOD_MS;
  const raw = uniformSeries(B, "roll_deg");
  const spectra = [{ data: amplitudeSpectrum(raw, fs), color: PC.teal, label: "raw" }];
  const proc = processed(raw);
  if (proc) spectra.push({ data: amplitudeSpectrum(proc, fs), color: PC.copper, width: 1.8, label: state.filter });
  if (state.truth) spectra.push({ data: amplitudeSpectrum(B.truth.map((t) => t.roll), fs), color: PC.violet, alpha: 0.8, label: "truth" });
  drawSpectrum(canvas, spectra, { nyquist: fs / 2, refs: [
    { hz: B.params.driftHz, label: `f_d ${B.params.driftHz} Hz`, color: PC.violet, row: 0 },
    { hz: B.params.dampedHz, label: `f₁ ${B.params.dampedHz} Hz`, color: PC.violet, row: 1 },
    { hz: fs / 2, label: "Nyquist 10 Hz", color: PC.amber, row: 2 }] });
  $("#fft-note").textContent = `Hann-windowed amplitude spectrum of roll at the nominal ${fs} Hz. Dropped and invalid samples are bridged linearly for this panel only, and relay jitter is ignored — both are stated assumptions, not properties of the data.`;
}

// ---------- replay ----------

function updateReplayBounds() {
  const ds = current();
  const max = Math.max(...ds.rows.map((r) => r.received_s));
  const scrub = $("#replay-scrub");
  scrub.max = String(max);
  scrub.step = String(max / 400);
  if (state.replay.t === null) { scrub.value = scrub.max; } else scrub.value = String(state.replay.t);
  syncRange(scrub);
  $("#replay-time").textContent = `${fixed(Number(scrub.value), 3)} / ${fixed(max, 3)} s`;
}

let rafId = 0, lastNow = 0;
function setPlaying(on) {
  state.replay.playing = on;
  const btn = $("#replay-play");
  btn.setAttribute("aria-pressed", String(on));
  btn.textContent = on ? "Pause" : "Play";
  cancelAnimationFrame(rafId);
  if (on) {
    const max = Number($("#replay-scrub").max);
    if (state.replay.t === null || state.replay.t >= max) state.replay.t = 0;
    lastNow = performance.now();
    const step = (now) => {
      const dt = (now - lastNow) / 1000; lastNow = now;
      state.replay.t = Math.min(state.replay.t + dt * state.replay.speed, max);
      applyReplay();
      if (state.replay.t >= max) { setPlaying(false); return; }
      rafId = requestAnimationFrame(step);
    };
    rafId = requestAnimationFrame(step);
  }
}

function applyReplay() {
  const t = state.replay.t;
  plot.revealUntil = t;
  plot.playhead = state.xAxis === "received" ? t : null;
  const scrub = $("#replay-scrub");
  if (t !== null) scrub.value = String(t);
  syncRange(scrub);
  $("#replay-time").textContent = `${fixed(Number(scrub.value), 3)} / ${fixed(Number(scrub.max), 3)} s`;
  const shown = current().rows.filter((r) => t === null || r.received_s <= t + 1e-9).length;
  $("#replay-count").textContent = `${shown} of ${current().rows.length} rows received`;
  plot.render();
}

// ---------- controls ----------

function syncControls() {
  for (const b of $$("[data-dataset]")) b.setAttribute("aria-pressed", String(b.dataset.dataset === state.dataset));
  for (const b of $$("[data-stream]")) { b.setAttribute("aria-pressed", String(b.dataset.stream === state.stream)); b.disabled = state.dataset === "B"; }
  for (const b of $$("[data-xaxis]")) b.setAttribute("aria-pressed", String(b.dataset.xaxis === state.xAxis));
  $("[data-xaxis='device']").disabled = state.dataset === "A" && state.stream === "both";
  for (const b of $$("[data-filter]")) b.setAttribute("aria-pressed", String(b.dataset.filter === state.filter));
  for (const b of $$("[data-channel]")) b.setAttribute("aria-pressed", String(state.channels[b.dataset.channel]));
  $("#opt-raw").setAttribute("aria-pressed", String(state.showRaw));
  $("#opt-band").setAttribute("aria-pressed", String(state.band));
  $("#opt-truth").setAttribute("aria-pressed", String(state.truth));
  $("#opt-band").disabled = state.dataset !== "B";
  $("#opt-truth").disabled = state.dataset !== "B";
  $("#alpha-field").hidden = state.filter !== "ema";
  $("#window-field").hidden = state.filter !== "ma";
  $("#dataset-title").textContent = current().title;
  $("#dataset-tag").textContent = state.dataset;
  $("#tau-out").textContent = `α ${state.alpha.toFixed(2)} · τ = ${(emaTimeConstant(state.alpha, NOMINAL_PERIOD_MS / 1000) * 1000).toFixed(0)} ms at T = 50 ms`;
  document.body.dataset.dataset = state.dataset;
}

function regenerate() {
  B = generatorDataset(state.gen);
  if (state.dataset === "B") { redraw({ keepView: true }); renderProvenance(); renderSpectrum(); applyReplay(); }
}

function bindControls() {
  for (const b of $$("[data-dataset]")) b.addEventListener("click", () => {
    state.dataset = b.dataset.dataset; state.replay.t = null; setPlaying(false);
    if (state.dataset === "B") state.xAxis = state.xAxis; // B has one stream (T)
    if (state.dataset === "A" && state.speedTouched !== true) { state.replay.speed = 0.1; $("#replay-speed").value = "0.1"; }
    if (state.dataset === "B" && state.speedTouched !== true) { state.replay.speed = 1; $("#replay-speed").value = "1"; }
    syncControls(); redraw(); renderProvenance(); renderSide(); renderSpectrum(); applyReplay();
    announce(`Dataset ${state.dataset}: ${current().title}`);
  });
  for (const b of $$("[data-stream]")) b.addEventListener("click", () => {
    state.stream = b.dataset.stream;
    if (state.stream === "both") state.xAxis = "received";
    syncControls(); redraw(); applyReplay();
  });
  for (const b of $$("[data-xaxis]")) b.addEventListener("click", () => { state.xAxis = b.dataset.xaxis; syncControls(); redraw(); applyReplay(); announce(`X axis: ${xLabel()}`); });
  for (const b of $$("[data-filter]")) b.addEventListener("click", () => { state.filter = b.dataset.filter; syncControls(); redraw({ keepView: true }); renderSpectrum(); applyReplay(); });
  for (const b of $$("[data-channel]")) b.addEventListener("click", () => { state.channels[b.dataset.channel] = !state.channels[b.dataset.channel]; syncControls(); redraw({ keepView: true }); applyReplay(); });
  $("#opt-raw").addEventListener("click", () => { state.showRaw = !state.showRaw; syncControls(); redraw({ keepView: true }); applyReplay(); });
  $("#opt-band").addEventListener("click", () => { state.band = !state.band; syncControls(); redraw({ keepView: true }); applyReplay(); });
  $("#opt-truth").addEventListener("click", () => { state.truth = !state.truth; syncControls(); redraw({ keepView: true }); renderSpectrum(); applyReplay(); });
  const alpha = $("#alpha");
  alpha.addEventListener("input", () => { state.alpha = Number(alpha.value); syncControls(); redraw({ keepView: true }); renderSpectrum(); applyReplay(); });
  syncRange(alpha);
  const win = $("#window");
  win.addEventListener("input", () => { state.window = Number(win.value); $("#window-out").textContent = `${state.window} samples`; redraw({ keepView: true }); renderSpectrum(); applyReplay(); });
  syncRange(win);
  $("#zoom-in").addEventListener("click", () => plot.zoom(1 / 1.5));
  $("#zoom-out").addEventListener("click", () => plot.zoom(1.5));
  $("#zoom-reset").addEventListener("click", () => plot.reset());
  $("#replay-play").addEventListener("click", () => setPlaying(!state.replay.playing));
  $("#replay-scrub").addEventListener("input", (e) => { setPlaying(false); state.replay.t = Number(e.target.value); applyReplay(); });
  $("#replay-end").addEventListener("click", () => { setPlaying(false); state.replay.t = null; plot.revealUntil = null; plot.playhead = null; updateReplayBounds(); applyReplay(); });
  $("#replay-speed").addEventListener("change", (e) => { state.replay.speed = Number(e.target.value); state.speedTouched = true; });
}

// ---------- static sections ----------

function renderKinds() {
  const v = evidence.vocabulary.evidence_classes;
  const c = evidence.counts;
  const card = (title, cls, meaning, here, badge) => h("article", { class: "panel ticked tt-kind" },
    h("div", { class: "panel-body" },
      h("p", { class: "label" }, cls), h("h3", {}, title),
      h("p", { class: "small muted" }, meaning), h("div", { class: "rule" }), here, badge));
  clear($("#kinds"),
    card("Physical measurement", "bench_measured · bench_observed", v.bench_measured.meaning,
      h("p", {}, "In this repository: ", h("b", { class: "num" }, String(c.accepted_physical_measurements)), " accepted inert measurements. Every physical quantity is ", notMeasured(), "."), categoryBadge("research")),
    card("Simulation", "simulated · analytical", v.simulated.meaning,
      h("p", {}, "Example: the C7 deployment-reliability sweep reports 10,000 of 10,000 successes — but it cannot generate the failures it counts (", h("a", { href: discrepancyLink("D-013") }, "D-013"), ")."), categoryBadge("research")),
    card("Software-generated test data", "synthetic", v.synthetic.meaning,
      h("p", {}, "Both datasets on this page. They exercise the audit and the plots; they say nothing about hardware."), categoryBadge("synthetic")));
}

function renderLimitations() {
  clear($("#tt-limitations"), A.audit.limitations.map((l) => h("li", {}, l)));
}

function renderClockDiagram() {
  const svg = `<svg viewBox="0 0 620 170" role="img" aria-label="Clock domains: rocket samples are stamped by the rocket clock only in LOG rows; live T packets are stamped by the launcher clock at relay">
  <defs><marker id="ar" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 8 4 0 8z" fill="#67d8cf"/></marker></defs>
  <g font-family="Plex Mono, monospace" font-size="10.5" fill="#8fa2ad">
    <text x="0" y="22">ROCKET millis()</text><text x="0" y="82">LAUNCHER millis()</text><text x="0" y="142">DASHBOARD received_at</text>
  </g>
  <g stroke="#33434f"><line x1="150" y1="18" x2="610" y2="18"/><line x1="150" y1="78" x2="610" y2="78"/><line x1="150" y1="138" x2="610" y2="138"/></g>
  ${[0, 1, 2, 3, 4, 5, 6].map((i) => { const x = 170 + i * 62; const j = [6, 13, 4, 18, 9, 3, 15][i]; return `<circle cx="${x}" cy="18" r="3.5" fill="#f1e9d6"/><line x1="${x}" y1="22" x2="${x + j}" y2="74" stroke="#67d8cf" marker-end="url(#ar)" stroke-width="1.2"/><circle cx="${x + j}" cy="78" r="3.5" fill="#67d8cf"/><line x1="${x + j}" y1="82" x2="${x + j + 7}" y2="134" stroke="#4c5f6c" stroke-width="1"/><circle cx="${x + j + 7}" cy="138" r="3" fill="#8fa2ad"/>`; }).join("")}
  <g font-family="Plex Mono, monospace" font-size="10" fill="#e0a274"><text x="150" y="48">DATA line carries no rocket timestamp →</text><text x="150" y="108">T,&lt;launcher ms&gt;,… stamped at relay (UART + loop delay)</text></g>
</svg>`;
  $("#clock-diagram").innerHTML = svg;
}

// ---------- boot ----------

async function boot() {
  [fixture, evidence] = await Promise.all([lab.telemetryFixture(), lab.evidence()]);
  A = fixtureDataset(fixture);
  B = generatorDataset(state.gen);
  window.__p33telemetry = { state, get A() { return A; }, get B() { return B; }, get plot() { return plot; } };
  renderKinds();
  renderLimitations();
  renderClockDiagram();
  plot = new LanePlot($("#plot"), { lanes: LANES(), xLabel: xLabel(), onCursor: (x, samples) => showReadout(samples) });
  state.replay.speed = 0.1;
  $("#replay-speed").value = "0.1";
  bindControls();
  syncControls();
  redraw();
  renderProvenance();
  renderSide();
  renderSpectrum();
  showReadout([]);
  applyReplay();
  $("#legend-packets").append(...PACKET_LEGEND.map(([k, c, d]) => h("li", {}, h("span", { class: "swatch", style: { background: c } }), h("b", { class: "mono" }, k), " ", h("span", { class: "muted" }, d))));
  window.addEventListener("resize", () => renderSpectrum());
  document.body.dataset.ready = "plots";
  // Architecture
  const vp = $("#arch-viewport");
  if (!webglAvailable()) {
    vp.replaceChildren(h("div", { class: "fallback-2d" }, h("p", {}, "WebGL is unavailable, so the 3D diagram cannot run. The documented nodes are listed here instead."),
      h("ul", { class: "arch-list" }, NODES.map((n) => h("li", {}, h("b", {}, n.name), ` — ${n.iface}. `, n.duties.join("; "))))));
  }
  const [gates, gs] = await Promise.all([canonical.safetyGates(), canonical.groundStatus()]);
  if (webglAvailable()) {
    try {
      mountArchitecture({ viewport: vp, inspector: $("#arch-inspector"), nodeList: $("#arch-nodes"),
        toggles: { pulses: $("#arch-pulses"), commands: $("#arch-commands"), reset: $("#arch-reset") }, safetyGates: gates, groundStatus: gs });
    } catch (err) {
      console.warn("architecture view failed", err);
      vp.replaceChildren(h("div", { class: "fallback-2d" }, h("p", {}, "The 3D diagram could not start on this device.")));
    }
  }
  document.body.dataset.ready = "true";
}

boot().catch((err) => {
  console.error(err);
  $("#main").prepend(h("div", { class: "notice warn wrap" }, `The theater could not load its data: ${err.message}`));
});
