// The 3D Engineering Workbench. Every control here changes something real in the scene;
// nothing in this module can reach firmware, hardware, or a network command interface.
import { mountShell } from "../core/shell.js";
import { h, $, $$, clear, announce, syncRange, press, depthTabs, webglAvailable, downloadBlob, reducedMotion } from "../core/dom.js";
import { lab, canonical, repoLink, docLink, claimLink, discrepancyLink, parseCSV } from "../core/data.js";
import { categoryBadge, assetBadge, statusChip, ASSETS } from "../core/taxonomy.js";
import { THREE, createRenderer, CameraRig, VIEWS, studioLights, environment, blueprintGrid, AxisGizmo, autoResize, stampedScreenshot, label3D } from "../core/three-kit.js";
import { applyMode } from "../core/materials.js";
import { explodePlan } from "../core/math/explode.js";
import { tex } from "../core/tex.js";
import { elevationPaths } from "../core/rocket-geometry.js";
import { buildRocket, buildFourBar, buildNaca } from "./specimens.js";

mountShell();

const params = new URLSearchParams(location.search);
const viewport = $("#viewport");
const grid = $(".wb-grid");
const state = {
  specimen: null, mode: params.get("mode") || "solid", explode: 0, sequential: false,
  section: { on: false, axis: "x", t: 0.5, flip: false, showPlane: true },
  ortho: false, dims: true, labels: params.get("labels") === "1", measure: false, selected: null, hidden: new Set(), isolated: null,
  overlays: new Set(), anim: null,
};
let evidence, specimens = {}, current = null, plan = null, gizmo, rig, renderer, labels, scene, gridObj, shadowFloor, sectionPlane, planeHelper, measureObjs = [], measurePts = [];
let needsRender = true;
const invalidate = () => { needsRender = true; };

// ---------------------------------------------------------------------------
// Rich text with inline TeX \( … \)
// ---------------------------------------------------------------------------
function rich(text) {
  const p = h("p", {});
  text.split(/(\\\(.*?\\\))/g).forEach((chunk) => {
    if (chunk.startsWith("\\(")) { const s = h("span", {}); tex(s, chunk.slice(2, -2), { display: false }); p.append(s); }
    else if (chunk) p.append(chunk);
  });
  return p;
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
async function boot() {
  const [ev, or, step, naca, archives, csvText, inputs, cross] = await Promise.all([
    lab.evidence(), lab.openrocket(), lab.fourBarStep(), lab.naca(), lab.archives(),
    canonical.c5Csv(), canonical.c5Inputs(), canonical.c5Crosscheck(),
  ]);
  evidence = ev;
  const extra = { c5: { csv: parseCSV(csvText), inputs, cross }, observation: or.lab_observations[0] };
  const data = { or, step, naca, archives, extra };
  renderSpecimenList(data);
  if (!webglAvailable()) { fallback2D(or, step); return; }
  initScene();
  specimens = {
    rocket: () => buildRocket(or, extra),
    fourbar: () => buildFourBar(step, ev),
    naca: () => buildNaca(naca),
  };
  data.archivesView = archives;
  window.__workbench = { state, select: (id) => select(id), setExplode, setMode, loadSpecimen, get current() { return current; }, jointCheck: () => current?.joints, pickAt: (x, y) => { const hit = pick({ clientX: x, clientY: y }); return hit ? { part: hit.object.__part, point: hit.point.toArray().map((v) => +v.toFixed(2)) } : null; } };
  await loadSpecimen(params.get("specimen") || "rocket", data);
  wireControls(data);
  if (params.get("explode")) setExplode(Number(params.get("explode")) / 100);
  if (params.get("section")) toggleSection(true);
  if (params.get("overlay")) params.get("overlay").split(",").forEach((o) => toggleOverlay(o, true));
  if (params.get("select")) select(params.get("select"));
  requestAnimationFrame(frame);
}

function initScene() {
  ({ renderer, labels } = createRenderer(viewport));
  scene = new THREE.Scene();
  scene.background = null;
  rig = new CameraRig(renderer.domElement);
  rig.controls.addEventListener("change", invalidate);
  studioLights(scene);
  environment(renderer, scene, 0.55);
  gizmo = new AxisGizmo();
  sectionPlane = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 0);
  autoResize(viewport, renderer, labels, rig, invalidate);
  scene.fog = null;
}

// ---------------------------------------------------------------------------
// Specimens
// ---------------------------------------------------------------------------
const SPECIMEN_LIST = [
  { id: "rocket", title: "Folding Stabilized Rocket", sub: "OpenRocket design file → parametric 3D", asset: "source-model", src: "Simulation/Folding Stabilized Rocket.ork" },
  { id: "fourbar", title: "Four-bar linkage", sub: "STEP export → OpenCascade tessellation", asset: "source-cad", src: "CAD Files/Four Bar Linkage.step" },
  { id: "naca", title: "NACA 0012 fin profile", sub: "Tested generator output (C3)", asset: "source-model", src: "CAD Files/naca_fin_generator.py" },
  { id: "archives", title: "Fusion 360 archives", sub: "Inventory only — not translated", asset: "not-translated", src: "CAD Files/*.f3z" },
];

function renderSpecimenList(data) {
  const list = $("#specimens");
  clear(list, SPECIMEN_LIST.map((s) => {
    const b = h("button", { class: "specimen", type: "button", role: "radio", "aria-checked": "false", "data-id": s.id },
      h("b", {}, s.title), h("span", { class: "cluster" }, assetBadge(s.asset)), h("span", { class: "muted", style: { fontSize: "12px" } }, s.sub), h("span", { class: "src" }, s.src));
    b.addEventListener("click", () => loadSpecimen(s.id, data));
    return b;
  }));
}

