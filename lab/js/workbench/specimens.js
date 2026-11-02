// Specimens for the workbench. Each is built only from committed sources:
//  - rocket:  OpenRocket design file parameters (lab/data/openrocket.json)      SOURCE MODEL
//  - fourbar: STEP export tessellated with OpenCascade (lab/data/cad/four_bar.json) SOURCE CAD
//  - naca:    tested NACA 0012 generator output (lab/data/naca0012.json)          SOURCE MODEL
//  - archives: Fusion 360 archives, inventoried but not translated                NOT TRANSLATED
import { THREE } from "../core/three-kit.js";
import { partVisuals, clayMaterial } from "../core/materials.js";
import { rocketParts, rocketDimensions, rocketUnspecified, buildPartGeometry, latheFeatureLines } from "../core/rocket-geometry.js";
import { dimension, unspecifiedCallout, stationRing, stationBand } from "./dims.js";

const CLAY = { nosecone: 0xd9b08c, bodytube: 0x2f7f80, trapezoidfinset: 0xc8794a, motor: 0x8a8f96 };
const SOLID = { nosecone: 0xe4ddcf, bodytube: 0x8ea3ae, trapezoidfinset: 0xc4cfd5, motor: 0x5d636b };

function mergeInto(group, visuals) { group.add(visuals); return visuals; }

function pickablesOf(group) {
  const out = [];
  group.traverse((o) => { if (o.isMesh && o.userData.role === "solid") out.push(o); });
  return out;
}

const fmt = (v, d = 2) => (v === null || v === undefined ? null : `${Number(v).toFixed(d)} mm`);

