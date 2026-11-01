// Model Comparison Studio. Conflicting calculations on record, side by side, with their
// assumptions. Nothing here picks a winner; requirement results come from evidence.json.
import { h } from "../core/dom.js";
import { lab, canonical, repoLink, discrepancyLink, claimLink, parseCSV } from "../core/data.js";
import { categoryBadge, statusChip, notMeasured } from "../core/taxonomy.js";
import { eq } from "../core/tex.js";
import { elevationPaths, rocketParts } from "../core/rocket-geometry.js";
import { caliberAxis, stabilityElevation, marginGauge, logBars, planformOverlay } from "./charts.js";

const M = 1000;

function panel(title, { wide = false, badge = "research", id } = {}, ...body) {
  return h("section", { class: `panel ticked${wide ? " wide" : ""}`, id, "aria-label": title },
    h("div", { class: "panel-head" }, h("h4", {}, title), categoryBadge(badge)),
    h("div", { class: "panel-body" }, ...body));
}

function reqLine(r) {
  return h("div", { class: "mx-reqs" }, h("div", { class: "req" }, h("b", {}, r.id), h("span", { class: `res ${r.result}` }, `${r.label}${r.evidence_class ? ` (${r.evidence_class})` : ""}`), h("span", {}, r.text)));
}

function discBlock(d) {
  return h("div", { class: "mx-disc" },
    h("header", {}, h("a", { href: discrepancyLink(d.id) }, `${d.id} · ${d.title}`), h("span", { class: "label" }, `${d.status} · ${d.kind.replaceAll("_", " ")}`)),
    h("div", { class: "mx-sides" }, d.sides.map((sd) => h("div", { class: "mx-side" }, h("b", {}, sd.artifact || sd.path), h("span", {}, sd.says)))),
    d.next_action ? h("p", { class: "muted mb0", style: { fontSize: "12px", marginTop: "6px" } }, "Next action on record: ", d.next_action) : null);
}