async function loadSpecimen(id, data) {
  data = data || loadSpecimen.data;
  loadSpecimen.data = data;
  $$(".specimen").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.id === id)));
  const placard = $("#placard");
  if (id === "archives") {
    showArchives(data.archives);
    placard.hidden = false;
    renderInspectorArchive(data.archives);
    $("#tree").replaceChildren(h("p", { class: "panel-body muted" }, "No geometry was translated, so there is no hierarchy to show. The archive's own component list is in the inspector."));
    updateClassHUD({ assetClass: "not-translated", title: "Fusion 360 archives" });
    return;
  }
  placard.hidden = true;
  if (current) { scene.remove(current.root); disposeTree(current.root); }
  clearMeasure();
  state.hidden.clear(); state.isolated = null; state.selected = null; state.overlays.clear();
  current = specimens[id]();
  current.overlayObjects = {};
  scene.add(current.root);
  current.root.updateMatrixWorld(true);
  // Attach part-specific dimensions to their parts so they travel with the explosion.
  for (const dim of [...(current.dims?.children || [])]) {
    const pid = dim.userData.part;
    const gid = dim.userData.id || "";
    if (!pid || gid.endsWith("-station")) { dim.userData.global = true; continue; }
    const part = current.parts.find((p) => p.id === pid);
    if (!part) { dim.userData.global = true; continue; }
    let host = part.group;
    if (part.kind === "trapezoidfinset") host = part.group.children.find((c) => (((c.userData.instance?.angleDeg ?? 0) % 360) + 360) % 360 === 0) || host;
    host.attach(dim);
  }
  const planItems = current.plan.map((p) => ({ ...p }));
  plan = { items: planItems, ...explodePlan(planItems, { axis: current.axis, spread: 100 }) };
  // floor + grid sized to the specimen
  if (gridObj) scene.remove(gridObj);
  if (shadowFloor) scene.remove(shadowFloor);
  const box = partsBox();
  const size = box.getSize(new THREE.Vector3());
  const span = Math.max(size.x, size.y, size.z);
  const minor = span > 300 ? 10 : 1;
  gridObj = blueprintGrid(Math.ceil((span * 2.6) / (minor * 10)) * minor * 10, minor);
  gridObj.position.y = current.flat ? box.min.y - span * 0.35 : box.min.y - Math.max(span * 0.06, 4);
  scene.add(gridObj);
  shadowFloor = new THREE.Mesh(new THREE.PlaneGeometry(span * 4, span * 4), new THREE.ShadowMaterial({ opacity: 0.28 }));
  shadowFloor.rotation.x = -Math.PI / 2; shadowFloor.position.y = gridObj.position.y - 0.05; shadowFloor.receiveShadow = true;
  scene.add(shadowFloor);
  const key = scene.getObjectByName("studio-lights").children[1];
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  const sc = key.shadow.camera; sc.left = -span; sc.right = span; sc.top = span; sc.bottom = -span; sc.near = 0.1; sc.far = span * 10;
  key.position.set(span * 0.8, span * 1.6, span * 1.0);
  key.target.position.set(0, 0, 0);
  sc.updateProjectionMatrix();
  // UI
  renderTree();
  renderOverlayButtons();
  renderTicks();
  updateClassHUD(current);
  $("#vp-info").innerHTML = current.info;
  updateScale();
  renderInspector(null);
  for (const o of current.overlays) if (o.on) toggleOverlay(o.id, true);
  applyAll();
  setExplode(0, { silent: true });
  rig.frame(box, current.frameDir, { animate: false, margin: 1.05 });
  rig.controls.saveState?.();
  announce(`${current.title} loaded`);
  invalidate();
}

function partsBox() {
  const box = new THREE.Box3();
  current.parts.forEach((p) => p.group.traverse((o) => { if ((o.isMesh || o.isLine) && o.geometry) { o.geometry.computeBoundingBox(); box.union(o.geometry.boundingBox.clone().applyMatrix4(o.matrixWorld)); } }));
  return box;
}

function disposeTree(obj) {
  obj.traverse((o) => {
    if (o.geometry) o.geometry.dispose();
    if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => { m.map?.dispose(); m.dispose(); });
    if (o.isCSS2DObject) o.element.remove();
  });
}

// ---------------------------------------------------------------------------
// Rendering state
// ---------------------------------------------------------------------------
function clipping() {
  if (!state.section.on) return [];
  return [sectionPlane];
}

function applyAll() {
  if (!current) return;
  const clip = clipping();
  for (const part of current.parts) {
    const hidden = state.hidden.has(part.id);
    const ghost = state.isolated && state.isolated !== part.id;
    const highlight = state.selected === part.id;
    part.group.visible = !hidden;
    part.group.traverse((o) => { if (o.userData.visuals) applyMode(o, state.mode, { clipping: clip, ghost, highlight }); });
    if (part.kind === "profile") part.group.children.forEach((c) => { if (c.material?.color && c.isLineLoop) c.material.color.set(highlight ? 0xe0a274 : 0xf1e9d6); });
  }
  for (const [id, obj] of Object.entries(current.overlayObjects)) {
    obj.traverse((o) => { if (o.userData.visuals) applyMode(o, state.mode, { clipping: clip }); });
  }
  if (current.dims) current.dims.visible = state.dims;
  current.root.traverse((o) => {
    if (o.userData.kind === "dimension") {
      const tierOK = o.userData.tier !== "part" || state.selected === o.userData.part || current.id !== "rocket";
      o.visible = state.dims && tierOK && !(o.userData.global && state.explode > 0.02);
    }
    if (o.isCSS2DObject && o.element.classList.contains("part-label")) o.visible = state.labels;
    if (o.userData.kind === "centerline") o.visible = state.mode === "blueprint" || state.mode === "wireframe";
  });
  const blueprint = state.mode === "blueprint";
  gridObj.children[0].material.opacity = blueprint ? 0.16 : 0.06;
  gridObj.children[1].material.opacity = blueprint ? 0.32 : 0.14;
  shadowFloor.visible = state.mode === "clay" || state.mode === "solid";
  renderer.toneMappingExposure = state.mode === "clay" ? 1.08 : 1.0;
  viewport.classList.toggle("is-blueprint", blueprint);
  viewport.style.background = blueprint ? "radial-gradient(ellipse at 50% 40%, #0d2a3e 0%, #071522 75%)" : "";
  updateSectionPlane();
  invalidate();
}

