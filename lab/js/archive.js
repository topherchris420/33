// Research Archive: capability matrix, live-recomputed candidate observations, provenance
// digests from the derived views, documents, and reproducibility commands.
import { mountShell } from "./core/shell.js";
import { h, $, clear, copyButton } from "./core/dom.js";
import { lab, repoLink, docLink } from "./core/data.js";
import { categoryBadge } from "./core/taxonomy.js";
import { transmissionAngle, couplerClosureBand } from "./core/math/fourbar.js";

mountShell();

const MATRIX = [
  ["3D rocket assembly", "ok", "Simulation/Folding Stabilized Rocket.ork", "Parametric geometry from the design file with OpenRocket axial semantics; every dimension carries its XML path."],
  ["Four-bar STEP inspection", "ok", "CAD Files/Four Bar Linkage.step", "Tessellated with OpenCascade (OCP); pin spacing taken from the B-rep's cylindrical faces; joint check from hole axes."],
  ["NACA 0012 profile", "ok", "CAD Files/naca_fin_generator.py", "Output of the tested generator. Span NOT SPECIFIED; extrusion shown only as an illustration."],
  ["Fusion 360 assemblies (.f3z)", "missing", "CAD Files/*.f3z", "Bodies are Autodesk ShapeManager B-rep with placements in proprietary streams. Inventoried (names, versions, B-rep statistics, embedded previews), not translated. Needs a STEP export from Fusion 360."],
  ["Exploded views", "partial", "Design-file positions", "Deterministic and reversible; separation paths are illustrative because no source records an assembly procedure."],
  ["Section planes, blueprint, x-ray, ortho views", "ok", "Displayed geometry", "Clipping with section hatching; feature edges and hidden lines in blueprint mode."],
  ["Mass, material, tolerance, manufacturing", "partial", "Design-file override inputs", "Shown only as simulation inputs where the file has them; otherwise NOT MEASURED / NOT SPECIFIED."],
  ["Folding-fin closure failure", "ok", "docs/EVIDENCE/C1_four_bar_sweep.json, mechanism/four_bar.py", "JS port verified row-for-row against the committed sweep, and against the Python model on closing configurations wherever Python is available (CI included)."],
  ["Model comparison (C5, C6, D-009, D-010)", "ok", "docs/EVIDENCE/*, evidence/discrepancies.json", "No winner declared; candidate observation LAB-OBS-1 flagged for review."],
  ["Evidence Observatory constellation & passports", "ok", "evidence/*.json via python -m evidence assessment", "Statuses and support levels are computed by evidence/assess.py, not re-derived."],
  ["Telemetry theater", "ok", "python -m evidence demo fixture + declared seeded generator", "Synthetic only; no physical telemetry exists in the record."],
  ["3D systems architecture", "ok", "docs/ARCHITECTURE.md, docs/WIRING.md, protocol/ground_status_model.json", "Diagram only; no transmit path."],
  ["Historical instrumentation exhibits", "ok", "General human-factors principles (original)", "Nothing reproduced from the distribution-restricted manual."],
  ["Opening cinematic", "ok", "Procedural Three.js + Web Audio", "80 s, deterministic timeline, captions, sound, browser-voice narration, skip/replay/chapters."],
  ["Recorded voice-over and Blender-authored film", "missing", "—", "Narration uses the browser's speech voice; a recorded voice and an offline-rendered film would need production assets."],
  ["Live hardware control, arming, ignition", "no", "—", "Excluded by design. The laboratory cannot send commands."],
  ["Physical measurements", "no", "evidence/measurements.json (empty)", "None exist; the laboratory never fabricates one."],
];

