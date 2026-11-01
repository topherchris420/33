// "Every Machine Begins With a Question." — the laboratory's opening film.
// The whole film is a pure function of time t: scrub, pause, replay, and skip all land on
// the same frame. The rocket is generated from the OpenRocket file; its dimensions, the
// evidence panel, and every status shown come from the committed record.
import { mountShell } from "../core/shell.js";
import { h, $, $$, clear, announce, reducedMotion, syncRange, press, webglAvailable } from "../core/dom.js";
import { lab, parseCSV, canonical } from "../core/data.js";
import { categoryBadge, assetBadge, statusChip } from "../core/taxonomy.js";
import { THREE, createRenderer, environment } from "../core/three-kit.js";
import { applyMode } from "../core/materials.js";
import { explodePlan } from "../core/math/explode.js";
import { makeWren, makeTally, Claymate } from "../core/claymates.js";
import { buildRocket } from "../workbench/specimens.js";
import { buildHangar, buildTable, buildPaper, buildPencil, buildLever, buildTurntable, buildHistoricalMiniature, buildLamps } from "./workshop.js";
import { FilmAudio } from "./audio.js";

mountShell();

const DURATION = 80;
const CHAPTERS = [
  { t: 0, name: "A question" }, { t: 7, name: "The workshop" }, { t: 14, name: "The lever" }, { t: 19, name: "The scan" },
  { t: 27, name: "Dimensions" }, { t: 31.5, name: "Exploded assembly" }, { t: 42, name: "Systems" }, { t: 50, name: "But does it work?" },
  { t: 56, name: "Between imagining and knowing" }, { t: 68, name: "Project 33" },
];
const CAPTIONS = [
  { a: 0.4, b: 6.6, sfx: "pencil on paper", text: "Every machine begins with a question." },
  { a: 15.1, b: 16.6, sfx: "lever clunks · lights dim", text: "" },
  { a: 19.0, b: 26.8, sfx: "scanner hum", text: "" },
  { a: 27.2, b: 31.2, sfx: "", text: "Each dimension is read from the design file." },
  { a: 31.5, b: 36.0, sfx: "parts separate", text: "Separation paths are illustrative — the file records positions, not an assembly procedure." },
  { a: 42.5, b: 49.6, sfx: "", text: "Sensors, electronics, and software — drawn as a schematic, not as physical placement." },
  { a: 50.0, b: 51.4, sfx: "everything stops", text: "" },
  { a: 56.0, b: 59.8, sfx: "", text: "Every machine begins as an idea." },
  { a: 59.8, b: 63.4, sfx: "", text: "Every design begins with assumptions." },
  { a: 63.4, b: 68.4, sfx: "", text: "But between imagining something and knowing something lies the most interesting part of engineering." },
];
const NARRATION = CAPTIONS.filter((c) => c.text && c.a >= 56).map((c) => ({ at: c.a, text: c.text }));
NARRATION.unshift({ at: 0.5, text: "Every machine begins with a question." });

// Optional fixed camera for rendering stills: ?cam=x,y,z,tx,ty,tz (used by tools/render_lab_poster.mjs).
const POSTER_CAM = (() => { const v = new URLSearchParams(location.search).get("cam"); const a = v ? v.split(",").map(Number) : null; return a && a.length === 6 && a.every(Number.isFinite) ? a : null; })();
const clamp01 = (x) => Math.min(Math.max(x, 0), 1);
const ease = (x) => { const k = clamp01(x); return k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2; };
const seg = (t, a, b) => clamp01((t - a) / (b - a));

let state = { t: 0, playing: false, cc: true, sound: false, voice: false, lastSpoken: -1, last: performance.now() };
let renderer, labels, scene, camera, composer, world, film;
const audio = new FilmAudio();