// ---------------------------------------------------------------------------
// Rocket (OpenRocket parametric model)
// ---------------------------------------------------------------------------
export function buildRocket(or, extra) {
  const parts = rocketParts(or);
  const model = or.current;
  const L = model.overall_length_m * 1000;
  const root = new THREE.Group();
  root.name = "rocket";
  root.position.x = -L / 2;
  const out = [];
  const tree = [{ id: "asm", label: model.rocket_name, depth: 0, type: "group" }, { id: "stage", label: "Sustainer (stage)", depth: 1, type: "group" }];
  for (const p of parts) {
    const group = new THREE.Group();
    group.name = p.id;
    const pieces = buildPartGeometry(THREE, p);
    const clay = clayMaterial({ color: CLAY[p.kind] ?? 0xc9a27e, scale: 0.05, bump: 0.8 });
    const lathe = p.kind === "nosecone" || p.kind === "bodytube" || p.kind === "motor";
    pieces.forEach(({ geometry, instance }) => {
      const edgePositions = lathe ? new Float32Array(latheFeatureLines(p)) : null;
      const v = partVisuals(geometry, { color: SOLID[p.kind] ?? 0x9fb3bf, clay, edgePositions, edgeThreshold: p.kind === "trapezoidfinset" ? 30 : 20 });
      if (instance) v.userData.instance = instance;
      mergeInto(group, v);
    });
    if (p.kind === "motor") group.userData.internal = true;
    root.add(group);
    const depth = p.kind === "trapezoidfinset" || p.kind === "motor" ? 3 : 2;
    out.push({ id: p.id, name: p.name, kind: p.kind, group, pickables: pickablesOf(group), meta: rocketMeta(p, model, extra) });
    tree.push({ id: p.id, label: p.name, sub: p.kind === "trapezoidfinset" ? `×${p.instances.length}` : (p.kind === "motor" ? "sim. input" : ""), depth, type: "part" });
  }
  // Dimensions in the XY plane (fins at 0°/180° lie in it).
  const dims = rocketDimensions(or, parts).map((d) => {
    const isY = d.axis === "y";
    const from = new THREE.Vector3(d.from[0], d.from[1], 0), to = new THREE.Vector3(d.to[0], d.to[1], 0);
    const offsetDir = isY ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0);
    const baseOffset = isY ? 0 : (d.finPlane ? d.offset : (d.offset < 0 ? d.offset - 0 : d.offset + 38.1));
    const g = dimension({ id: d.id, from, to, offsetDir, offset: isY ? 0 : baseOffset, text: `${d.label} ${d.value.toFixed(d.value >= 100 ? 1 : 2)} mm`, source: d.source, part: d.part });
    g.userData.tier = ["overall", "nose-l", "tube1-l", "tube2-l", "dia"].includes(d.id) ? "overview" : "part";
    return g;
  });
  const unspecified = rocketUnspecified(parts).map((u) => unspecifiedCallout({ id: u.id, at: new THREE.Vector3(u.at[0], u.at[1], 0), text: u.text, label: u.label, part: u.part,
    lift: { hinge: new THREE.Vector3(-30, 205, 0), joints: new THREE.Vector3(0, 110, 0), electronics: new THREE.Vector3(0, 95, 0) }[u.id] || new THREE.Vector3(0, 100, 0) }));
  const dimGroup = new THREE.Group(); dims.forEach((d) => dimGroup.add(d)); root.add(dimGroup);
  const center = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-25, 0, 0), new THREE.Vector3(L + 25, 0, 0)]),
    new THREE.LineDashedMaterial({ color: 0xe0a274, dashSize: 14, gapSize: 4, transparent: true, opacity: 0.7, depthTest: false }));
  center.computeLineDistances();
  center.userData.kind = "centerline";
  center.renderOrder = 8;
  root.add(center);
  const unsGroup = new THREE.Group(); unspecified.forEach((u) => unsGroup.add(u)); unsGroup.visible = false; root.add(unsGroup);

  // Exploded view: illustrative separation paths. The file records positions, not an assembly procedure.
  const plan = [];
  for (const p of out) {
    const part = parts.find((q) => q.id === p.id);
    const cx = (part.x0 + part.x1) / 2;
    if (part.kind === "trapezoidfinset") {
      p.group.children.forEach((v, i) => {
        const a = (v.userData.instance.angleDeg * Math.PI) / 180;
        plan.push({ id: `${p.id}#${i}`, part: p.id, child: v, center: [cx, 0, 0], direction: [part.rootChord > 60 ? 0.35 : 0, Math.cos(a), Math.sin(a)], distance: part.span * 0.75 + 40, order: part.rootChord > 60 ? 1 : 0 });
      });
    } else if (part.kind === "nosecone") plan.push({ id: p.id, part: p.id, center: [cx, 0, 0], direction: [-1, 0, 0], distance: 150, order: 3 });
    else if (part.kind === "motor") plan.push({ id: p.id, part: p.id, center: [cx, 0, 0], direction: [1, 0, 0], distance: 330, order: 2 });
    else if (part.kind === "bodytube" && part.x0 > 1) plan.push({ id: p.id, part: p.id, center: [cx, 0, 0], direction: [1, 0, 0], distance: part.x0 > 300 ? 170 : 0, order: 4 });
    else plan.push({ id: p.id, part: p.id, center: [cx, 0, 0], direction: [1, 0, 0], distance: 0, order: 5 });
  }

  const overlays = [
    { id: "stability", label: "Stability stations · C5", title: "CG and both CP formulations at their recorded stations, with the R-C5-WINDOW band",
      build: () => stabilityOverlay(extra, parts) },
    { id: "pre-retune", label: "Pre-retune fins · D-009", title: "Aft fins as they were before inputs were revised toward paper targets (archived OpenRocket model)",
      build: () => preRetuneOverlay(or) },
    { id: "unspecified", label: "Not in source", title: "Callouts for what the OpenRocket file does not describe", target: unsGroup },
  ];
  return {
    id: "rocket", title: "Folding Stabilized Rocket", subtitle: "OpenRocket design file, current revision", assetClass: "source-model",
    source: { path: model.source.path, sha256: model.source.sha256, inner: model.source.inner_file },
    root, parts: out, tree, dims: dimGroup, unspecified: unsGroup, overlays, plan,
    explodeNote: "Separation paths are illustrative: the OpenRocket file records where components sit, not how they are assembled.",
    axis: [1, 0, 0], frameDir: new THREE.Vector3(0.3, 0.34, 1), lengthMM: L,
    info: `<b>${model.rocket_name}</b> · ${model.creator} · format ${model.format_version}<br>Overall ${L.toFixed(1)} mm · d<sub>ref</sub> ${(model.reference_diameter_m * 1000).toFixed(1)} mm · stations from nose tip along +X`,
    claims: ["C5"], discrepancies: ["D-006", "D-007", "D-008", "D-009", "D-023"], observations: or.lab_observations,
  };
}