function obs(or) {
  const o1 = or.lab_observations[0];
  // LAB-OBS-2: recompute the transmission-angle feasibility search in the browser.
  const a = 25, b = 15;
  let closing = 0, feasible = 0, checked = 0;
  for (let c = 1; c <= 200; c += 1) for (let d = 1; d <= 200; d += 1) {
    checked++;
    let closes = true, ok = true;
    for (let t = 0; t <= 92; t += 1) {
      const mu = transmissionAngle(a, c, b, d, t);
      if (mu === null) { closes = false; ok = false; break; }
      if (mu < 40 || mu > 140) ok = false;
    }
    if (closes) closing++;
    if (ok) feasible++;
  }
  const band = couplerClosureBand(a, b, 15);
  return [
    h("div", { class: "panel ticked" }, h("div", { class: "panel-head" }, h("h4", {}, `${o1.id} · C5`), h("span", { class: "pill partial" }, "candidate")), h("div", { class: "panel-body" },
      h("p", {}, h("b", {}, o1.title)), h("p", {}, o1.detail),
      h("dl", { class: "kv" }, h("dt", {}, "By .ork rules"), h("dd", { class: "num" }, `${(o1.values_m.ork_semantics * 1000).toFixed(1)} mm`), h("dt", {}, "In C5 inputs"), h("dd", { class: "num" }, `${(o1.values_m.static_margin_inputs_X_f * 1000).toFixed(1)} mm`), h("dt", {}, "Difference"), h("dd", { class: "num" }, `${(o1.values_m.difference * 1000).toFixed(1)} mm`)),
      h("p", { class: "muted" }, o1.not_computed),
      h("p", {}, o1.sources.map((s) => h("a", { class: "src", href: repoLink(s), style: { display: "block" } }, s))))),
    h("div", { class: "panel ticked" }, h("div", { class: "panel-head" }, h("h4", {}, "LAB-OBS-2 · C1"), h("span", { class: "pill partial" }, "candidate")), h("div", { class: "panel-body" },
      h("p", {}, h("b", {}, "With the recorded ground (25 mm) and input (15 mm) links, no coupler/output pair satisfies both closure and R-C1-TRANSMISSION over 0–92°.")),
      h("p", {}, `Searched every integer coupler and output length from 1 to 200 mm (${checked.toLocaleString()} pairs, 1° steps, recomputed now in your browser): ${closing.toLocaleString()} close over the whole range; ${feasible} also keep the transmission angle within 40–140°.`),
      h("p", {}, `For the recorded output (15 mm), the coupler lengths that close are ${band.low.toFixed(1)}–${band.high.toFixed(1)} mm — and the 25 mm coupler drawn by the Fusion script (D-005) sits at a dead-centre pose at 0°.`),
      h("p", { class: "muted" }, "Convention (mechanism/four_bar.py): drive angle 0° means the input link lies along the ground line, toward D. Under that convention the result holds for every real length, not only integers: the 40–140° band needs c·d ≥ 253 mm², while closing at 0° needs c² + d² − 1.532·c·d ≤ 100 mm², and the two cannot both hold. Shift the 92° window to start elsewhere (for example at 30°) and closing pairs exist."),
      h("p", { class: "muted" }, "Implication for review: D-002 asks which dimensions were intended. This suggests the ground and input lengths, or the drive-angle origin and pivot layout, need review too — not only the coupler. Arithmetic on recorded values; not a design recommendation."),
      h("a", { class: "src", href: "mechanism.html" }, "Explore it in the Mechanism Lab sandbox"))),
  ];
}

async function provenance() {
  const names = ["evidence.json", "openrocket.json", "naca0012.json", "telemetry_fixture.json"];
  const views = await Promise.all(names.map((n) => fetch(new URL(`../data/${n}`, import.meta.url)).then((r) => r.json())));
  const cad = await lab.cadManifest();
  const rows = [];
  views.forEach((v, i) => {
    const inputs = Object.entries(v.inputs || {});
    rows.push(h("tr", {}, h("td", {}, h("a", { href: repoLink(`lab/data/${names[i]}`) }, `lab/data/${names[i]}`), h("div", { class: "muted", style: { fontSize: "11px" } }, v.generated_by)),
      h("td", {}, `${inputs.length} inputs`, h("details", {}, h("summary", { class: "label" }, "digests"), inputs.map(([p, d]) => h("div", { class: "src" }, `${p} · ${d.slice(0, 12)}`))))));
  });
  for (const o of cad.outputs) {
    rows.push(h("tr", {}, h("td", {}, h("a", { href: repoLink(o.path) }, o.path), h("div", { class: "hash" }, o.sha256.slice(0, 16)), o.note ? h("div", { class: "muted", style: { fontSize: "11px" } }, o.note) : null),
      h("td", {}, Object.entries(o.inputs).map(([p, d]) => h("div", { class: "src" }, `${p} · ${d.slice(0, 12)}`)))));
  }
  clear($("#prov"), h("thead", {}, h("tr", {}, h("th", {}, "Derived view"), h("th", {}, "Pinned inputs (SHA-256)"))), h("tbody", {}, rows));
}