async function boot() {
  const [ev, or, csvText, inputs, cross] = await Promise.all([lab.evidence(), lab.openrocket(), canonical.c5Csv(), canonical.c5Inputs(), canonical.c5Crosscheck()]);
  buildEvidencePanel(ev);
  wireControls();
  if (!webglAvailable()) { $("#start").querySelector(".lede").textContent = "This film needs WebGL, which is unavailable here. The workbench and documents carry the same content."; return; }
  ({ renderer, labels } = createRenderer($("#stage")));
  renderer.toneMappingExposure = 1.05;
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x07090c);
  scene.fog = new THREE.Fog(0x07090c, 700, 2200);
  environment(renderer, scene, 0.25);
  camera = new THREE.PerspectiveCamera(32, 1, 1, 6000);
  world = buildWorld(or, { c5: { csv: parseCSV(csvText), inputs, cross }, observation: or.lab_observations[0] });
  if (!renderer.userData.software) {
    composer = new THREE.EffectComposer(renderer);
    composer.addPass(new THREE.RenderPass(scene, camera));
    composer.addPass(new THREE.UnrealBloomPass(new THREE.Vector2(512, 512), 0.55, 0.6, 0.82));
    composer.addPass(new THREE.OutputPass());
  }
  const resize = () => {
    const el = $("#stage");
    const w = el.clientWidth, hgt = el.clientHeight;
    renderer.setSize(w, hgt, false); labels.setSize(w, hgt);
    camera.aspect = w / hgt; camera.updateProjectionMatrix();
    composer?.setSize(w, hgt);
    render();
  };
  new ResizeObserver(resize).observe($("#stage"));
  resize();
  // Compile every shader up front: software renderers otherwise stall mid-film.
  try { await renderer.compileAsync(scene, camera); } catch { /* older drivers: compile lazily */ }
  window.__film = { get t() { return state.t; }, seek, play, pause, get playing() { return state.playing; }, world };
  const startAt = Number(new URLSearchParams(location.search).get("t"));
  seek(Number.isFinite(startAt) ? startAt : 0);
  if (reducedMotion()) $("#rm-note").hidden = false;
  requestAnimationFrame(tick);
}

