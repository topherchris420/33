// Information architecture: from a raw observation to an operator's interpretation, for three
// synthetic sources. Each source can be put into one of five states; every stage of the
// pipeline, the generic display preview, and the cockpit exhibit react to it.
import { h, clear, announce } from "../core/dom.js";
import { drawPreview } from "./symbology.js";

export const STATES = ["nominal", "missing", "stale", "inconsistent", "unavailable"];
export const STATE_LABEL = { nominal: "Nominal", missing: "Missing", stale: "Stale", inconsistent: "Inconsistent", unavailable: "Unavailable" };
export const STAGES = ["Measurement", "Validation", "Estimate", "Display", "Alert", "Operator"];

export const SOURCES = {
  airdata: {
    name: "Air data", short: "ADC",
    observation: "static and total pressure p_s, p_t",
    estimate: "airspeed, barometric altitude",
    validity: 0.5,
  },
  inertial: {
    name: "Inertial reference", short: "IRS",
    observation: "body angular rates ω, specific force f",
    estimate: "attitude θ, φ and heading ψ",
    validity: 0.1,
  },
  gnss: {
    name: "Satellite navigation", short: "GNSS",
    observation: "pseudoranges ρ_i to tracked satellites",
    estimate: "position and its integrity bound",
    validity: 2.0,
  },
};

/** What each pipeline stage holds for a source in a given state. */
export function stageText(id, state, age) {
  const s = SOURCES[id];
  const T = {
    nominal: [`${s.observation} sampled this cycle`, "range, rate-of-change and age checks pass", `${s.estimate} with a stated uncertainty`, "value drawn normally", "none", "uses the value, keeps cross-checking"],
    missing: ["expected sample did not arrive this cycle", "no new sample to check", "previous estimate carried for one cycle", "dashes, or held value if within its validity window", "none yet — a single gap is normal", "notices only if it persists"],
    stale: [`last valid sample ${age.toFixed(1)} s old`, `age ${age.toFixed(1)} s > validity window ${s.validity} s → STALE`, "last valid estimate, uncertainty growing", "value shown amber with its age", `CAUTION · ${s.short} DATA AGED`, "treats value as history, not the present"],
    inconsistent: ["samples arrive and pass individual checks", `independent sources differ beyond threshold δ`, "two estimates — the system cannot tell which is right", "both values or a comparator flag", `CAUTION · ${s.short} DISAGREE`, "must decide which source to trust (standby, other cues)"],
    unavailable: ["no output: source failed or never initialised", "source declared invalid", "no estimate exists", "symbol removed, failure flag shown", `WARNING · ${s.short} FAIL`, "knows the information is gone — and must not imagine it"],
  };
  return T[state];
}

export function messagesFor(sources) {
  const out = [];
  for (const [id, src] of Object.entries(sources)) {
    const t = stageText(id, src.state, src.age)[4];
    if (t !== "none" && !t.startsWith("none")) out.push({ kind: t.startsWith("WARNING") ? "warning" : "caution", text: t.replace(/ · /, " ") });
  }
  out.push({ kind: "advisory", text: "ADVISORY NAV INTEGRITY NORMAL" }, { kind: "status", text: "STATUS DISPLAY 2 PRIMARY" }, { kind: "status", text: "STATUS FUEL BALANCE OK" });
  if (sources.gnss.state !== "nominal") out[out.length - 3].text = "ADVISORY NAV INTEGRITY REDUCED";
  return out;
}

export function mountInfoArch({ root, preview, store }) {
  const rows = {};
  const controls = h("div", { class: "ia-controls" });
  for (const [id, s] of Object.entries(SOURCES)) {
    const seg = h("div", { class: "seg ia-seg", role: "group", "aria-label": `${s.name} state` },
      STATES.map((st) => h("button", { class: "btn", type: "button", "data-source": id, "data-state": st, "aria-pressed": String(st === "nominal"),
        onclick: () => { store.setSource(id, st); announce(`${s.name}: ${STATE_LABEL[st]}`); } }, STATE_LABEL[st])));
    controls.append(h("div", { class: "ia-source" }, h("div", { class: "ia-source-name" }, h("b", {}, s.name), h("small", { class: "muted" }, ` → ${s.estimate}`)), seg));
  }
  const grid = h("div", { class: "ia-grid", role: "table", "aria-label": "Information pipeline per source" },
    h("div", { class: "ia-row ia-head", role: "row" }, h("div", { role: "columnheader" }, ""), STAGES.map((st, i) => h("div", { role: "columnheader", class: "ia-stage-h" }, h("span", { class: "ia-n" }, String(i + 1)), st))));
  for (const [id, s] of Object.entries(SOURCES)) {
    const cells = STAGES.map((_, i) => h("div", { class: "ia-cell", role: "cell", "data-stage": i }));
    const row = h("div", { class: "ia-row", role: "row", "data-source": id }, h("div", { class: "ia-rowhead", role: "rowheader" }, s.name), cells);
    rows[id] = { row, cells };
    grid.append(row);
  }
  root.append(controls, grid);

  const ctx = preview.getContext("2d");
  function paint() {
    const st = store.get();
    for (const [id, { row, cells }] of Object.entries(rows)) {
      const src = st.sources[id];
      row.dataset.state = src.state;
      const texts = stageText(id, src.state, src.age);
      cells.forEach((c, i) => clear(c, texts[i]));
    }
    for (const b of root.querySelectorAll("button[data-source]")) b.setAttribute("aria-pressed", String(st.sources[b.dataset.source].state === b.dataset.state));
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = preview.clientWidth || 420, hh = preview.clientHeight || 260;
    if (preview.width !== Math.round(w * dpr)) { preview.width = Math.round(w * dpr); preview.height = Math.round(hh * dpr); }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    drawPreview(ctx, w, hh, st.displayState, st.sources);
  }
  store.subscribe(paint);
  paint();
  return { paint, tick() { paint(); } };
}