function setMode(mode) {
  state.mode = mode;
  $$("#modes .btn").forEach((b) => press(b, b.dataset.mode === mode));
  applyAll();
  updateClassHUD(current);
  announce(`Rendering: ${mode}`);
}

// ---------------------------------------------------------------------------
// Explode
// ---------------------------------------------------------------------------
function setExplode(amount, { silent = false } = {}) {
  if (!current) return;
  state.explode = Math.min(Math.max(amount, 0), 1);
  const offsets = plan.offsets(state.explode, { sequential: state.sequential });
  for (const item of plan.items) {
    const target = item.child || current.parts.find((p) => p.id === item.part)?.group;
    if (!target) continue;
    const o = offsets.get(item.id);
    target.position.set(o[0], o[1], o[2]);
  }
  const input = $("#explode");
  input.value = String(state.explode * 100);
  input.dispatchEvent(new Event("sync"));
  $("#explode-out").textContent = `${Math.round(state.explode * 100)}%`;
  press($("#btn-explode"), state.explode > 0.5);
  current.root.traverse((o) => {
    if (o.userData.kind === "dimension" && o.userData.global) o.visible = state.dims && state.explode <= 0.02 && (o.userData.tier !== "part" || state.selected === o.userData.part || current.id !== "rocket");
  });
  updateReadouts();
  if (!silent) invalidate();
  invalidate();
}

function animateExplode(to, { sequential = state.sequential, duration = 3600 } = {}) {
  if (state.anim) { state.anim = null; updateAnimButtons(); return; }
  state.sequential = sequential;
  $("#sequential").checked = sequential;
  const from = state.explode;
  if (reducedMotion()) { setExplode(to); return; }
  const start = performance.now();
  const span = Math.abs(to - from) * duration || 1;
  state.anim = { tick: (now) => {
    const t = Math.min((now - start) / span, 1);
    setExplode(from + (to - from) * t, { silent: true });
    if (t >= 1) { state.anim = null; updateAnimButtons(); announce(to > 0.5 ? "Disassembled" : "Assembled"); }
  } };
  updateAnimButtons();
}

function updateAnimButtons() {
  $("#btn-sequence").textContent = state.anim ? "❚❚ Pause" : "▶ Disassemble";
  $("#btn-reverse").textContent = state.anim ? "❚❚ Pause" : "◀ Assemble";
}

function renderTicks() {
  const ticks = $("#explode-ticks");
  clear(ticks);
  if (!plan.sequence.length) return;
  const stagger = 0.55, n = plan.sequence.length;
  const seen = new Set();
  plan.sequence.forEach((id, i) => {
    const item = plan.items.find((x) => x.id === id);
    const part = current.parts.find((p) => p.id === item.part);
    if (!part || seen.has(part.id) || item.distance === 0) return;
    seen.add(part.id);
    const start = n > 1 ? (i / (n - 1)) * stagger : 0;
    const short = { nosecone: "Nose", bodytube: part.name.replace("Body ", ""), motor: "Motor env.", trapezoidfinset: part.id === "fins1" ? "Fwd fins" : "Aft fins", link: part.name.replace(" link", "") }[part.kind] || part.name;
    ticks.append(h("span", { style: { left: `${(start + (1 - stagger) / 2) * 100}%`, top: `${(seen.size % 2) * 9}px` }, title: part.name }, short));
  });
}

// ---------------------------------------------------------------------------
// Section plane
// ---------------------------------------------------------------------------
function sectionBox() {
  const box = new THREE.Box3();
  current.parts.forEach((p) => box.expandByObject(p.group));
  return box;
}

function updateSectionPlane() {
  if (!current) return;
  const s = state.section;
  const box = sectionBox();
  const axisIdx = { x: 0, y: 1, z: 2 }[s.axis];
  const min = box.min.getComponent(axisIdx), max = box.max.getComponent(axisIdx);
  const pos = min + (max - min) * s.t;
  const n = new THREE.Vector3(); n.setComponent(axisIdx, s.flip ? 1 : -1);
  sectionPlane.normal.copy(n);
  sectionPlane.constant = s.flip ? -pos : pos;
  if (planeHelper) { scene.remove(planeHelper); planeHelper.geometry.dispose(); planeHelper = null; }
  if (s.on && s.showPlane) {
    const size = box.getSize(new THREE.Vector3()).multiplyScalar(1.15);
    const dims = [size.x, size.y, size.z].filter((_, i) => i !== axisIdx);
    const g = new THREE.PlaneGeometry(Math.max(dims[0], 1), Math.max(dims[1], 1));
    planeHelper = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color: 0x67d8cf, transparent: true, opacity: 0.07, side: THREE.DoubleSide, depthWrite: false }));
    const border = new THREE.LineSegments(new THREE.EdgesGeometry(g), new THREE.LineBasicMaterial({ color: 0x67d8cf, transparent: true, opacity: 0.6 }));
    planeHelper.add(border);
    const c = box.getCenter(new THREE.Vector3());
    c.setComponent(axisIdx, pos);
    planeHelper.position.copy(c);
    if (s.axis === "x") planeHelper.rotation.y = Math.PI / 2;
    if (s.axis === "y") planeHelper.rotation.x = Math.PI / 2;
    scene.add(planeHelper);
  }
  const local = current.root.worldToLocal(new THREE.Vector3().setComponent(axisIdx, pos)).getComponent(axisIdx);
  const name = { x: "transverse (normal X)", y: "horizontal (normal Y)", z: "longitudinal (normal Z)" }[s.axis];
  $("#section-out").textContent = s.on ? `${name} at ${s.axis.toUpperCase()} = ${local.toFixed(1)} mm${current.id === "rocket" && s.axis === "x" ? " from nose tip" : ""}` : "off";
}