function buildWorld(or, extra) {
  const w = {};
  buildHangar(scene);
  buildTable(scene);
  w.paper = buildPaper(scene, or);
  w.pencil = buildPencil(scene);
  w.lever = buildLever(scene);
  w.turntable = buildTurntable(scene);
  w.miniature = buildHistoricalMiniature(scene);
  w.lamps = buildLamps(scene);
  // Lights
  w.hemi = new THREE.HemisphereLight(0xc9dce6, 0x20160e, 0.6);
  w.key = new THREE.SpotLight(0xffe7c8, 120000, 1600, 0.55, 0.55, 2);
  w.key.position.set(260, 520, 360); w.key.target.position.set(0, 0, 0);
  w.key.castShadow = !renderer.userData.software;
  w.key.shadow.mapSize.set(2048, 2048); w.key.shadow.bias = -0.0004;
  w.rim = new THREE.DirectionalLight(0x67d8cf, 0.0);
  w.rim.position.set(-300, 200, -300);
  scene.add(w.hemi, w.key, w.key.target, w.rim);
  // Rocket from the OpenRocket file, at miniature scale (0.2 units per mm), on the turntable.
  w.spec = buildRocket(or, extra);
  w.rocket = w.spec.root;
  w.rocket.position.set(0, 0, 0);
  const holder = new THREE.Group();
  holder.scale.setScalar(0.2);
  holder.position.y = 9 + 0.2 * 38.1 * 0.2;
  holder.position.y = 16;
  holder.add(w.rocket);
  w.turntable.top.add(holder);
  w.holder = holder;
  w.spec.unspecified.visible = false;
  for (const part of w.spec.parts) part.group.traverse((o) => { if (o.userData.visuals) applyMode(o, "clay"); });
  w.clayMats = [];
  w.spec.root.traverse((o) => { if (o.userData.role === "clay") w.clayMats.push(o.material); });
  // Dimensions: keep the overview chain, hide part-tier ones (they would crowd the film).
  w.dims = [];
  w.spec.root.traverse((o) => { if (o.userData.kind === "dimension") { o.visible = false; if (o.userData.tier === "overview") w.dims.push(o); } });
  w.plan = explodePlan(w.spec.plan.map((p) => ({ ...p })), { axis: [1, 0, 0] });
  // Scan beam
  const beamGeom = new THREE.PlaneGeometry(70, 70);
  w.beam = new THREE.Mesh(beamGeom, new THREE.MeshBasicMaterial({ color: 0x67d8cf, transparent: true, opacity: 0.18, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending }));
  w.beam.rotation.y = Math.PI / 2;
  const beamEdge = new THREE.Mesh(new THREE.PlaneGeometry(1.2, 70), new THREE.MeshBasicMaterial({ color: 0xbaf7f0, side: THREE.DoubleSide, transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending, depthWrite: false }));
  w.beam.add(beamEdge);
  w.beam.visible = false;
  scene.add(w.beam);
  // Characters
  w.wren = makeWren({ scale: 0.55 }); w.wren.position.set(70, 0, 30); w.wren.rotation.y = -0.4;
  w.tally = makeTally({ scale: 0.5 }); w.tally.position.set(260, 0, 140); w.tally.rotation.y = -1.2;
  w.pip = new Claymate({ name: "Pip", body: 0xc47a45, skin: 0xe0b48c, accent: 0x0b5d63, hair: 0x5a3a24, goggles: false, scale: 0.42 });
  w.pip.position.set(-120, 0, 90);
  scene.add(w.wren, w.tally, w.pip);
  // Prepare the sign texture now so its material compiles before playback.
  w.tally.holdSign("BUT DOES IT\nWORK?"); w.tally.sign.visible = false; w.tally.action = "idle";
  // Schematic layer: architecture as floating labelled tiles (not physical placement)
  w.schematic = new THREE.Group();
  const nodes = [
    ["Rocket ESP32", 0, 34, 0], ["MPU6050 IMU", -60, 52, 10], ["4 canard servos", 70, 50, -6], ["Ignition servo · interlocked", 110, 24, 12],
    ["UART2 115200 → Launcher ESP32", -120, 18, -8], ["Read-only status board", 40, 70, 18],
  ];
  for (const [name, x, y, z] of nodes) {
    const tile = new THREE.Mesh(new THREE.PlaneGeometry(34, 10), new THREE.MeshBasicMaterial({ color: 0x0b5d63, transparent: true, opacity: 0.55, side: THREE.DoubleSide, depthWrite: false }));
    const border = new THREE.LineSegments(new THREE.EdgesGeometry(tile.geometry), new THREE.LineBasicMaterial({ color: 0x67d8cf }));
    tile.add(border);
    const el = document.createElement("div"); el.className = "css2d-label"; el.textContent = name;
    const lbl = new THREE.CSS2DObject(el); tile.add(lbl);
    tile.position.set(x, y, z);
    tile.userData.base = tile.position.clone();
    w.schematic.add(tile);
  }
  w.schematic.position.set(120, 4, -40);
  w.schematic.visible = false;
  scene.add(w.schematic);
  return w;
}

// ---------------------------------------------------------------------------
// Camera keyframes [t, position, target]
// ---------------------------------------------------------------------------
const KEYS = [
  [0, [-40, 190, 52], [-40, 0, 40]],
  [6.5, [-20, 150, 70], [-30, 0, 40]],
  [11, [-30, 190, 470], [-30, 20, -10]],
  [14, [180, 90, 260], [120, 20, 0]],
  [17, [260, 70, 140], [120, 20, -60]],
  [22, [210, 60, 40], [120, 22, -60]],
  [27, [120, 50, 120], [120, 22, -60]],
  [31, [120, 120, 220], [120, 30, -60]],
  [36, [-30, 140, 230], [120, 30, -60]],
  [42, [240, 90, 160], [120, 40, -60]],
  [50, [230, 62, 130], [140, 30, -20]],
  [56, [230, 62, 130], [140, 30, -20]],
  [62, [260, 140, 220], [100, 20, -40]],
  [68, [140, 240, 420], [40, 0, -40]],
  [80, [40, 760, 620], [0, 0, -60]],
];

function cameraAt(t) {
  let i = 0;
  while (i < KEYS.length - 2 && t > KEYS[i + 1][0]) i++;
  const [t0, p0, q0] = KEYS[i], [t1, p1, q1] = KEYS[i + 1];
  const k = ease((t - t0) / (t1 - t0));
  const lerp = (a, b) => a.map((v, j) => v + (b[j] - v) * k);
  return { pos: lerp(p0, p1), target: lerp(q0, q1) };
}