export async function buildComparison(root, { ev }) {
  const [or, cross, inputs, csvText, c6] = await Promise.all([
    lab.openrocket(), canonical.c5Crosscheck(), canonical.c5Inputs(), canonical.c5Csv(), canonical.c6DesignPoint(),
  ]);
  const disc = Object.fromEntries(ev.discrepancies.map((d) => [d.id, d]));
  const req = Object.fromEntries(ev.requirements.map((r) => [r.id, r]));
  const claim = Object.fromEntries(ev.claims.map((c) => [c.id, c]));
  const csv = parseCSV(csvText).map((r) => ({ t: +r.time_s, cg: +r.cg_m, cp: +r.cp_m, sm: +r.sm_calibers }));
  const smMin = Math.min(...csv.map((r) => r.sm)), smMax = Math.max(...csv.map((r) => r.sm));
  const cgMin = Math.min(...csv.map((r) => r.cg)), cgMax = Math.max(...csv.map((r) => r.cg));
  const win = req["R-C5-WINDOW"].bound;
  const obs = or.lab_observations.find((o) => o.id === "LAB-OBS-1");
  const elevation = elevationPaths(or, "current");
  const aft = elevation.parts.filter((p) => p.kind === "trapezoidfinset").reduce((m, p) => (p.span > (m?.span ?? 0) ? p : m), null);
  const dRef = or.current.reference_diameter_m * M;

  /* ---------------- C5 ---------------- */
  const stations = [
    { min: cgMin * M, max: cgMax * M, color: "#f1e9d6", symbol: "cg", label: `CG ${(cgMin * M).toFixed(0)}–${(cgMax * M).toFixed(0)} mm · C5_static_margin.csv cg_m (burn history, hard-coded Estes C6-5 — D-007)` },
    { min: inputs.cp_m * M, color: "#67d8cf", symbol: "cp", label: `CP reference ${(inputs.cp_m * M).toFixed(1)} mm · C5_static_margin_inputs.json cp_m` },
    { min: cross.cp_m * M, color: "#e3c27a", symbol: "cp", label: `CP textbook ${(cross.cp_m * M).toFixed(1)} mm · C5_barrowman_crosscheck.json cp_m` },
    { min: cgMin * M + win.min * dRef, max: cgMax * M + win.max * dRef, color: "#4cc9bb", dashed: true, label: `CP that would meet ${win.min}–${win.max} cal for this CG: x_CG + [${win.min}, ${win.max}]·d_ref (derived, d_ref ${dRef.toFixed(1)} mm)` },
    { min: obs.values_m.static_margin_inputs_X_f * M, color: "#e0a274", dashed: true, top: aft.rootRadius + aft.span, label: `fin LE X_f = ${(obs.values_m.static_margin_inputs_X_f * M).toFixed(0)} mm as read by static_margin.py` },
    { min: obs.values_m.ork_semantics * M, color: "#eef6f8", top: aft.rootRadius + aft.span, label: `fin LE ${(obs.values_m.ork_semantics * M).toFixed(0)} mm by OpenRocket "${aft.axialMethod}" semantics (LAB-OBS-1)` },
  ];
  const ghost = { x0: obs.values_m.static_margin_inputs_X_f * M, r: aft.rootRadius, sweep: aft.sweep, span: aft.span, tip: aft.tipChord, root: aft.rootChord, label: "fin where static_margin.py places it" };

  const refCard = h("div", { class: "mx-model-card ref" },
    h("h5", {}, "Reference formulation"), h("span", { class: "src" }, "Simulation/static_margin.py"),
    eq(String.raw`X_F = X_f + \frac{{\color{#67d8cf}C_R}}{3}\,\frac{C_R + 2C_T}{C_R + C_T} + \frac{1}{6}\Bigl[(C_R + C_T) - \frac{C_R C_T}{C_R + C_T}\Bigr]`),
    eq(String.raw`C_{N,F} = \Bigl(1 + \frac{R}{R+S}\Bigr)\frac{4N\,(S/d)^2}{1 + \sqrt{1 + \bigl(2\,{\color{#67d8cf}L_f}/(C_R + C_T)\bigr)^2}}`),
    h("p", { class: "mx-note mb0" }, `L_f read from sweeplength = ${inputs.geometry.L_f_sweeplength} m. Result ${smMin.toFixed(2)}–${smMax.toFixed(2)} cal (C5_static_margin.csv).`));
  const tbCard = h("div", { class: "mx-model-card tb" },
    h("h5", {}, "Textbook Barrowman cross-check"), h("span", { class: "src" }, "Simulation/barrowman_crosscheck.py"),
    eq(String.raw`X_F = X_f + \frac{{\color{#e3c27a}X_R}}{3}\,\frac{C_R + 2C_T}{C_R + C_T} + \frac{1}{6}\Bigl[(C_R + C_T) - \frac{C_R C_T}{C_R + C_T}\Bigr]`),
    eq(String.raw`C_{N,F} = \Bigl(1 + \frac{R}{R+S}\Bigr)\frac{4N\,(S/d)^2}{1 + \sqrt{1 + \bigl(2\,{\color{#e3c27a}L_F}/(C_R + C_T)\bigr)^2}},\quad L_F = \sqrt{S^2 + \bigl(X_R + \tfrac{C_T}{2} - \tfrac{C_R}{2}\bigr)^2}`),
    h("p", { class: "mx-note mb0" }, `L_F = ${cross.midchord_length_m} m (midchord_length_m). Result ${cross.sm_min_calibers.toFixed(2)}–${cross.sm_max_calibers.toFixed(2)} cal. Status on record: “${cross.status}”.`));
  const g = inputs.geometry;
  const varList = h("dl", { class: "vars" },
    h("dt", {}, "X_f"), h("dd", {}, `fin root leading-edge station from the nose tip — ${g.X_f} m in both scripts (see LAB-OBS-1)`),
    h("dt", {}, "X_R"), h("dd", {}, `tip leading-edge sweep distance — sweeplength ${g.L_f_sweeplength} m`),
    h("dt", {}, "C_R, C_T"), h("dd", {}, `root and tip chord — ${g.C_R} m, ${g.C_T} m`),
    h("dt", {}, "S"), h("dd", {}, `fin span (height) — ${g.S} m`),
    h("dt", {}, "d, R"), h("dd", {}, `reference diameter and body radius at the fins — ${g.d_ref} m, ${g.d_ref / 2} m`),
    h("dt", {}, "N"), h("dd", {}, "fin count — 4"));

  root.append(panel("C5 · Static margin: two formulations, one requirement", { wide: true, id: "cmp-c5" },
    h("div", { class: "cluster", style: { marginBottom: "10px" } },
      h("a", { href: claimLink("C5") }, "Claim C5"), statusChip(claim.C5.status, claim.C5.status_label),
      h("span", { class: "label" }, `support ${claim.C5.support_label}`)),
    reqLine(req["R-C5-WINDOW"]),
    h("div", { class: "mx-scroll" }, caliberAxis({ window: win, reference: { min: smMin, max: smMax }, textbook: { min: cross.sm_min_calibers, max: cross.sm_max_calibers } })),
    h("p", { class: "mx-note" }, "Both formulations are on record and share every input except the fin term. The requirement result is MODELS DISAGREE; neither model has been independently reviewed, so neither is declared correct. A static margin is not dynamic stability or flight readiness."),
    h("h4", { style: { marginTop: "18px" } }, "Where the stations fall on the OpenRocket geometry"),
    h("div", { class: "mx-scroll" }, stabilityElevation({ elevation, stations, ghostFin: ghost, dRef })),
    h("p", { class: "mx-note" }, "Side elevation generated from the parameters in Simulation/Folding Stabilized Rocket.ork (fins shown in the upper half only). Stations are millimetres from the nose tip."),
    h("div", { class: "mx-two", style: { marginTop: "14px" } }, refCard, tbCard),
    h("h4", { style: { marginTop: "14px" } }, "Variables"), varList,
    h("div", { class: "mx-two", style: { marginTop: "8px" } },
      h("div", {}, h("h4", {}, "Shared by both (crosscheck record)"), h("ul", {}, cross.shared_with_reference.map((x) => h("li", {}, x)))),
      h("div", {}, h("h4", {}, "Differs (crosscheck record)"), h("ul", {}, cross.differs_from_reference_in.map((x) => h("li", {}, x))),
        h("h4", {}, "Formula notes (inputs record)"), h("ul", {}, inputs.formula_notes.map((x) => h("li", {}, x))))),
    h("div", { class: "mx-obs", style: { margin: "14px 0" } },
      h("div", { class: "cluster" }, h("span", { class: "flag" }, "Candidate for human review · not in the discrepancy register"), categoryBadge("research")),
      h("h3", { style: { margin: "8px 0" } }, `${obs.id}: ${obs.title}`),
      h("p", {}, obs.detail),
      h("table", { class: "data" },
        h("thead", {}, h("tr", {}, h("th", {}, "Quantity"), h("th", { class: "num" }, "Value (m)"), h("th", {}, "Source"))),
        h("tbody", {},
          h("tr", {}, h("td", {}, "Fin LE station by OpenRocket semantics"), h("td", { class: "num mono" }, obs.values_m.ork_semantics.toFixed(3)), h("td", { class: "src" }, "Simulation/Folding Stabilized Rocket.ork → lab/data/openrocket.json")),
          h("tr", {}, h("td", {}, "X_f recorded by static_margin.py"), h("td", { class: "num mono" }, obs.values_m.static_margin_inputs_X_f.toFixed(3)), h("td", { class: "src" }, "docs/EVIDENCE/C5_static_margin_inputs.json")),
          h("tr", {}, h("td", {}, "Difference"), h("td", { class: "num mono" }, obs.values_m.difference.toFixed(3)), h("td", {}, "arithmetic")))),
      h("p", { class: "mb0", style: { marginTop: "8px" } }, h("b", {}, "Not computed here. "), obs.not_computed),
      h("p", { class: "muted mb0", style: { fontSize: "12px" } }, `Status: ${obs.status}. Related: ${obs.related.join(", ")}.`)),
    ...["D-006", "D-007", "D-008"].map((id) => discBlock(disc[id]))));

  /* ---------------- C6 ---------------- */
  const kMin = c6.k_min_N_m_rad, kSup = c6.k_supplied_N_m_rad;
  root.append(panel("C6 · Spring margin against its own requirement", { id: "cmp-c6" },
    h("div", { class: "cluster", style: { marginBottom: "10px" } }, h("a", { href: claimLink("C6") }, "Claim C6"), statusChip(claim.C6.status, claim.C6.status_label)),
    marginGauge({ kMin, kSupplied: kSup, requiredFraction: req["R-C6-MARGIN"].bound.min }),
    h("p", { class: "mx-note" }, "Arc: copper — below k_min; amber — above k_min but under the required margin; teal — margin ≥ ", `${(req["R-C6-MARGIN"].bound.min * 100).toFixed(0)} %`, " (R-C6-MARGIN). Needle: k_supplied."),
    h("dl", { class: "kv" },
      h("dt", {}, "k_min"), h("dd", { class: "mono" }, `${kMin} N·m/rad — C6_design_point.json k_min_N_m_rad (analytical)`),
      h("dt", {}, "k_supplied"), h("dd", { class: "mono" }, `${kSup} N·m/rad — ${c6.k_supplied_basis}`),
      h("dt", {}, "margin"), h("dd", { class: "mono" }, `${(c6.margin_fraction * 100).toFixed(2)} % = ${c6.units.margin_fraction}`),
      h("dt", {}, "required"), h("dd", { class: "mono" }, `≥ ${(req["R-C6-MARGIN"].bound.min * 100).toFixed(0)} % → k ≥ ${(kMin * (1 + req["R-C6-MARGIN"].bound.min)).toFixed(2)} N·m/rad (arithmetic)`),
      h("dt", {}, "measured rate"), h("dd", {}, notMeasured(), " — R-C6-SPRING-RATE")),
    reqLine(req["R-C6-MARGIN"]), reqLine(req["R-C6-KMIN"]), reqLine(req["R-C6-SPRING-RATE"]),
    h("h4", { style: { marginTop: "14px" } }, "Model assumptions (design-point record)"),
    h("ul", {}, c6.model_assumptions.map((x) => h("li", {}, x))),
    h("p", { class: "mx-note mb0" }, `The shortfall is ${((req["R-C6-MARGIN"].bound.min - c6.margin_fraction) * 100).toFixed(2)} percentage points — small, but the record keeps the failed requirement rather than rounding it away (D-011). Both k values are model numbers; no spring has been measured.`)));

  /* ---------------- D-010 ---------------- */
  const sideOf = (artifact) => disc["D-010"].sides.find((sd) => sd.artifact === artifact)?.says || "";
  const parts = rocketParts(or);
  const aftFin = parts.filter((p) => p.kind === "trapezoidfinset").reduce((m, p) => (p.span > (m?.span ?? 0) ? p : m), null);
  const D010 = [
    { q: "Fin mass", unit: "g", domain: [1, 1000], rows: [
      { model: "Mass model (mass_inputs)", artifact: "mass_inputs", value: 5.3, quote: "about 5.3 g in CFRP", color: "#67d8cf" },
      { model: "Reliability model", artifact: "reliability_run_record", value: 15, quote: "15 g fin", color: "#e3c27a" },
      { model: "Spring model (design point)", artifact: "spring_design_point", value: 154, quote: "154 g fin", color: "#e07650" }] },
    { q: "Fin chord", unit: "mm", domain: [10, 1000], rows: [
      { model: "Reliability model", artifact: "reliability_run_record", value: 60, quote: "60 mm", color: "#e3c27a" },
      { model: "Spring model (design point)", artifact: "spring_design_point", value: 120, quote: "120 mm chord", color: "#e07650" },
      { model: "OpenRocket aft fin root chord", source: aftFin.fields.rootchord.path, value: +aftFin.rootChord.toFixed(1), color: "#f1e9d6" }] },
    { q: "Fin egress velocity", unit: "m/s", domain: [10, 1000], rows: [
      { model: "Reliability model", artifact: "reliability_run_record", value: 70, quote: "70 m/s egress", color: "#e3c27a" },
      { model: "Spring model (design point)", artifact: "spring_design_point", value: 205, quote: "205 m/s egress", color: "#e07650" }] },
  ];
  const verify = h("table", { class: "data" }, h("thead", {}, h("tr", {}, h("th", {}, "Value"), h("th", {}, "Source"), h("th", {}, "Check"))),
    h("tbody", {}, D010.flatMap((gq) => gq.rows.map((r) => {
      const ok = r.artifact ? sideOf(r.artifact).includes(r.quote) : true;
      return h("tr", {}, h("td", { class: "mono" }, `${r.value} ${gq.unit}`),
        h("td", { class: "src" }, r.artifact ? `D-010 side · ${r.artifact}: “${r.quote}”` : `${or.current.source.path} · ${r.source}`),
        h("td", {}, h("span", { class: `mx-transcribed${ok ? "" : " no"}` }, r.artifact ? (ok ? "✓ matches record text" : "✗ transcription mismatch") : "read from data")));
    }))));
  root.append(panel("D-010 · The models do not describe the same fin", { id: "cmp-d010" },
    h("p", { class: "mx-note" }, "The mass, spring, and reliability models each assume a different fin. Values are transcribed from the D-010 discrepancy text (each checked against the record at load time); the OpenRocket chord is read from the design file."),
    h("div", { class: "mx-scroll" }, logBars(D010)),
    h("details", {}, h("summary", { class: "label", style: { cursor: "pointer" } }, "Transcription check"), verify),
    discBlock(disc["D-010"])));

  /* ---------------- D-009 ---------------- */
  const priorParts = rocketParts(or, { variant: "pre_retune" });
  const priorAft = priorParts.filter((p) => p.kind === "trapezoidfinset").reduce((m, p) => (p.span > (m?.span ?? 0) ? p : m), null);
  const fin = (p, label) => ({ x0: p.x0, sweep: p.sweep, span: p.span, tip: p.tipChord, root: p.rootChord, label });
  const area = (p) => ((p.rootChord + p.tipChord) / 2) * p.span;
  root.append(panel("D-009 · Inputs revised until the targets were met", { wide: true, id: "cmp-d009" },
    h("div", { class: "mx-two" },
      h("div", {}, planformOverlay(fin(aftFin, `current: root ${aftFin.rootChord.toFixed(0)} · span ${aftFin.span.toFixed(0)} mm`),
        fin(priorAft, `pre-retune: root ${priorAft.rootChord.toFixed(0)} · span ${priorAft.span.toFixed(1)} mm`))),
      h("div", {},
        h("table", { class: "data" },
          h("thead", {}, h("tr", {}, h("th", {}, "Aft fin"), h("th", { class: "num" }, "Current"), h("th", { class: "num" }, "Pre-retune"))),
          h("tbody", {},
            ...[["Root chord", "rootChord"], ["Tip chord", "tipChord"], ["Sweep length", "sweep"], ["Span", "span"], ["Thickness", "thickness"], ["LE station", "x0"]].map(([label, k]) =>
              h("tr", {}, h("td", {}, label), h("td", { class: "num mono" }, `${aftFin[k].toFixed(1)} mm`), h("td", { class: "num mono" }, `${priorAft[k].toFixed(1)} mm`))),
            h("tr", {}, h("td", {}, "Planform area (trapezoid arithmetic)"), h("td", { class: "num mono" }, `${(area(aftFin) / 100).toFixed(0)} cm²`), h("td", { class: "num mono" }, `${(area(priorAft) / 100).toFixed(1)} cm²`)))),
        h("p", { class: "src" }, `current: ${or.current.source.path} · pre-retune: ${or.pre_retune.source.path}`),
        h("p", { class: "mx-note" }, "Matching a target is not validation. The current fins may be right, but the record holds no independent source (drawing, datasheet, measurement) for the revised values, so C5, C6, and C8 stay open."),
        discBlock(disc["D-009"])))));

  if (disc["D-023"]) root.append(h("p", { class: "muted wide", style: { gridColumn: "1 / -1", fontSize: "12.5px" } }, "Related: ", h("a", { href: discrepancyLink("D-023") }, `D-023 · ${disc["D-023"].title}`), ". Every chart on this page is generated from committed values at load time, not from screenshots."));
}