function toggleSection(on = !state.section.on) {
  state.section.on = on;
  press($("#btn-section"), on);
  $("#section-controls").setAttribute("aria-disabled", String(!on));
  applyAll();
  announce(on ? "Section plane on" : "Section plane off");
}

// ---------------------------------------------------------------------------
// Overlays
// ---------------------------------------------------------------------------
function renderOverlayButtons() {
  const box = $("#vp-overlays");
  clear(box, current.overlays.map((o) => {
    const b = h("button", { class: "btn", type: "button", "aria-pressed": "false", "data-overlay": o.id, title: o.title }, o.label, o.illustrative ? h("span", { class: "asset asset-illustration", style: { marginLeft: "4px" } }, "illustrative") : null);
    b.addEventListener("click", () => toggleOverlay(o.id));
    return b;
  }));
}

function toggleOverlay(id, on) {
  const o = current?.overlays.find((x) => x.id === id);
  if (!o) return;
  const next = on ?? !state.overlays.has(id);
  if (next) state.overlays.add(id); else state.overlays.delete(id);
  if (o.target) o.target.visible = next;
  else if (next && !current.overlayObjects[id]) { current.overlayObjects[id] = o.build(); current.root.add(current.overlayObjects[id]); }
  else if (current.overlayObjects[id]) current.overlayObjects[id].visible = next;
  const btn = $(`[data-overlay="${id}"]`);
  if (btn) press(btn, next);
  if (next && current.overlayObjects[id]?.userData.legend) $("#vp-info").innerHTML = `${current.info}<br><span class="muted">${current.overlayObjects[id].userData.legend}</span>`;
  else $("#vp-info").innerHTML = current.info;
  applyAll();
}

// ---------------------------------------------------------------------------
// Hierarchy tree
// ---------------------------------------------------------------------------
function renderTree() {
  const tree = $("#tree");
  clear(tree);
  $("#tree-count").textContent = `${current.parts.length} parts`;
  current.tree.forEach((node) => {
    const part = current.parts.find((p) => p.id === node.id);
    const row = h("div", { class: `tree-row ${node.type === "group" ? "group-row" : ""}`, role: "treeitem", "aria-level": String(node.depth + 1), tabindex: "-1", "data-id": node.id, style: { "--depth": node.depth }, "aria-selected": "false" });
    if (part) {
      const eye = h("button", { class: "eye", type: "button", "aria-label": `Hide ${node.label}`, title: "Show / hide (H)" }, "◉");
      eye.addEventListener("click", (e) => { e.stopPropagation(); toggleHidden(part.id); });
      const iso = h("button", { class: "iso", type: "button", "aria-pressed": "false", "aria-label": `Isolate ${node.label}`, title: "Isolate: ghost everything else (I)" }, "ISO");
      iso.addEventListener("click", (e) => { e.stopPropagation(); toggleIsolate(part.id); });
      row.append(eye, h("span", { class: "name" }, node.label, node.sub ? h("small", {}, node.sub) : null), iso);
      row.addEventListener("click", () => select(part.id));
    } else {
      row.append(h("span", { "aria-hidden": "true" }, "▾"), h("span", { class: "name" }, node.label), h("span"));
      row.addEventListener("click", () => select(null));
    }
    row.addEventListener("keydown", (e) => treeKeys(e, row));
    tree.append(row);
  });
  const first = tree.querySelector(".tree-row");
  if (first) first.tabIndex = 0;
  const legend = $("#legend");
  clear(legend, h("div", { class: "label" }, "Asset classes in this lab"),
    ...Object.entries(ASSETS).map(([k, a]) => h("div", { class: "cluster", title: a.text }, assetBadge(k))),
    h("p", { class: "muted", style: { fontSize: "11.5px", margin: "6px 0 0" } }, current.explodeNote));
}

function treeKeys(e, row) {
  const rows = $$(".tree-row");
  const i = rows.indexOf(row);
  const focus = (r) => { if (!r) return; rows.forEach((x) => { x.tabIndex = -1; }); r.tabIndex = 0; r.focus(); };
  if (e.key === "ArrowDown") { e.preventDefault(); focus(rows[i + 1]); }
  else if (e.key === "ArrowUp") { e.preventDefault(); focus(rows[i - 1]); }
  else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); row.click(); }
  else if (e.key.toLowerCase() === "h" && row.dataset.id) { e.stopPropagation(); toggleHidden(row.dataset.id); }
  else if (e.key.toLowerCase() === "i" && row.dataset.id) { e.stopPropagation(); toggleIsolate(row.dataset.id); }
}

function syncTree() {
  $$(".tree-row").forEach((row) => {
    const id = row.dataset.id;
    row.setAttribute("aria-selected", String(id === state.selected));
    row.classList.toggle("hidden-part", state.hidden.has(id));
    const eye = row.querySelector(".eye");
    if (eye) { eye.textContent = state.hidden.has(id) ? "◌" : "◉"; eye.setAttribute("aria-label", `${state.hidden.has(id) ? "Show" : "Hide"} ${row.querySelector(".name").textContent}`); }
    const iso = row.querySelector(".iso");
    if (iso) press(iso, state.isolated === id);
  });
}

function toggleHidden(id) {
  if (state.hidden.has(id)) state.hidden.delete(id); else state.hidden.add(id);
  syncTree(); applyAll();
  announce(`${id} ${state.hidden.has(id) ? "hidden" : "shown"}`);
}