// ---------------------------------------------------------------------------
// The film as a function of time
// ---------------------------------------------------------------------------
function apply(t, dt) {
  const w = world;
  const frozen = t >= 50 && t < 56;
  // pencil & paper
  const p = seg(t, 0.5, 6.8);
  const tip = w.paper.draw(t < 7.5 ? p : 1);
  const tipWorld = w.paper.toWorld(tip);
  // camera: follow the pencil while it draws, then hand over to the keyframed path
  const cam = cameraAt(t);
  const camPos = new THREE.Vector3(...cam.pos), camTarget = new THREE.Vector3(...cam.target);
  if (t < 8.5) {
    const follow = Math.min(t, 6.8);
    const drawTip = w.paper.toWorld(w.paper.tipAt(seg(follow, 0.5, 6.8)));
    const fPos = drawTip.clone().add(new THREE.Vector3(-26 + follow * 3, 44 + follow * 4, 62 + follow * 6));
    const k = ease(seg(t, 6.4, 8.5));
    camPos.lerpVectors(fPos, camPos, k);
    camTarget.lerpVectors(drawTip, camTarget, k);
  }
  if (POSTER_CAM) { camPos.set(...POSTER_CAM.slice(0, 3)); camTarget.set(...POSTER_CAM.slice(3, 6)); }
  camera.position.copy(camPos);
  camera.lookAt(camTarget);
  w.pencil.visible = t < 9;
  w.pencil.position.copy(tipWorld).add(new THREE.Vector3(0, t < 6.9 ? 0 : 18 * seg(t, 6.9, 8.5), 0));
  // lever
  const pull = seg(t, 14.6, 15.4);
  w.lever.arm.rotation.z = 0.7 - 1.4 * ease(pull);
  // lights
  const dim = ease(seg(t, 15.6, 17.2)) * (1 - ease(seg(t, 66, 72)) * 0.6);
  w.key.intensity = 120000 * (1 - 0.85 * dim);
  w.hemi.intensity = 0.6 * (1 - 0.7 * dim);
  w.rim.intensity = 2.2 * dim;
  w.lamps.forEach((l) => { l.light.intensity = 9000 * (1 - 0.8 * dim); l.light.color.setHex(dim > 0.5 ? 0x9fe8df : 0xffd9a8); l.bulb.material.color.setHex(dim > 0.5 ? 0x9fe8df : 0xffe2b0); });
  // turntable rotation (stops when frozen)
  w.turntable.top.rotation.y = -0.35 + 0.012 * Math.max(0, Math.min(t, 50) - 7) + (t > 56 ? 0.012 * (t - 56) : 0);
  // scan clay -> wireframe and back
  const box = new THREE.Box3().setFromObject(w.holder);
  const xmin = box.min.x - 8, xmax = box.max.x + 8;
  const forward = seg(t, 19, 26.6), back = seg(t, 63.5, 66.8);
  const scanOn = t >= 19 && t < 66.8;
  const scanX = forward < 1 ? xmin + (xmax - xmin) * forward : xmax - (xmax - xmin) * back;
  // Fragments with dot(p - origin, dir) < 0 are discarded: clay vanishes behind the beam
  // on the way out (forward) and returns from the tail on the way back.
  const scanDir = new THREE.Vector3(1, 0, 0);
  for (const m of w.clayMats) {
    const u = m.userData.uniforms;
    u.uScanOn.value = scanOn ? 1 : 0;
    u.uScanOrigin.value.set(scanX, 0, 0);
    u.uScanDir.value.copy(scanDir);
    u.uScanWidth.value = 10;
  }
  const wireOn = t >= 19 && t < 67;
  for (const part of w.spec.parts) part.group.traverse((o) => {
    if (o.userData.role === "edges") { o.visible = wireOn; o.material.color.setHex(0x9fe8df); }
    if (o.userData.role === "hidden") o.visible = wireOn && t > 27;
  });
  w.beam.visible = (forward > 0 && forward < 1) || (back > 0 && back < 1);
  w.beam.position.set(scanX, box.getCenter(new THREE.Vector3()).y, box.getCenter(new THREE.Vector3()).z);
  // dimensions unfold one by one
  w.dims.forEach((d, i) => {
    const k = seg(t, 27.2 + i * 0.8, 27.9 + i * 0.8) * (1 - seg(t, 31.2, 31.6));
    d.visible = k > 0.01;
    d.scale.set(1, 1, 1);
    d.traverse((o) => { if (o.isCSS2DObject) o.element.style.opacity = String(k); });
  });
  // exploded assembly
  const ex = ease(seg(t, 31.5, 35.5)) * (1 - ease(seg(t, 60, 64)));
  const offs = w.plan.offsets(ex, { sequential: true });
  for (const item of w.spec.plan) {
    const target = item.child || w.spec.parts.find((q) => q.id === item.part)?.group;
    const o = offs.get(item.id);
    if (target && o) target.position.set(...o);
  }
  // annotation
  const ann = $("#annotation");
  const annOn = t >= 37 && t < 43.5;
  if (annOn) {
    const txt = "GEOMETRY IS NOT VALIDATION.";
    const n = Math.floor(seg(t, 37.2, 39.4) * txt.length);
    if (ann.dataset.n !== String(n)) { ann.innerHTML = `${txt.slice(0, n)}<span class="rule"></span>`; ann.dataset.n = String(n); }
    ann.classList.toggle("show", t > 39.4);
    ann.style.opacity = String(1 - seg(t, 42.6, 43.5));
  } else if (ann.innerHTML) { ann.innerHTML = ""; ann.dataset.n = ""; }
  // schematic layer
  const schem = seg(t, 42.2, 44) * (1 - seg(t, 49.4, 50.2) * (t < 50 ? 1 : 0));
  w.schematic.visible = t >= 42.2 && t < 50.2;
  w.schematic.children.forEach((tile, i) => {
    tile.position.copy(tile.userData.base).add(new THREE.Vector3(0, Math.sin(t * 1.3 + i) * 2, 0));
    tile.lookAt(camera.position);
    tile.material.opacity = 0.55 * schem;
    tile.traverse((o) => { if (o.isCSS2DObject) o.element.style.opacity = String(schem); });
  });
  // characters
  const wren = w.wren, tally = w.tally, pip = w.pip;
  setAction(wren, t < 13 ? (t > 8 ? "notebook" : "idle") : t < 14.5 ? "point" : t < 16.5 ? "lever" : t < 27 ? "surprised" : t < 31 ? "think" : t < 50 ? "point" : t < 56 ? "surprised" : t < 68 ? "notebook" : "wave", t);
  const leverPos = new THREE.Vector3(150, 0, 60).add(new THREE.Vector3(-18, 0, 4));
  if (t > 12.5 && t < 17) wren.position.lerpVectors(new THREE.Vector3(70, 0, 30), leverPos, ease(seg(t, 12.5, 14.2)));
  else if (t >= 17) wren.position.lerpVectors(leverPos, new THREE.Vector3(150, 0, 80), ease(seg(t, 26, 29)));
  else wren.position.set(70, 0, 30);
  wren.lookAt3(t < 14 ? new THREE.Vector3(-40, 0, 40) : new THREE.Vector3(120, 30, -60));
  // Tally: walks in at the freeze with the sign
  const tallyIn = ease(seg(t, 50.2, 52));
  tally.position.lerpVectors(new THREE.Vector3(300, 0, 90), new THREE.Vector3(146, 0, -4), tallyIn);
  if (t >= 51 && t < 57) { if (tally.signText !== "BUT DOES IT\nWORK?") tally.holdSign("BUT DOES IT\nWORK?"); tally.sign.visible = true; tally.action = "sign"; }
  else { tally.sign.visible = false; setAction(tally, t > 57 ? "notebook" : "idle", t); }
  const faceCam = Math.atan2(camera.position.x - tally.position.x, camera.position.z - tally.position.z);
  tally.rotation.y = -1.1 + (faceCam + 1.1) * tallyIn;
  tally.lookAt3(camera.position);
  // Pip walks along the back of the table carrying nothing in particular
  const pipT = (t * 0.06) % 1;
  pip.position.set(-200 + 380 * (pipT < 0.5 ? pipT * 2 : 2 - pipT * 2), 0, 120);
  pip.rotation.y = pipT < 0.5 ? Math.PI / 2 : -Math.PI / 2;
  setAction(pip, "idle", t);
  for (const mate of [wren, tally, pip]) {
    if (!frozen || mate === tally) { mate.time = t - 1 / 24; mate._frame = -1; mate.update(1 / 24); }
  }
  // walking legs for Pip
  const step = Math.floor(t * 12) % 4;
  pip.legL.rotation.x = [0.4, 0, -0.4, 0][step]; pip.legR.rotation.x = [-0.4, 0, 0.4, 0][step];
  // clay boil only between stop-motion frames
  const frame = Math.floor(t * 12);
  for (const m of w.clayMats) m.userData.uniforms.uStep.value = frozen ? 0 : frame % 997;
  // overlays
  $("#evidence").hidden = !(t >= 52.2 && t < 57.2);
  const title = $("#title");
  const showTitle = t >= 70.5;
  if (title.hidden === showTitle) title.hidden = !showTitle;
  document.body.classList.toggle("no-bars", t >= 70);
  renderer.domElement.style.filter = frozen ? `saturate(${1 - 0.65 * seg(t, 50, 50.6)}) contrast(1.05)` : "";
  updateCaption(t);
  updateTag(t);
}