const DOCS = [
  ["Evidence", [["Claim passports", "docs/claims/README.md"], ["Traceability matrix", "docs/TRACEABILITY.md"], ["Discrepancy register", "docs/DISCREPANCIES.md"], ["Evidence Observatory", "docs/EVIDENCE_OBSERVATORY.md"], ["Project status", "docs/PROJECT_STATUS.md"]]],
  ["Engineering", [["Architecture", "docs/ARCHITECTURE.md"], ["CAD assemblies", "docs/CAD_ASSEMBLIES.md"], ["Protocol", "docs/PROTOCOL.md"], ["Wiring", "docs/WIRING.md"], ["Degraded modes", "docs/DEGRADED_MODES.md"], ["Ground status", "docs/GROUND_STATUS.md"]]],
  ["Process & safety", [["Safety boundary", "docs/SAFETY.md"], ["Testing", "docs/TESTING.md"], ["Roadmap", "docs/ROADMAP.md"], ["Bench sessions", "docs/BENCH_SESSIONS.md"], ["Living laboratory (this site)", "docs/LIVING_LAB.md"], ["Contributing", "CONTRIBUTING.md"]]],
];

const CMDS = [
  ["python -m evidence status", "Claim table, requirement results, and scopes."],
  ["python -m evidence check", "Strict record check: drift, stale reviews, stale generated documents."],
  ["python tools/export_lab_data.py --check", "Every laboratory data view is current and every pinned input digest matches."],
  ["node --test tests/lab_math.test.mjs", "The JS four-bar port reproduces the committed C1 sweep and agrees with mechanism/four_bar.py."],
  ["python -m pytest tests/test_lab_data.py tests/test_lab_isolation.py -q", "Laboratory provenance and command-isolation checks."],
  ["python tools/serve_lab.py", "Serve the site locally, then open http://localhost:8000/lab/."],
  ["python tools/cad_to_web.py", "Regenerate CAD views (needs cadquery and zstandard); translates any STEP placed in CAD Files/exports/."],
];

async function boot() {
  clear($("#matrix"), h("thead", {}, h("tr", {}, h("th", {}, "Capability"), h("th", {}, "Status"), h("th", {}, "Built from"), h("th", {}, "Notes"))),
    h("tbody", {}, MATRIX.map(([name, st, src, note]) => h("tr", {}, h("td", {}, name), h("td", {}, h("span", { class: `pill ${st}` }, { ok: "Built", partial: "Partial", missing: "Missing", no: "Not done" }[st])), h("td", { class: "src" }, src), h("td", { class: "muted" }, note)))));
  clear($("#docs"), DOCS.map(([group, items]) => h("div", { class: "panel ticked" }, h("div", { class: "panel-head" }, h("h4", {}, group)), h("div", { class: "panel-body" }, h("ul", { class: "hub-list" }, items.map(([t, p]) => h("li", {}, h("a", { href: docLink(p) }, t))))))));
  clear($("#cmds"), CMDS.map(([c, d]) => h("div", { class: "cmd" }, h("code", {}, c), copyButton(c), h("span", {}, d))));
  const or = await lab.openrocket();
  clear($("#obs"), obs(or));
  await provenance();
}

boot().catch((err) => { console.error(err); });