function rocketMeta(p, model, extra) {
  const field = (k) => p.fields?.[k];
  const dims = [];
  const add = (q, k, factor = 1000, label) => { const f = field(k); if (f) dims.push({ q, v: fmt(f.value * factor, f.value * factor >= 100 ? 1 : 2) ?? f.value, src: f.path, raw: `${f.text ?? f.value} ${label ?? "m"}` }); };
  const meta = {
    title: p.name, componentId: p.oid || "—", sourceFile: p.sourceFile, sourcePath: p.path, assetClass: "source-model",
    dims, mass: null, material: null, assumptions: [], limitations: [], claims: ["C5"], discrepancies: [], observations: [], depths: {},
  };
  const station = { q: "Station (from nose tip)", v: `${p.x0.toFixed(1)} → ${p.x1.toFixed(1)} mm`, src: p.kind === "motor" ? `${p.path} (aft end at parent aft end + overhang ${p.overhang.toFixed(1)} mm)` : `${p.path} · axial method "${p.axialMethod}"` };
  if (p.kind === "nosecone") {
    add("Length", "length"); add("Base radius", "aftradius"); add("Wall thickness", "thickness");
    dims.push({ q: "Shape", v: field("shape")?.value, src: field("shape")?.path });
    meta.depths = {
      intro: "The nose meets the air first. Its shape sets how smoothly flow divides, and how far forward the aerodynamic forces act.",
      engineering: ["\\(r(x) = R\\sqrt{1 - \\left(\\tfrac{L - x}{L}\\right)^2}\\), an ellipsoid of length \\(L\\) and base radius \\(R\\).",
        "D-008 records that Simulation/static_margin.py uses the ogive nose CP coefficient (0.466) for this ellipsoid nose."],
    };
    meta.discrepancies = ["D-008"];
  } else if (p.kind === "bodytube") {
    add("Length", "length"); add("Outer radius", "radius"); add("Wall thickness", "thickness");
    meta.depths = {
      intro: "The tube is the airframe's backbone. Its diameter is also the ruler for stability: margins are counted in body diameters (calibers).",
      engineering: ["Static margin in calibers: \\(\\mathrm{SM} = \\dfrac{x_{CP} - x_{CG}}{d_{ref}}\\), with \\(d_{ref} = 2R = 76.2\\,\\text{mm}\\) here.",
        "Override mass and CG are simulation inputs typed into the file; they replace the computed values for this component and its subcomponents."],
    };
    meta.discrepancies = ["D-008", "D-010"];
  } else if (p.kind === "trapezoidfinset") {
    add("Root chord", "rootchord"); add("Tip chord", "tipchord"); add("Span (height)", "height"); add("LE sweep length", "sweeplength"); add("Thickness", "thickness");
    dims.push({ q: "Count", v: `${p.instances.length} at ${p.instances.map((i) => `${((i.angleDeg % 360) + 360) % 360}°`).join(", ")}`, src: field("fincount")?.path });
    dims.push({ q: "Cross-section", v: field("crosssection")?.value, src: field("crosssection")?.path });
    const big = p.span > 100;
    meta.depths = {
      intro: big ? "These large fins sit at the tail. Pushed by the airflow, they move the centre of pressure aft, which is what keeps a rocket pointing into the wind."
        : "A small fin set further forward. The firmware drives four canard servos, but this file does not say whether these fins model them.",
      engineering: big ? ["Barrowman fin CP term (textbook): \\(X_F = X_f + \\dfrac{X_R}{3}\\dfrac{C_R + 2C_T}{C_R + C_T} + \\dfrac{1}{6}\\left[(C_R + C_T) - \\dfrac{C_R C_T}{C_R + C_T}\\right]\\).",
        "D-006 records two differences: the reference script uses \\(C_R\\) where the textbook uses \\(X_R\\), and its normal-force term uses the sweep length where the textbook uses the mid-chord line length. Neither formulation has been independently reviewed, so neither is declared correct.",
        "The script records \\(X_f = 0.381\\,\\text{m}\\); OpenRocket's \"bottom\" placement puts the leading edge at \\(0.471\\,\\text{m}\\) (LAB-OBS-1, unreviewed)."]
        : ["Placed with method \"absolute\": 0.18 m from the nose tip regardless of the tube it belongs to.", "Rendered cross-section: flat plate with rounded edges (OpenRocket uses the cross-section setting for drag)."],
    };
    meta.limitations.push("Fixed fins in this file: no hinge, fold angle, or deployment geometry exists in the OpenRocket model.");
    if (big) { meta.discrepancies = ["D-006", "D-009", "D-010"]; meta.observations = ["LAB-OBS-1"]; }
  } else if (p.kind === "motor") {
    dims.push({ q: "Diameter", v: fmt(p.radius * 2), src: `${p.path}/diameter` });
    dims.push({ q: "Length", v: fmt(p.length, 1), src: `${p.path}/length` });
    dims.push({ q: "Designation", v: `${p.manufacturer ?? ""} ${p.designation ?? ""}`.trim(), src: `${p.path}/designation` });
    meta.assetClass = "source-model";
    meta.depths = {
      intro: "Only an envelope: the space the simulation file reserves for a motor. Nothing about propulsion is modelled or validated here.",
      engineering: ["D-007: the static-margin script burns a hard-coded Estes C6-5 while this file specifies the motor shown. The script's CG history, which both CP formulations use, therefore does not describe this file's configuration."],
    };
    meta.limitations.push("Live propulsion is outside this repository's validation boundary.");
    meta.discrepancies = ["D-007"];
  }
  dims.unshift(station);
  if (p.overrideMass !== null && p.overrideMass !== undefined) {
    meta.mass = { text: `${(p.overrideMass * 1000).toFixed(0)} g — simulation override input${p.overrideMassSub === "true" ? " (includes subcomponents)" : ""}`, src: p.fields.overridemass?.path };
  }
  if (p.material) meta.material = { text: `${p.material} — simulation material assignment, not as-built`, src: p.fields.material?.path };
  meta.assumptions.push("Geometry follows the file's parameters; OpenRocket's axial-method rules place each component.");
  meta.limitations.push("A design-file shape is not evidence of a physical part; no as-built dimension is recorded.");
  meta.research = [{ k: "Design file", v: model.source.path }, { k: "SHA-256", v: model.source.sha256 }, { k: "Inner XML", v: `${model.source.inner_file} · ${model.source.inner_sha256.slice(0, 12)}` }, { k: "Element", v: p.path }];
  return meta;
}