function setAction(mate, action, t) {
  if (mate.action !== action) { mate.action = action; mate.actionStart = t; }
}

function updateCaption(t) {
  const c = CAPTIONS.find((x) => t >= x.a && t < x.b);
  const el = $("#caption");
  const key = c ? `${c.a}` : "";
  if (el.dataset.key === key) return;
  el.dataset.key = key;
  clear(el, c ? [c.sfx ? h("span", { class: "sfx" }, `[ ${c.sfx} ]`) : null, c.text] : []);
}

function updateTag(t) {
  const el = $("#tag");
  let key, items;
  if (t < 7) { key = "a"; items = [categoryBadge("research", "drawn from the OpenRocket file")]; }
  else if (t < 19) { key = "b"; items = [categoryBadge("research", "rocket from design-file parameters"), categoryBadge("historical", "museum miniature · illustrative"), categoryBadge("conceptual", "clay characters")]; }
  else if (t < 31.5) { key = "c"; items = [categoryBadge("research"), assetBadge("source-model")]; }
  else if (t < 42) { key = "d"; items = [categoryBadge("research"), assetBadge("source-model"), assetBadge("reconstructed")]; }
  else if (t < 50) { key = "e"; items = [categoryBadge("research"), h("span", { class: "asset asset-illustration" }, "schematic · not physical placement")]; }
  else if (t < 70) { key = "f"; items = [categoryBadge("research", "evidence record")]; }
  else { key = "g"; items = []; }
  if (el.dataset.key === key) return;
  el.dataset.key = key;
  clear(el, items);
}