function toggleIsolate(id) {
  state.isolated = state.isolated === id ? null : id;
  if (state.isolated) { state.hidden.delete(id); select(id); }
  syncTree(); applyAll();
  announce(state.isolated ? `${id} isolated; other parts ghosted` : "Isolation cleared");
}

// ---------------------------------------------------------------------------
// Selection & inspector
// ---------------------------------------------------------------------------
function select(id) {
  state.selected = id;
  syncTree();
  applyAll();
  renderInspector(id ? current.parts.find((p) => p.id === id) : null);
  if (id) announce(`Selected ${current.parts.find((p) => p.id === id)?.name}`);
}

function evidenceChips(claims = [], discrepancies = [], observations = []) {
  const box = h("div", {});
  for (const cid of claims) {
    const c = evidence.claims.find((x) => x.id === cid);
    if (c) box.append(h("a", { class: "chip-link", href: claimLink(cid), title: c.status_meaning }, `${cid}`, statusChip(c.status, c.status_label)));
  }
  for (const did of discrepancies) {
    const d = evidence.discrepancies.find((x) => x.id === did);
    if (d) box.append(h("a", { class: "chip-link", href: discrepancyLink(did), title: d.title }, `${did} · ${d.status.toUpperCase()}`));
  }
  for (const oid of observations) box.append(h("span", { class: "chip-link", title: "Candidate for human review; not in the discrepancy register" }, `${oid} · CANDIDATE`));
  return box;
}

function renderInspector(part) {
  const el = $("#inspector");
  if (!part) {
    const c = current;
    clear(el,
      h("div", { class: "cluster" }, categoryBadge("research"), assetBadge(c.assetClass)),
      h("h3", {}, c.title), h("p", { class: "muted" }, c.subtitle),
      h("dl", { class: "kv" }, h("dt", {}, "Source"), h("dd", {}, h("a", { href: repoLink(c.source.path) }, c.source.path)),
        h("dt", {}, "SHA-256"), h("dd", { class: "hash" }, c.source.sha256 || "—"),
        h("dt", {}, "Parts"), h("dd", {}, String(c.parts.length))),
      h("section", {}, h("h4", {}, "Evidence"), evidenceChips(c.claims, c.discrepancies, (c.observations || []).map((o) => o.id))),
      ...(c.observations || []).map((o) => h("div", { class: "obs" }, h("div", { class: "label" }, `${o.id} · ${o.status}`), h("p", {}, h("b", {}, o.title)), h("p", {}, o.detail), h("p", { class: "muted" }, o.not_computed))),
      c.joints ? h("section", {}, h("h4", {}, "Joint check (from STEP geometry)"), h("p", {}, `${c.joints.concentric.length} of ${c.joints.pairsConsidered} hole pairs on different links share an axis. A pinned four-bar needs four. The file is four separate bars, as D-005 records.`)) : null,
      h("p", { class: "muted", style: { fontSize: "12px" } }, "Select a part in the viewport or the hierarchy to inspect it. Values come only from the source; anything absent is marked NOT SPECIFIED or NOT MEASURED."));
    return;
  }
  const m = part.meta;
  const depths = h("div", { id: `depth-${part.id}` });
  depthTabs(depths, [
    { label: "Introduction", content: (p) => p.append(h("p", {}, m.depths.intro || "")) },
    { label: "Engineering", content: (p) => (m.depths.engineering || []).forEach((t) => p.append(rich(t))) },
    { label: "Research", content: (p) => p.append(h("dl", { class: "kv" }, ...(m.research || []).flatMap((r) => [h("dt", {}, r.k), h("dd", { class: r.k === "SHA-256" ? "hash" : "" }, r.v)]))) },
  ]);
  clear(el,
    h("div", { class: "cluster" }, categoryBadge("research"), assetBadge(m.assetClass)),
    h("h3", {}, m.title),
    h("dl", { class: "kv" },
      h("dt", {}, "Component ID"), h("dd", { class: "mono", style: { fontSize: "11px" } }, m.componentId),
      h("dt", {}, "Source file"), h("dd", {}, h("a", { href: repoLink(m.sourceFile) }, m.sourceFile)),
      h("dt", {}, "Source path"), h("dd", { class: "src" }, m.sourcePath),
      h("dt", {}, "Mass"), h("dd", {}, m.mass ? [m.mass.text.startsWith("NOT") ? h("span", { class: "not-measured" }, m.mass.text.split(" — ")[0]) : m.mass.text.split(" — ")[0], h("div", { class: "muted", style: { fontSize: "11px" } }, m.mass.text.split(" — ")[1] || ""), m.mass.src ? h("div", { class: "src" }, m.mass.src) : null] : h("span", { class: "not-measured" }, "NOT MEASURED")),
      h("dt", {}, "Material"), h("dd", {}, m.material ? [m.material.text.split(" — ")[0], h("div", { class: "muted", style: { fontSize: "11px" } }, m.material.text.split(" — ")[1]), h("div", { class: "src" }, m.material.src)] : h("span", { class: "not-measured" }, "NOT SPECIFIED")),
      h("dt", {}, "Tolerance"), h("dd", {}, h("span", { class: "not-measured" }, "NOT SPECIFIED")),
      h("dt", {}, "Manufacturing"), h("dd", {}, h("span", { class: "not-measured" }, "NOT SPECIFIED"))),
    h("section", {}, h("h4", {}, "Known dimensions"),
      h("table", { class: "data dim-table" }, h("tbody", {}, m.dims.map((d) => h("tr", {}, h("td", {}, d.q), h("td", { class: "num" }, String(d.v ?? "—").startsWith("NOT") ? h("span", { class: "not-measured" }, d.v) : d.v), h("td", { class: "src" }, d.src || "")))))),
    h("section", {}, h("h4", {}, "Explanation"), depths),
    h("section", {}, h("h4", {}, "Modeling assumptions"), h("ul", {}, m.assumptions.map((a) => h("li", {}, a)))),
    h("section", {}, h("h4", {}, "Documented limitations"), h("ul", {}, m.limitations.map((a) => h("li", {}, a)))),
    h("section", {}, h("h4", {}, "Evidence passport links"), evidenceChips(m.claims, m.discrepancies, m.observations)),
  );
}