function stabilityOverlay(extra, parts) {
  const group = new THREE.Group();
  const R = parts.find((p) => p.kind === "bodytube")?.radius ?? 38.1;
  const { csv, inputs, cross } = extra.c5;
  const cg = csv.map((r) => Number(r.cg_m) * 1000);
  const cgMin = Math.min(...cg), cgMax = Math.max(...cg);
  const dref = inputs.geometry.d_ref * 1000;
  const cpRef = inputs.cp_m * 1000, cpTxt = cross.cp_m * 1000;
  group.add(stationBand({ x0: cgMax + 1.5 * dref, x1: cgMin + 2.0 * dref, radius: R + 7, color: 0x4cc9bb,
    text: `R-C5-WINDOW · CP meeting 1.5–2.0 cal at every recorded CG: ${(cgMax + 1.5 * dref).toFixed(1)}–${(cgMin + 2.0 * dref).toFixed(1)} mm`, sub: `x_CG,max + 1.5·d_ref to x_CG,min + 2.0·d_ref, d_ref ${dref.toFixed(1)} mm · derived for display` }));
  group.add(stationRing({ x: (cgMin + cgMax) / 2, radius: R + 4, color: 0xf1e9d6, text: `CG ${cgMin.toFixed(0)}–${cgMax.toFixed(0)} mm`, sub: "docs/EVIDENCE/C5_static_margin.csv · cg_m" }));
  group.add(stationRing({ x: cpRef, radius: R + 4, color: 0x67d8cf, text: `CP reference ${cpRef.toFixed(1)} mm`, sub: "C5_static_margin_inputs.json · cp_m · SM 1.55–1.57 cal" }));
  group.add(stationRing({ x: cpTxt, radius: R + 4, color: 0xe07650, text: `CP textbook ${cpTxt.toFixed(1)} mm`, sub: "C5_barrowman_crosscheck.json · cp_m · SM 0.74–0.76 cal" }));
  const obs = extra.observation;
  if (obs) {
    group.add(stationRing({ x: obs.values_m.static_margin_inputs_X_f * 1000, radius: R + 22, color: 0xe3c27a, dashed: true, text: `Fin LE in script ${(obs.values_m.static_margin_inputs_X_f * 1000).toFixed(0)} mm`, sub: "LAB-OBS-1 · unreviewed candidate" }));
    group.add(stationRing({ x: obs.values_m.ork_semantics * 1000, radius: R + 22, color: 0xe3c27a, dashed: true, text: `Fin LE by .ork rules ${(obs.values_m.ork_semantics * 1000).toFixed(0)} mm`, sub: "position type=\"bottom\" · LAB-OBS-1" }));
  }
  group.userData.legend = "Two formulations, one rocket: neither CP is declared correct (D-006). The window band is arithmetic on the requirement and the recorded CG.";
  return group;
}