function buildEvidencePanel(ev) {
  const c = ev.counts;
  clear($("#evidence"),
    h("h4", {}, "The evidence record answers"),
    h("div", { class: "cluster" }, h("span", { class: "zero" }, String(c.accepted_physical_measurements)), h("span", { class: "muted" }, "accepted physical measurements")),
    h("ol", {}, ev.claims.map((cl) => h("li", {}, h("b", {}, cl.id), h("span", {}, cl.title), statusChip(cl.status, cl.status_label)))),
    h("p", { class: "muted small" }, `${c.discrepancies_open} of ${c.discrepancies_total} discrepancies open · ${c.predictions_not_measured} of ${c.predictions_total} predictions not measured · bench-validation prototype, not flight-tested.`));
}

// ---------------------------------------------------------------------------
// Playback
// ---------------------------------------------------------------------------
function render() {
  if (!scene) return;
  if (composer) composer.render(); else renderer.render(scene, camera);
  labels.render(scene, camera);
}

function seek(t) {
  state.t = Math.min(Math.max(t, 0), DURATION);
  apply(state.t, 0);
  render();
  syncUI();
  audio.seek(state.t, state.playing && state.sound);
  state.lastSpoken = NARRATION.findIndex((n) => n.at >= state.t) - 1;
}

function play() {
  if (state.t >= DURATION - 0.05) seek(0);
  state.playing = true;
  state.last = performance.now();
  $("#start").hidden = true;
  audio.seek(state.t, state.sound);
  syncUI();
}