function renderInspectorArchive(arch) {
  const el = $("#inspector");
  clear(el, h("div", { class: "cluster" }, categoryBadge("research"), assetBadge("not-translated")),
    h("h3", {}, "Fusion 360 archives"),
    h("p", {}, arch.archives[0].translation.reason),
    h("p", { class: "muted" }, arch.archives[0].translation.unblock),
    ...arch.archives.map((a) => h("section", {}, h("h4", {}, a.path),
      h("dl", { class: "kv" }, h("dt", {}, "SHA-256"), h("dd", { class: "hash" }, a.sha256), h("dt", {}, "Bytes"), h("dd", { class: "num" }, a.bytes.toLocaleString())),
      h("table", { class: "data" }, h("thead", {}, h("tr", {}, h("th", {}, "Design (as named in archive)"), h("th", { class: "num" }, "Ver."), h("th", { class: "num" }, "B-rep faces*"))),
        h("tbody", {}, a.designs.map((d) => h("tr", {}, h("td", {}, d.name, d.is_root ? h("span", { class: "label", style: { marginLeft: "6px" } }, "root") : null), h("td", { class: "num" }, d.version), h("td", { class: "num" }, d.current_state_statistics.faces.toLocaleString()))))))),
    h("p", { class: "muted", style: { fontSize: "11.5px" } }, "* Faces in the current state of each body blob, counted by tools/sab_inventory.py. Blobs may include intermediate timeline bodies, so counts describe archive content, not the final design."));
}

function showArchives(arch) {
  const placard = $("#placard");
  clear(placard, h("div", { class: "inner" },
    h("div", { class: "cluster" }, categoryBadge("research"), assetBadge("not-translated")),
    h("h2", {}, "The Fusion archives stay closed — on purpose."),
    h("p", { class: "lede" }, "These are the project's authoritative CAD sources. Their bodies are Autodesk ShapeManager B-rep, and their placements live in proprietary streams. A partial or unplaced conversion would draw an assembly the record cannot support, so the lab shows what the archives contain instead of guessing what they look like in 3D."),
    h("p", { class: "muted" }, "Preview images below are thumbnails Autodesk rendered and stored inside each archive. They are pictures of the designs, not measurements."),
    h("div", { class: "archive-grid" }, arch.archives.flatMap((a) => a.designs.filter((d) => d.preview).map((d) =>
      h("figure", {}, h("img", { src: `../${d.preview}`, alt: `Fusion-embedded preview of ${d.name}`, loading: "lazy" }),
        h("figcaption", {}, h("span", { class: "label" }, a.path.replace("CAD Files/", "")), d.name))))),
    h("div", { class: "notice" }, h("span", {}, "To unlock true assembly geometry: export STEP from Fusion 360 into ", h("code", {}, "CAD Files/exports/"), " and run ", h("code", {}, "python tools/cad_to_web.py"), ". The workbench will load it with part names and provenance."))));
}

function updateClassHUD(c) {
  if (!c) return;
  clear($("#vp-class"), categoryBadge("research"), assetBadge(c.assetClass),
    h("span", { class: "asset asset-illustration" }, state.mode === "clay" ? "clay rendering" : `${state.mode} rendering`),
    state.explode > 0 && c.explodeNote ? h("span", { class: "asset asset-reconstructed", title: c.explodeNote }, "illustrative separation") : null);
}

// ---------------------------------------------------------------------------
// Picking & measuring
// ---------------------------------------------------------------------------
const ray = new THREE.Raycaster();
function pick(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  const ndc = new THREE.Vector2(((event.clientX - rect.left) / rect.width) * 2 - 1, -((event.clientY - rect.top) / rect.height) * 2 + 1);
  ray.setFromCamera(ndc, rig.camera);
  const meshes = current.parts.filter((p) => !state.hidden.has(p.id)).flatMap((p) => p.pickables.map((m) => Object.assign(m, { __part: p.id })));
  const hits = ray.intersectObjects(meshes, false).filter((hit) => !state.section.on || sectionPlane.distanceToPoint(hit.point) >= 0);
  return hits[0] || null;
}

function onClick(event) {
  if (!current) return;
  const hit = pick(event);
  if (state.measure) {
    if (!hit) return;
    addMeasurePoint(hit.point);
    return;
  }
  select(hit ? hit.object.__part : null);
}

function addMeasurePoint(p) {
  if (measurePts.length === 2) clearMeasure();
  measurePts.push(p.clone());
  const dot = new THREE.Mesh(new THREE.SphereGeometry(current.lengthMM / 300, 12, 10), new THREE.MeshBasicMaterial({ color: 0xe0a274, depthTest: false }));
  dot.position.copy(p); dot.renderOrder = 20;
  scene.add(dot); measureObjs.push(dot);
  if (measurePts.length === 2) {
    const [a, b] = measurePts;
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([a, b]), new THREE.LineBasicMaterial({ color: 0xe0a274, depthTest: false }));
    line.renderOrder = 20;
    const d = a.distanceTo(b);
    const lbl = label3D(`${d.toFixed(2)} mm`, { className: "css2d-label warn", sub: "on displayed geometry" });
    lbl.position.copy(a).lerp(b, 0.5);
    scene.add(line, lbl); measureObjs.push(line, lbl);
    state.lastMeasure = d;
    announce(`Distance ${d.toFixed(2)} millimetres`);
  }
  updateReadouts();
  invalidate();
}