function preRetuneOverlay(or) {
  const group = new THREE.Group();
  const prior = rocketParts(or, { variant: "pre_retune" });
  const aft = prior.filter((p) => p.kind === "trapezoidfinset").reduce((m, p) => (p.span > (m?.span ?? 0) ? p : m), null);
  if (!aft) return group;
  const mat = new THREE.MeshBasicMaterial({ color: 0xe3c27a, transparent: true, opacity: 0.22, depthWrite: false, side: THREE.DoubleSide });
  const line = new THREE.LineBasicMaterial({ color: 0xe3c27a });
  for (const { geometry } of buildPartGeometry(THREE, aft)) {
    group.add(new THREE.Mesh(geometry, mat));
    group.add(new THREE.LineSegments(new THREE.EdgesGeometry(geometry, 30), line));
  }
  const tag = document.createElement("div");
  tag.className = "css2d-label warn";
  tag.innerHTML = `Pre-retune aft fins: root ${aft.rootChord.toFixed(1)} mm · span ${aft.span.toFixed(1)} mm<small>evidence/archive/C5_openrocket_pre_retune.ork.xml · D-009</small>`;
  const obj = new THREE.CSS2DObject(tag);
  obj.position.set(aft.x0, aft.rootRadius + aft.span + 18, 0);
  group.add(obj);
  return group;
}

// ---------------------------------------------------------------------------
// Four-bar STEP (source CAD)
// ---------------------------------------------------------------------------
const FB_CLAY = { ground: 0x9a8f80, input: 0xc8603f, coupler: 0x2f7f80, output: 0x7f9a52 };

export function buildFourBar(step, evidence) {
  const root = new THREE.Group();
  root.name = "four-bar";
  const parts = [];
  const tree = [{ id: "asm", label: "Four Bar Linkage.step", depth: 0, type: "group" }];
  const all = new THREE.Box3();
  for (const p of step.parts) {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(p.positions, 3));
    geometry.setIndex(p.indices);
    geometry.computeVertexNormals();
    const segs = [];
    for (const e of p.edges) {
      for (let i = 0; i + 5 < e.points.length; i += 3) segs.push(e.points[i], e.points[i + 1], e.points[i + 2], e.points[i + 3], e.points[i + 4], e.points[i + 5]);
    }
    const color = new THREE.Color(...(p.color || [0.7, 0.7, 0.7]));
    const v = partVisuals(geometry, { color, edgePositions: new Float32Array(segs), clay: clayMaterial({ color: FB_CLAY[p.role] ?? 0xc9a27e, scale: 0.35, bump: 0.6 }) });
    const group = new THREE.Group();
    group.name = p.role || p.name;
    group.add(v);
    root.add(group);
    geometry.computeBoundingBox();
    all.union(geometry.boundingBox);
    const id = p.role || `part-${p.name}`;
    parts.push({ id, name: `${(p.role || "link").replace(/^./, (c) => c.toUpperCase())} link`, kind: "link", group, pickables: pickablesOf(group), step: p, meta: fourBarMeta(p, step) });
    tree.push({ id, label: `${(p.role || "link").replace(/^./, (c) => c.toUpperCase())} link`, sub: `STEP #${p.name}`, depth: 1, type: "part" });
  }
  const center = all.getCenter(new THREE.Vector3());
  root.position.set(-center.x, -center.y, -center.z);
  // Pin-spacing dimensions taken from each link's cylindrical faces in the STEP B-rep.
  const dimGroup = new THREE.Group();
  for (const part of parts) {
    const holes = part.step.cylindrical_features;
    if (holes.length !== 2) continue;
    const [h1, h2] = holes.map((h) => new THREE.Vector3(...h.axis_point));
    const g = dimension({ id: `${part.id}-pins`, from: h1, to: h2, offsetDir: new THREE.Vector3(0, part.id === "coupler" ? 1 : -1, 0), offset: part.id === "coupler" ? 7 : (part.id === "ground" ? -12 : -6), text: `${part.step.pin_spacing_mm_brep.toFixed(3)} mm pin spacing`, source: `from STEP B-rep cylindrical faces · ${part.id}`, part: part.id, scale: 0.35 });
    dimGroup.add(g);
  }
  root.add(dimGroup);
  const plan = parts.map((p) => {
    const z = (p.step.bbox_mm[2] + p.step.bbox_mm[5]) / 2;
    const layer = Math.round(z / 2);
    return { id: p.id, part: p.id, center: [0, 0, z], direction: [0, 0, 1], distance: layer * 9, order: 3 - layer };
  });
  const joints = jointCheck(step.parts);
  const overlays = [
    { id: "pins", label: "Pin axes & joint check", title: "Every cylindrical feature's axis, and whether any two links share one", build: () => pinOverlay(step.parts, joints) },
  ];
  return {
    id: "fourbar", title: "Four Bar Linkage.step", subtitle: "STEP AP214 export · tessellated with OpenCascade", assetClass: "source-cad",
    source: { path: step.source, sha256: step.source_sha256 }, root, parts, tree, dims: dimGroup, overlays, plan,
    explodeNote: "Layers lift along +Z in STEP stacking order. The file places four separate bars; it records no joints or assembly sequence (D-005).",
    axis: [1, 0, 0], frameDir: new THREE.Vector3(0.25, 0.55, 1), lengthMM: 70, joints,
    info: `<b>${step.source}</b> · ${step.parts.length} solids · tessellation ${step.tessellation.linear_deflection_mm} mm / ${step.tessellation.angular_deflection_rad} rad<br>Joint check from geometry: <b>${joints.concentric.length} of ${joints.pairsConsidered} hole pairs concentric across links</b>`,
    claims: ["C1"], discrepancies: ["D-002", "D-005"], observations: [],
  };
}