function pause() {
  state.playing = false;
  audio.stopAll();
  window.speechSynthesis?.cancel();
  syncUI();
}

function tick(now) {
  requestAnimationFrame(tick);
  if (!state.playing) return;
  const dt = Math.min((now - state.last) / 1000, 0.1);
  state.last = now;
  state.t = Math.min(state.t + dt, DURATION);
  apply(state.t, dt);
  render();
  speak(state.t);
  syncUI();
  if (state.t >= DURATION) { state.playing = false; syncUI(); announce("Film finished"); }
}

function speak(t) {
  if (!state.voice || !state.sound || !window.speechSynthesis) return;
  const idx = NARRATION.findIndex((n, i) => i > state.lastSpoken && t >= n.at);
  if (idx === -1) return;
  state.lastSpoken = idx;
  const u = new SpeechSynthesisUtterance(NARRATION[idx].text);
  u.rate = 0.92; u.pitch = 0.95;
  window.speechSynthesis.speak(u);
}

function syncUI() {
  const scrub = $("#scrub");
  scrub.value = String(state.t);
  scrub.style.setProperty("--fill", `${(state.t / DURATION) * 100}%`);
  const fmt = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  $("#time").textContent = `${fmt(state.t)} / ${fmt(DURATION)}`;
  const toggle = $("#toggle");
  toggle.textContent = state.playing ? "❚❚" : "▶";
  toggle.setAttribute("aria-label", state.playing ? "Pause" : "Play");
  const ch = CHAPTERS.reduce((m, c, i) => (state.t >= c.t ? i : m), 0);
  $$("#chapters button").forEach((b, i) => b.setAttribute("aria-current", String(i === ch)));
}

function wireControls() {
  $("#chapters").append(...CHAPTERS.map((c) => {
    const b = h("button", { type: "button", title: c.name, "aria-label": `Chapter: ${c.name}` });
    b.addEventListener("click", () => { seek(c.t + 0.01); announce(`Chapter: ${c.name}`); });
    return b;
  }));
  syncRange($("#scrub")).addEventListener("input", (e) => seek(Number(e.target.value)));
  $("#toggle").addEventListener("click", () => (state.playing ? pause() : play()));
  $("#play-sound").addEventListener("click", async () => { state.sound = await audio.enable(); press($("#sound"), state.sound); play(); });
  $("#play-silent").addEventListener("click", () => play());
  $("#replay").addEventListener("click", () => { seek(0); play(); });
  $("#watch-again").addEventListener("click", () => { seek(0); play(); });
  $("#skip").addEventListener("click", () => { seek(71); pause(); $("#start").hidden = true; announce("Skipped to the title"); });
  $("#cc").addEventListener("click", () => { state.cc = press($("#cc")); document.body.classList.toggle("no-cc", !state.cc); });
  $("#sound").addEventListener("click", async () => {
    const on = $("#sound").getAttribute("aria-pressed") !== "true";
    if (on) state.sound = await audio.enable(); else { state.sound = false; audio.disable(); window.speechSynthesis?.cancel(); }
    press($("#sound"), state.sound);
    audio.seek(state.t, state.playing && state.sound);
  });
  $("#narration").addEventListener("click", async () => {
    state.voice = press($("#narration"));
    if (state.voice && !state.sound) { state.sound = await audio.enable(); press($("#sound"), state.sound); audio.seek(state.t, state.playing); }
    if (!state.voice) window.speechSynthesis?.cancel();
  });
  window.addEventListener("keydown", (e) => {
    if (e.target.matches("input, textarea")) return;
    if (e.key === " ") { e.preventDefault(); state.playing ? pause() : play(); }
    else if (e.key === "ArrowRight") seek(state.t + 5);
    else if (e.key === "ArrowLeft") seek(state.t - 5);
    else if (e.key.toLowerCase() === "c") $("#cc").click();
  });
}

boot().catch((err) => { console.error(err); $("#start").querySelector(".lede").textContent = `The film could not load: ${err.message}`; });