function clearMeasure() {
  measureObjs.forEach((o) => { scene?.remove(o); if (o.isCSS2DObject) o.element.remove(); o.geometry?.dispose(); });
  measureObjs = []; measurePts = []; state.lastMeasure = null;
  updateReadouts();
}

function updateReadouts() {
  const r = $("#readouts");
  if (!r || !current) return;
  const lines = [
    h("div", {}, "Specimen: ", h("b", {}, current.title)),
    h("div", {}, "Projection: ", h("b", {}, state.ortho ? "orthographic" : "perspective"), " · units ", h("b", {}, "mm")),
    state.measure ? h("div", {}, "Measure: ", measurePts.length === 0 ? "click a surface point" : measurePts.length === 1 ? "click a second point" : h("b", {}, `${state.lastMeasure.toFixed(2)} mm`),
      h("span", { class: "muted" }, current.id === "fourbar" ? " (tessellation ±0.01 mm)" : " (display mesh)")) : null,
    state.explode > 0 ? h("div", { class: "muted" }, current.explodeNote) : null,
  ];
  clear(r, ...lines);
}

function updateScale() {
  const L = current.lengthMM;
  const nice = [1, 2, 5, 10, 20, 50, 100, 200, 500][[1, 2, 5, 10, 20, 50, 100, 200, 500].findIndex((v) => v > L / 8) || 0];
  clear($("#vp-scale"), h("span", {}, `Grid: ${L > 300 ? "10 mm minor · 100 mm major" : "1 mm minor · 10 mm major"}`));
}

// ---------------------------------------------------------------------------
// Controls
// ---------------------------------------------------------------------------
function wireControls(data) {
  const explode = syncRange($("#explode"));
  explode.addEventListener("sync", () => explode.style.setProperty("--fill", `${explode.value}%`));
  explode.addEventListener("input", () => { state.anim = null; updateAnimButtons(); setExplode(Number(explode.value) / 100); updateClassHUD(current); });
  $("#sequential").addEventListener("change", (e) => { state.sequential = e.target.checked; setExplode(state.explode); });
  $("#btn-explode").addEventListener("click", () => { animateExplode(state.explode > 0.5 ? 0 : 1, { sequential: false, duration: 1400 }); updateClassHUD(current); });
  $("#btn-sequence").addEventListener("click", () => { if (state.explode >= 0.999 && !state.anim) setExplode(0); animateExplode(1, { sequential: true }); updateClassHUD(current); });
  $("#btn-reverse").addEventListener("click", () => { if (state.explode <= 0.001 && !state.anim) setExplode(1); animateExplode(0, { sequential: true }); });
  $$("#modes .btn").forEach((b) => b.addEventListener("click", () => setMode(b.dataset.mode)));
  $("#btn-section").addEventListener("click", () => toggleSection());
  const section = syncRange($("#section"));
  section.addEventListener("input", () => { state.section.t = Number(section.value) / 1000; if (!state.section.on) toggleSection(true); else applyAll(); });
  $$("#section-axis .btn").forEach((b) => b.addEventListener("click", () => { state.section.axis = b.dataset.axis; $$("#section-axis .btn").forEach((x) => press(x, x === b)); if (!state.section.on) toggleSection(true); else applyAll(); }));
  $("#section-flip").addEventListener("click", () => { state.section.flip = !state.section.flip; applyAll(); });
  $("#section-plane-show").addEventListener("change", (e) => { state.section.showPlane = e.target.checked; applyAll(); });
  $("#btn-ortho").addEventListener("click", () => { state.ortho = press($("#btn-ortho")); rig.setProjection(state.ortho); updateReadouts(); invalidate(); announce(state.ortho ? "Orthographic projection" : "Perspective projection"); });
  $("#btn-dims").addEventListener("click", () => { state.dims = press($("#btn-dims")); applyAll(); });
  $("#btn-labels").addEventListener("click", () => { state.labels = press($("#btn-labels")); toggleLabels(); });
  $("#btn-measure").addEventListener("click", () => { state.measure = press($("#btn-measure")); if (!state.measure) clearMeasure(); updateReadouts(); viewport.style.cursor = state.measure ? "crosshair" : ""; });
  const views = $("#views");
  for (const [key, v] of Object.entries(VIEWS)) {
    const b = h("button", { class: "btn", type: "button", "data-view": key, title: `${v.label} view` }, v.label.slice(0, key === "iso" ? 3 : 2));
    b.addEventListener("click", () => setView(key));
    views.append(b);
  }
  $("#btn-reset").addEventListener("click", reset);
  $("#btn-full").addEventListener("click", () => {
    const target = $(".wb-center");
    if (document.fullscreenElement) document.exitFullscreen(); else target.requestFullscreen?.();
  });
  $("#btn-shot").addEventListener("click", screenshot);
  $$(".wb-collapse").forEach((b) => b.addEventListener("click", () => { grid.classList.toggle(`collapse-${b.dataset.collapse}`); }));
  // Click vs drag
  let down = null;
  renderer.domElement.addEventListener("pointerdown", (e) => { down = { x: e.clientX, y: e.clientY }; });
  renderer.domElement.addEventListener("pointerup", (e) => { if (down && Math.hypot(e.clientX - down.x, e.clientY - down.y) < 5) onClick(e); down = null; });
  window.addEventListener("keydown", keys);
  toggleLabels();
}

function setView(key) {
  const v = VIEWS[key];
  current.root.updateMatrixWorld(true);
  rig.frame(partsBox(), new THREE.Vector3(...v.dir), { up: new THREE.Vector3(...v.up), margin: 1.08 });
  announce(`${v.label} view`);
  invalidate();
}