function fourBarMeta(p, step) {
  const holes = p.cylindrical_features;
  const role = p.role || "unknown";
  const recorded = { ground: 25, coupler: 60, input: 15, output: 15 }[role];
  return {
    title: `${role.replace(/^./, (c) => c.toUpperCase())} link`, componentId: `STEP product #${p.name}`, sourceFile: step.source, sourcePath: p.chain.join(" › "), assetClass: "source-cad",
    dims: [
      { q: "Pin spacing (STEP B-rep)", v: `${p.pin_spacing_mm_brep?.toFixed(3) ?? "—"} mm`, src: "distance between cylindrical-face axes in the STEP B-rep" },
      { q: "Recorded model length", v: recorded ? `${recorded} mm` : "NOT SPECIFIED", src: "mechanism/four_bar.py BASELINE" },
      { q: "Hole radius (STEP B-rep)", v: holes.map((h) => `${h.radius_mm.toFixed(3)} mm`).join(", "), src: "cylindrical faces" },
      { q: "Bounding box", v: `${(p.bbox_mm[3] - p.bbox_mm[0]).toFixed(2)} × ${(p.bbox_mm[4] - p.bbox_mm[1]).toFixed(2)} × ${(p.bbox_mm[5] - p.bbox_mm[2]).toFixed(2)} mm`, src: "OCC bounding box (includes tessellation tolerance)" },
      { q: "Volume", v: `${p.volume_mm3.toFixed(1)} mm³`, src: "OCC volume properties of the solid" },
    ],
    mass: { text: "NOT MEASURED — no material or density is recorded for the STEP links", src: null },
    material: null,
    assumptions: [p.role_basis, "Link width 5 mm, thickness 2 mm and hole Ø2 mm come from export_step() in Project33FourBar.py."],
    limitations: ["The STEP places four separate bars; it is not a constrained or closed mechanism (D-005).", "Display tessellation is not the B-rep; measurements here use the B-rep values exported by the converter."],
    claims: ["C1"], discrepancies: ["D-005", "D-002"], observations: [],
    depths: {
      intro: role === "coupler" ? "The coupler is the long link that should join the input link to the output link. At 60 mm it is too long for the 15 mm links to reach — the loop cannot close." : "Each bar is a link. Pins through the holes would make joints; the distance between hole centres is what kinematics cares about.",
      engineering: ["Pin-centre distance is the link length in the planar model. Grashof check for the recorded set: \\(s + l = 15 + 60 = 75 > p + q = 15 + 25 = 40\\), so non-Grashof.",
        "D-005: the Fusion sketch script draws this coupler from (0, 15) to (25, 15) — 25 mm — while the STEP and the model use 60 mm."],
    },
    research: [{ k: "STEP", v: step.source }, { k: "SHA-256", v: step.source_sha256 }, { k: "Product", v: `#${p.name} · colour ${JSON.stringify(p.color)}` }, { k: "Triangles", v: String(p.triangles) }, { k: "Converter", v: "tools/cad_to_web.py (OCP)" }],
  };
}

/** Find hole axes shared between different links (a pin joint would need one). */
export function jointCheck(stepParts, tol = 0.01) {
  const holes = [];
  stepParts.forEach((p) => p.cylindrical_features.forEach((h) => holes.push({ part: p.role || p.name, x: h.axis_point[0], y: h.axis_point[1] })));
  const concentric = [];
  let pairs = 0;
  for (let i = 0; i < holes.length; i++) {
    for (let j = i + 1; j < holes.length; j++) {
      if (holes[i].part === holes[j].part) continue;
      pairs++;
      if (Math.hypot(holes[i].x - holes[j].x, holes[i].y - holes[j].y) < tol) concentric.push([holes[i], holes[j]]);
    }
  }
  return { holes, concentric, pairsConsidered: pairs };
}

function pinOverlay(stepParts, joints) {
  const group = new THREE.Group();
  const colors = { ground: 0xd0d6da, input: 0xff7a5c, coupler: 0x6aa8ff, output: 0x7fe08a };
  for (const h of joints.holes) {
    const g = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(h.x, h.y, -6), new THREE.Vector3(h.x, h.y, 34)]);
    const line = new THREE.Line(g, new THREE.LineDashedMaterial({ color: colors[h.part] ?? 0xffffff, dashSize: 1.2, gapSize: 0.8, depthTest: false }));
    line.computeLineDistances();
    line.renderOrder = 12;
    group.add(line);
    const el = document.createElement("div");
    el.className = "css2d-label";
    el.style.fontSize = "9.5px";
    el.textContent = `${h.part} (${h.x.toFixed(1)}, ${h.y.toFixed(1)})`;
    const o = new THREE.CSS2DObject(el);
    o.position.set(h.x, h.y, 36);
    group.add(o);
  }
  const el = document.createElement("div");
  el.className = "css2d-label warn";
  el.innerHTML = `${joints.concentric.length} of ${joints.pairsConsidered} cross-link hole pairs concentric<small>no two links share a pin axis in this STEP (consistent with D-005)</small>`;
  const o = new THREE.CSS2DObject(el);
  o.position.set(0, -14, 20);
  group.add(o);
  return group;
}