function toggleLabels() {
  if (!current) return;
  if (state.labels && !current.labelsBuilt) {
    for (const p of current.parts) {
      const box = new THREE.Box3().setFromObject(p.group);
      const lbl = label3D(p.name, { className: "css2d-label part-label" });
      const local = p.group.worldToLocal(new THREE.Vector3((box.min.x + box.max.x) / 2, box.max.y, (box.min.z + box.max.z) / 2));
      lbl.position.copy(local).add(new THREE.Vector3(0, current.lengthMM / 60, 0));
      p.group.add(lbl);
    }
    current.labelsBuilt = true;
  }
  applyAll();
}

function reset() {
  state.anim = null;
  setExplode(0);
  state.hidden.clear(); state.isolated = null;
  if (state.section.on) toggleSection(false);
  state.section = { on: false, axis: "x", t: 0.5, flip: false, showPlane: true };
  $("#section").value = "500"; $("#section").dispatchEvent(new Event("input"));
  toggleSection(false);
  $$("#section-axis .btn").forEach((x) => press(x, x.dataset.axis === "x"));
  if (state.ortho) { state.ortho = false; press($("#btn-ortho"), false); rig.setProjection(false); }
  clearMeasure();
  setMode("solid");
  select(null);
  rig.frame(partsBox(), current.frameDir, { margin: 1.05 });
  announce("Workbench reset");
}

async function screenshot() {
  const c = current;
  const lines = [
    `PROJECT 33 · ${c.title} · ${state.mode.toUpperCase()} rendering${state.section.on ? " · SECTION" : ""}${state.explode > 0 ? ` · EXPLODED ${Math.round(state.explode * 100)}% (illustrative)` : ""}`,
    `Source: ${c.source.path} · sha256 ${String(c.source.sha256 || "").slice(0, 16)} · ${ASSETS[c.assetClass].label.toUpperCase()}`,
    `Category: PROJECT 33 RESEARCH · a rendering is not a measurement · ${new Date().toISOString().slice(0, 10)}`,
  ];
  const blob = await stampedScreenshot(renderer, () => renderFrame(true), lines);
  downloadBlob(blob, `project33-${c.id}-${state.mode}.png`);
  announce("Screenshot exported");
}

function keys(e) {
  if (e.target.matches("input, textarea, select") || e.metaKey || e.ctrlKey || e.altKey) return;
  const k = e.key.toLowerCase();
  const map = { 1: "clay", 2: "solid", 3: "wireframe", 4: "blueprint", 5: "xray" };
  if (map[k]) setMode(map[k]);
  else if (k === "e") $("#btn-explode").click();
  else if (k === "s") toggleSection();
  else if (k === "o") $("#btn-ortho").click();
  else if (k === "d") $("#btn-dims").click();
  else if (k === "l") $("#btn-labels").click();
  else if (k === "m") $("#btn-measure").click();
  else if (k === "r") reset();
  else if (k === "p") screenshot();
  else if (k === "f" && !e.shiftKey) setView("iso");
  else if (k === "h" && state.selected) toggleHidden(state.selected);
  else if (k === "i" && state.selected) toggleIsolate(state.selected);
  else if (k === "escape") { select(null); if (state.isolated) toggleIsolate(state.isolated); }
  else return;
  e.preventDefault();
}

// ---------------------------------------------------------------------------
// Frame loop (renders on demand)
// ---------------------------------------------------------------------------
function renderFrame(force = false) {
  const w = renderer.domElement.width, hgt = renderer.domElement.height;
  renderer.setViewport(0, 0, w, hgt);
  renderer.render(scene, rig.camera);
  labels.render(scene, rig.camera);
  const size = Math.round(86 * renderer.getPixelRatio());
  gizmo.render(renderer, rig.camera, w - size - 10, hgt - size - 10, size);
}

function frame(now) {
  requestAnimationFrame(frame);
  if (!current) return;
  if (state.anim) { state.anim.tick(now); needsRender = true; }
  const moving = rig.tween || rig.controls.enableDamping;
  rig.update(now);
  if (rig.tween) needsRender = true;
  if (!needsRender && !moving) return;
  if (!needsRender && moving) { /* damping settles via change events */ }
  if (needsRender) { renderFrame(); needsRender = false; }
}

// ---------------------------------------------------------------------------
// 2D fallback when WebGL is unavailable
// ---------------------------------------------------------------------------
function fallback2D(or, step) {
  const el = $("#fallback");
  el.hidden = false;
  const { paths, length } = elevationPaths(or);
  const pad = 30, W = length + pad * 2, H = 520;
  const svg = `<svg viewBox="${-pad} ${-H / 2} ${W} ${H}" role="img" aria-label="Side elevation of the rocket generated from the OpenRocket file" style="width:100%;background:#071522">
    ${paths.map((p) => `<polyline points="${p.points.map(([x, y]) => `${x},${-y}`).join(" ")}" fill="${p.closed ? "rgba(103,216,207,0.08)" : "none"}" stroke="${p.fin ? "#e0a274" : "#eef6f8"}" stroke-width="${p.thin ? 0.6 : 1.2}" ${p.closed ? "" : ""}/>`).join("")}
  </svg>`;
  el.innerHTML = `<div class="cluster">${categoryBadge("research").outerHTML}${assetBadge("source-model").outerHTML}</div><h3>WebGL is not available — 2D side elevation</h3>${svg}
    <p class="muted">Generated from ${or.current.source.path}. Overall length ${(or.current.overall_length_m * 1000).toFixed(1)} mm. The four-bar STEP parts measure ${step.parts.map((p) => `${p.role} ${p.pin_spacing_mm_brep} mm`).join(", ")} between pin axes (from the STEP B-rep).</p>`;
}

boot().catch((err) => {
  console.error(err);
  const el = $("#fallback");
  el.hidden = false;
  el.textContent = `The workbench could not load its source data: ${err.message}`;
});