// ---------------------------------------------------------------------------
// NACA 0012 profile (tested generator output, C3)
// ---------------------------------------------------------------------------
export function buildNaca(naca) {
  const root = new THREE.Group();
  root.name = "naca";
  const pts = [...naca.upper.map(([x, y]) => new THREE.Vector2(x, y)), ...naca.lower.slice(1, -1).reverse().map(([x, y]) => new THREE.Vector2(x, y))];
  const shape = new THREE.Shape(pts);
  const depth = 10;
  const geometry = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: false });
  geometry.translate(0, 0, -depth / 2);
  const v = partVisuals(geometry, { color: 0xb7c7cf, clay: clayMaterial({ color: 0xc8794a, scale: 0.4, bump: 0.6 }), edgeThreshold: 25 });
  const extrusion = new THREE.Group(); extrusion.add(v); extrusion.visible = false;
  const profileLine = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts.map((p) => new THREE.Vector3(p.x, p.y, 0))), new THREE.LineBasicMaterial({ color: 0xf1e9d6 }));
  const profile = new THREE.Group(); profile.add(profileLine);
  const ptsGeom = new THREE.BufferGeometry().setFromPoints(pts.map((p) => new THREE.Vector3(p.x, p.y, 0)));
  profile.add(new THREE.Points(ptsGeom, new THREE.PointsMaterial({ color: 0x67d8cf, size: 3, sizeAttenuation: false })));
  const pickPlane = new THREE.Mesh(new THREE.ShapeGeometry(shape), new THREE.MeshBasicMaterial({ color: 0x67d8cf, transparent: true, opacity: 0.08, side: THREE.DoubleSide, depthWrite: false }));
  pickPlane.userData.role = "solid";
  profile.add(pickPlane);
  root.add(profile, extrusion);
  root.position.set(-naca.chord_mm / 2, 0, 0);
  const dimGroup = new THREE.Group();
  dimGroup.add(dimension({ id: "chord", from: new THREE.Vector3(0, 0, 0), to: new THREE.Vector3(naca.chord_mm, 0, 0), offsetDir: new THREE.Vector3(0, -1, 0), offset: 9, text: `Chord ${naca.chord_mm.toFixed(2)} mm`, source: naca.function, scale: 0.4 }));
  let best = 0, bx = 0;
  naca.upper.forEach(([x, y], i) => { const t = y - naca.lower[i][1]; if (t > best) { best = t; bx = x; } });
  dimGroup.add(dimension({ id: "thickness", from: new THREE.Vector3(bx, naca.lower.find(([x]) => x === bx)?.[1] ?? -best / 2, 0), to: new THREE.Vector3(bx, best / 2, 0), offsetDir: new THREE.Vector3(1, 0, 0), offset: 0, text: `Max thickness ${naca.max_thickness_mm_sampled.toFixed(3)} mm (sampled)`, source: `x ≈ ${bx.toFixed(2)} mm of 51 cosine-spaced stations`, scale: 0.4 }));
  root.add(dimGroup);
  const parts = [{ id: "profile", name: "NACA 0012 profile", kind: "profile", group: profile, pickables: [pickPlane], meta: nacaMeta(naca) }];
  return {
    id: "naca", title: "NACA 0012 fin profile", subtitle: "Output of the tested generator (C3)", assetClass: "source-model",
    source: { path: naca.generator, sha256: naca.inputs[naca.generator] }, root, parts, dims: dimGroup, plan: [],
    tree: [{ id: "asm", label: "naca_fin_generator.py", depth: 0, type: "group" }, { id: "profile", label: "NACA 0012 profile", sub: "51 + 51 pts", depth: 1, type: "part" }],
    overlays: [{ id: "extrude", label: "Illustrative extrusion", title: "A 10 mm display depth. The span is NOT SPECIFIED by the generator.", build: null, target: extrusion, illustrative: true }],
    explodeNote: "A single profile has nothing to explode.", axis: [1, 0, 0], frameDir: new THREE.Vector3(0, 0, 1), lengthMM: 60, flat: true,
    info: `<b>${naca.designation}</b> · chord ${naca.chord_mm} mm · ${naca.upper.length} upper + ${naca.lower.length} lower stations (cosine spacing)<br>Span: <b>NOT SPECIFIED</b>`,
    claims: ["C3"], discrepancies: [], observations: [],
  };
}

function nacaMeta(naca) {
  return {
    title: "NACA 0012 profile", componentId: naca.designation, sourceFile: naca.generator, sourcePath: naca.function, assetClass: "source-model",
    dims: [{ q: "Chord", v: `${naca.chord_mm.toFixed(2)} mm`, src: naca.function }, { q: "Max thickness (sampled)", v: `${naca.max_thickness_mm_sampled.toFixed(3)} mm`, src: "max over stations of upper − lower" }, { q: "Span", v: "NOT SPECIFIED", src: naca.span }],
    mass: { text: "NOT SPECIFIED — a profile has no mass", src: null }, material: null,
    assumptions: ["Symmetric 4-digit series: m = 0, p = 0, t = 0.12."], limitations: [naca.limitation, "Where this profile is used is not recorded. Cross-reference: the reliability run also assumes a 60 mm chord, while the spring and OpenRocket models use other chords (see D-010, which does not cover C3)."],
    claims: ["C3"], discrepancies: [], observations: [],
    depths: {
      intro: "An airfoil is a carefully shaped cross-section. This one is symmetric and 12% as thick as it is long.",
      engineering: ["Half-thickness: \\(y_t = 5tc\\,[0.2969\\sqrt{\\xi} - 0.1260\\,\\xi - 0.3516\\,\\xi^2 + 0.2843\\,\\xi^3 - 0.1015\\,\\xi^4]\\), \\(\\xi = x/c\\), \\(t = 0.12\\), \\(c = 60\\,\\text{mm}\\).",
        "Cosine spacing \\(\\xi_i = \\tfrac{1}{2}(1 - \\cos\\tfrac{i\\pi}{n})\\) clusters points at the leading and trailing edges, so the sampled maximum (7.198 mm) sits just under 0.12c = 7.2 mm."],
    },
    research: [{ k: "Generator", v: naca.generator }, { k: "SHA-256", v: naca.inputs[naca.generator] }, { k: "Function", v: naca.function }],
  };
}
