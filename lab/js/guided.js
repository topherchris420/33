// Guided Lab: six lessons. Each opens with a short clay scene (illustration), points at the
// real tool, and ends with a challenge whose answer is computed from committed data.
import { mountShell } from "./core/shell.js";
import { h, $, $$, clear, announce, reducedMotion, webglAvailable } from "./core/dom.js";
import { lab, canonical } from "./core/data.js";
import { categoryBadge } from "./core/taxonomy.js";
import { THREE, createRenderer, environment } from "./core/three-kit.js";
import { clayMaterial, applyMode } from "./core/materials.js";
import { makeWren, makeTally } from "./core/claymates.js";
import { closureResidual, diagonal, BASELINE } from "./core/math/fourbar.js";
import { buildRocket } from "./workbench/specimens.js";
import { explodePlan } from "./core/math/explode.js";

mountShell();

const store = {
  get() { try { return JSON.parse(localStorage.getItem("p33-guided") || "{}"); } catch { return {}; } },
  set(v) { try { localStorage.setItem("p33-guided", JSON.stringify(v)); } catch { /* storage unavailable: progress lives for this visit only */ } },
};
let progress = store.get();

function lessons(ev, or, fixture, inputs) {
  const total = (or.current.overall_length_m * 1000).toFixed(1);
  const { ground: a, input: b, coupler: c, output: d } = BASELINE;
  const fmax = diagonal(a, b, 92);
  return [
    {
      id: "dims", n: 1, title: "Where did these dimensions come from?", cat: "research", sign: "WHERE DID THESE\nDIMENSIONS COME FROM?", prop: "rocket",
      caption: "Wren explodes the model; Tally asks for the source.",
      body: [
        "A rendering can look finished while saying nothing about where its numbers came from. In the workbench every dimension is generated from a named field in the OpenRocket design file, and anything the file does not describe is labelled NOT SPECIFIED.",
        "Open the workbench in blueprint mode, explode the assembly, and select a fin set: its root chord, tip chord, span, and leading-edge station each carry their XML path.",
      ],
      tool: { href: "workbench.html?specimen=rocket&mode=blueprint&select=fins2", label: "Open the rocket in blueprint mode" },
      q: "The design file's overall length is the sum of which fields?",
      options: [
        { t: "The nose cone length plus both body tube lengths", ok: true },
        { t: "The body tubes plus the aft fins' root chord" },
        { t: "The body tubes plus the motor length" },
      ],
      explain: `OpenRocket stacks body components in document order, so the nose (38.1 mm) and the two tubes (342.9 + 220.0 mm) give ${total} mm. Fins and the motor sit inside that length; they do not extend it.`,
    },
    {
      id: "closure", n: 2, title: "The mechanism that cannot close", cat: "research", sign: "IT WON'T\nCLOSE.", prop: "links",
      caption: "Wren pushes; the links refuse to meet.",
      body: [
        "Claim C1 asks whether the recorded four-bar linkage can carry the fin from folded to deployed. The committed model says it cannot assemble at any drive angle — and the lab shows that failure instead of animating a success.",
        "In the Mechanism Lab, sweep the drive angle and watch the gap between the coupler circle and the output circle. It never reaches zero.",
      ],
      tool: { href: "mechanism.html", label: "Open the folding-fin investigation" },
      q: `The coupler (${c} mm) and output link (${d} mm) can only join when the distance from B to D is at least…`,
      options: [{ t: `${d} mm` }, { t: `${Math.abs(c - d)} mm`, ok: true }, { t: `${c} mm` }, { t: `${c + d} mm` }],
      explain: `Two circles of radius ${c} and ${d} mm intersect only when the distance between their centres lies between |c − d| = ${Math.abs(c - d)} mm and c + d = ${c + d} mm. Over 0–92° the B–D distance never exceeds ${fmax.toFixed(1)} mm, so the gap is at least ${closureResidual(a, b, c, d, 92).toFixed(1)} mm (D-002).`,
    },
    {
      id: "models", n: 3, title: "Two models, one rocket", cat: "research", sign: "TWO MODELS.\nONE ROCKET.", prop: "rocket-rings",
      caption: "Tally holds up the disagreement; Wren shrugs.",
      body: [
        "Static margin measures how far the centre of pressure sits behind the centre of gravity, in body diameters. The repository holds two formulations that disagree about it — and the record refuses to pick a winner without evidence.",
        "The comparison studio puts both on one axis against the 1.5–2.0 caliber requirement, and marks a station the lab thinks a human should review.",
      ],
      tool: { href: "mechanism.html#comparison", label: "Open the model comparison studio" },
      q: `The reference formulation gives ${inputs.sm_min_calibers.toFixed(2)}–${inputs.sm_max_calibers.toFixed(2)} cal, inside the window. Does that make it the correct model?`,
      options: [{ t: "Yes — it satisfies the requirement" }, { t: "No — satisfying a requirement is not validating the model", ok: true }],
      explain: "Both formulations share questioned inputs: a hard-coded motor that differs from the design file (D-007) and an ogive nose coefficient for an ellipsoid nose (D-008). The two disagree by a factor of two (D-006). Landing inside a window is a result, not a validation.",
    },
    {
      id: "signal", n: 4, title: "From signal to evidence", cat: "synthetic", sign: "WHOSE\nCLOCK?", prop: "scope",
      caption: "A gap on the screen; Tally asks whose clock drew it.",
      body: [
        "A telemetry plot looks like a measurement, but its timestamps may not mean what they seem. The Telemetry Theater replays the repository's intentionally flawed synthetic fixture and shows what the audit catches: a duplicate, an invalid sample, a gap, a clock that ran backwards, and a log dump that never ended.",
      ],
      tool: { href: "telemetry.html", label: "Open the Telemetry Theater" },
      q: "Live T packets carry a time field. Whose clock stamped it?",
      options: [{ t: "The rocket's millis() when the IMU was sampled" }, { t: "The launcher's millis() when it relayed the line", ok: true }, { t: "The dashboard computer's clock" }],
      explain: `The launcher builds T packets as T,<launcher millis()>,… when it relays a rocket DATA line (D-018). Recovered LOG rows carry the rocket's own clock, so the two are never mixed. The fixture's audit lists ${fixture.audit.findings.length} findings.`,
    },
    {
      id: "measured", n: 5, title: "What still must be measured?", cat: "research", sign: "WHAT'S\nMEASURED?", prop: "ledger",
      caption: "The ledger's measurement page is empty — on purpose.",
      body: [
        "The Evidence Observatory draws every claim, requirement, discrepancy, prediction, and artifact as one network. Its centre is the most honest node in the project: accepted physical measurements.",
      ],
      tool: { href: "observatory.html", label: "Open the Evidence Observatory" },
      q: "How many human-accepted physical measurements does the record hold today?",
      options: [ev.counts.accepted_physical_measurements, 3, 8, 25].map((v, i) => ({ t: String(v), ok: i === 0 })).sort((x, y) => Number(x.t) - Number(y.t)),
      explain: `${ev.counts.accepted_physical_measurements}. Only a named human can accept an inert measurement into the record; until then every physical quantity stays NOT MEASURED, and ${ev.counts.predictions_not_measured} of ${ev.counts.predictions_total} predictions wait for one.`,
    },
    {
      id: "trust", n: 6, title: "Reading a display you can trust", cat: "historical", sign: "CAN I TRUST\nTHIS?", prop: "display",
      caption: "A value goes stale on a clay display.",
      body: [
        "Aircraft displays separate raw observations, derived estimates, what is drawn, and what is flagged. The Instrumentation Lab shows those general principles with original, synthetic examples — and compares the dependency lesson with Project 33's own source-pinned status model.",
      ],
      tool: { href: "instruments.html", label: "Open the Instrumentation Lab" },
      q: "A data source stops updating. What should a trustworthy display do with its last value?",
      options: [{ t: "Keep showing it normally until a new value arrives" }, { t: "Mark it stale (or remove it) so it is never read as current", ok: true }, { t: "Replace it with zero" }],
      explain: "Old data shown as current is worse than no data. The same rule runs through Project 33's telemetry audit: invalid samples are counted and excluded, never replaced with zero.",
    },
  ];
}

// ---------------------------------------------------------------------------
// Vignette stage
// ---------------------------------------------------------------------------
let stage;
function makeStage(or, extra) {
  if (!webglAvailable()) return null;
  const el = $("#vignette");
  const { renderer, labels } = createRenderer(el);
  const scene = new THREE.Scene();
  environment(renderer, scene, 0.35);
  scene.add(new THREE.HemisphereLight(0xdde9ef, 0x2a1d12, 0.9));
  const key = new THREE.DirectionalLight(0xfff0d8, 2.6); key.position.set(80, 160, 120); key.castShadow = !renderer.userData.software;
  key.shadow.mapSize.set(1024, 1024); Object.assign(key.shadow.camera, { left: -160, right: 160, top: 160, bottom: -160 });
  scene.add(key);
  const plinth = new THREE.Mesh(new THREE.CylinderGeometry(150, 156, 14, 64), clayMaterial({ color: 0x24313b, scale: 0.02, bump: 0.3 }));
  plinth.position.y = -7; plinth.receiveShadow = true; scene.add(plinth);
  const camera = new THREE.PerspectiveCamera(30, 1, 1, 3000);
  camera.position.set(0, 92, 255); camera.lookAt(0, 34, -10);
  const wren = makeWren({ scale: 0.75 }); wren.position.set(-70, 0, 30); wren.rotation.y = 0.5;
  const tally = makeTally({ scale: 0.7 }); tally.position.set(85, 0, 40); tally.rotation.y = -0.6;
  tally.holdSign("?"); tally.sign.visible = false;
  scene.add(wren, tally);
  const props = new THREE.Group(); scene.add(props);
  // Rocket prop (from the OpenRocket file)
  const spec = buildRocket(or, extra);
  const rocketHolder = new THREE.Group(); rocketHolder.scale.setScalar(0.22); rocketHolder.position.set(0, 26, -20); rocketHolder.add(spec.root);
  spec.unspecified.visible = false;
  const plan = explodePlan(spec.plan.map((p) => ({ ...p })), { axis: [1, 0, 0] });
  const button = new THREE.Group();
  const bbase = new THREE.Mesh(new THREE.CylinderGeometry(12, 13, 6, 24), clayMaterial({ color: 0x2b2f33, scale: 0.3 })); bbase.position.y = 3;
  const bcap = new THREE.Mesh(new THREE.CylinderGeometry(9, 9, 6, 24), clayMaterial({ color: 0xc8463a, scale: 0.3 })); bcap.position.y = 8;
  button.add(bbase, bcap); button.position.set(-40, 0, 70);
  // Links prop
  const links = new THREE.Group();
  const bar = (len, color) => { const m = new THREE.Mesh(new THREE.BoxGeometry(len, 4, 8), clayMaterial({ color, scale: 0.3 })); m.castShadow = true; return m; };
  const s = 2.2;
  const lg = bar(25 * s, 0x9a8f80); lg.position.set(0, 2, 0);
  const li = bar(15 * s, 0xc8603f); li.position.set(-12.5 * s - 4, 6, -8); li.rotation.y = 0.6;
  const lc = bar(60 * s, 0x2f7f80); lc.position.set(-6, 10, -46); lc.rotation.y = -0.05;
  const lo = bar(15 * s, 0x7f9a52); lo.position.set(12.5 * s + 6, 6, -10); lo.rotation.y = -0.7;
  links.add(lg, li, lc, lo);
  // Scope prop
  const scope = new THREE.Group();
  const box = new THREE.Mesh(new THREE.RoundedBoxGeometry(110, 70, 40, 4, 4), clayMaterial({ color: 0x3b4650, scale: 0.08 }));
  box.position.y = 38; box.castShadow = true;
  const screenCanvas = document.createElement("canvas"); screenCanvas.width = 512; screenCanvas.height = 300;
  const sctx = screenCanvas.getContext("2d");
  sctx.fillStyle = "#04140f"; sctx.fillRect(0, 0, 512, 300); sctx.strokeStyle = "#67d8cf"; sctx.lineWidth = 4; sctx.beginPath();
  for (let x = 0; x < 512; x += 4) { const y = 150 + 70 * Math.sin(x / 40) * Math.exp(-x / 900); if (x > 230 && x < 300) { sctx.stroke(); sctx.beginPath(); continue; } x === 0 || x === 300 ? sctx.moveTo(x, y) : sctx.lineTo(x, y); }
  sctx.stroke(); sctx.fillStyle = "#e07650"; sctx.font = "28px monospace"; sctx.fillText("GAP", 240, 60);
  const stex = new THREE.CanvasTexture(screenCanvas); stex.colorSpace = THREE.SRGBColorSpace;
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(92, 54), new THREE.MeshBasicMaterial({ map: stex }));
  screen.position.set(0, 38, 20.5);
  scope.add(box, screen); scope.position.set(0, 0, -20);
  // Ledger prop
  const ledger = new THREE.Group();
  const cover = new THREE.Mesh(new THREE.BoxGeometry(110, 6, 76), clayMaterial({ color: 0x6b3b2a, scale: 0.1 })); cover.position.y = 3;
  const pageCanvas = document.createElement("canvas"); pageCanvas.width = 512; pageCanvas.height = 360;
  const pctx = pageCanvas.getContext("2d"); pctx.fillStyle = "#f1e9d6"; pctx.fillRect(0, 0, 512, 360);
  pctx.fillStyle = "#3b2a17"; pctx.font = "600 34px Georgia"; pctx.fillText("Accepted measurements", 40, 70);
  pctx.font = "160px Georgia"; pctx.fillText("0", 200, 260);
  const ptex = new THREE.CanvasTexture(pageCanvas); ptex.colorSpace = THREE.SRGBColorSpace;
  const pages = new THREE.Mesh(new THREE.PlaneGeometry(104, 70), new THREE.MeshStandardMaterial({ map: ptex, roughness: 0.9 }));
  pages.rotation.x = -Math.PI / 2; pages.position.y = 6.2;
  ledger.add(cover, pages); ledger.position.set(0, 0, -10); ledger.rotation.x = 0;
  // Display prop
  const display = new THREE.Group();
  const frame = new THREE.Mesh(new THREE.RoundedBoxGeometry(100, 66, 12, 4, 3), clayMaterial({ color: 0x222a30, scale: 0.1 })); frame.position.y = 40;
  const dCanvas = document.createElement("canvas"); dCanvas.width = 512; dCanvas.height = 320;
  const dctx = dCanvas.getContext("2d"); dctx.fillStyle = "#061016"; dctx.fillRect(0, 0, 512, 320);
  dctx.fillStyle = "#8fa2ad"; dctx.font = "34px monospace"; dctx.fillText("AIRSPEED (synthetic)", 40, 70);
  dctx.fillStyle = "#e3c27a"; dctx.font = "92px monospace"; dctx.fillText("212", 60, 190);
  dctx.strokeStyle = "#e3c27a"; dctx.setLineDash([12, 8]); dctx.lineWidth = 4; dctx.strokeRect(40, 105, 230, 110);
  dctx.font = "30px monospace"; dctx.fillText("STALE 4.2 s", 290, 180);
  const dtex = new THREE.CanvasTexture(dCanvas); dtex.colorSpace = THREE.SRGBColorSpace;
  const dscreen = new THREE.Mesh(new THREE.PlaneGeometry(88, 55), new THREE.MeshBasicMaterial({ map: dtex })); dscreen.position.set(0, 40, 6.2);
  display.add(frame, dscreen); display.position.set(0, 0, -20);
  const all = { rocket: [rocketHolder, button], "rocket-rings": [rocketHolder], links: [links], scope: [scope], ledger: [ledger], display: [display] };
  const resize = () => { const w = el.clientWidth, hh = el.clientHeight; renderer.setSize(w, hh, false); labels.setSize(w, hh); camera.aspect = w / hh; camera.updateProjectionMatrix(); };
  new ResizeObserver(resize).observe(el); resize();
  let lesson = null, t0 = 0, running = false;
  const st = {
    play(l) {
      lesson = l; t0 = performance.now(); running = true;
      props.clear();
      (all[l.prop] || []).forEach((o) => props.add(o));
      tally.signText = null; tally.holdSign(l.sign); tally.sign.visible = false;
      for (const part of spec.parts) part.group.traverse((o) => { if (o.userData.visuals) applyMode(o, "clay"); });
      spec.root.traverse((o) => { if (o.userData.kind === "dimension") o.visible = false; });
      if (reducedMotion()) { st.render(9); running = false; }
    },
    render(t) {
      const l = lesson;
      if (!l) return;
      const seg = (a, b) => Math.min(Math.max((t - a) / (b - a), 0), 1);
      wren.lookAt3(new THREE.Vector3(0, 30, 0)); tally.lookAt3(camera.position);
      const setA = (m, a) => { if (m.action !== a) { m.action = a; m.actionStart = t; } };
      if (l.prop === "rocket") {
        wren.position.lerpVectors(new THREE.Vector3(-90, 0, 40), new THREE.Vector3(-55, 0, 72), seg(0.2, 1.4));
        setA(wren, t < 1.6 ? "idle" : t < 2.4 ? "push" : t < 6 ? "surprised" : "notebook");
        bcap.position.y = t > 1.6 && t < 2.2 ? 5.5 : 8;
        const ex = seg(2.2, 3.6);
        const offs = plan.offsets(ex, { sequential: true });
        for (const item of spec.plan) { const target = item.child || spec.parts.find((q) => q.id === item.part)?.group; const o = offs.get(item.id); if (target && o) target.position.set(...o); }
        tally.sign.visible = t > 4 && t < 9.5; setA(tally, tally.sign.visible ? "sign" : "idle");
        const bp = t > 6;
        for (const part of spec.parts) part.group.traverse((o) => { if (o.userData.visuals) applyMode(o, bp ? "blueprint" : "clay"); });
        spec.root.traverse((o) => { if (o.userData.kind === "dimension") o.visible = bp && o.userData.tier === "overview"; });
        spec.unspecified.visible = bp;
        spec.unspecified.children.forEach((u) => { u.visible = u.userData.id === "hinge"; });
        rocketHolder.rotation.y = 0.2 * Math.sin(t * 0.4);
      } else {
        spec.unspecified.visible = false;
        if (l.prop === "links") { setA(wren, t > 1 && t < 4 ? "push" : "shrug"); wren.position.set(-80 + (t > 1 && t < 4 ? 6 * Math.sin(t * 4) : 0), 0, 10); lc.position.z = -46 + (t > 1 && t < 4 ? 3 * Math.sin(t * 4.2) : 0); }
        else if (l.prop === "rocket-rings") { setA(wren, "shrug"); }
        else if (l.prop === "ledger") { setA(wren, "think"); }
        else setA(wren, t > 2 ? "point" : "idle");
        tally.sign.visible = t > 1.2; setA(tally, tally.sign.visible ? "sign" : "idle");
        rocketHolder.rotation.y = 0.3 * Math.sin(t * 0.4);
      }
      for (const m of [wren, tally]) { m.time = t - 1 / 24; m._frame = -1; m.update(1 / 24); }
      renderer.render(scene, camera); labels.render(scene, camera);
    },
    tick() { requestAnimationFrame(st.tick); if (!running) return; const t = (performance.now() - t0) / 1000; st.render(t); if (t > 10) running = false; },
  };
  requestAnimationFrame(st.tick);
  return st;
}

// ---------------------------------------------------------------------------
// Lesson UI
// ---------------------------------------------------------------------------
function renderList(all, current) {
  clear($("#lessons"), all.map((l) => {
    const b = h("button", { type: "button", "aria-current": String(l.id === current), "data-id": l.id },
      h("span", { class: "n" }, String(l.n)), h("span", {}, l.title), progress[l.id] ? h("span", { class: "done" }, "✓ DONE") : h("span"));
    b.addEventListener("click", () => openLesson(all, l.id));
    return b;
  }));
  const done = all.filter((l) => progress[l.id]).length;
  $("#progress").textContent = `${done} of ${all.length} challenges answered correctly${done === all.length ? " — the whole lab is yours." : "."}`;
}

function openLesson(all, id) {
  const l = all.find((x) => x.id === id) || all[0];
  renderList(all, l.id);
  history.replaceState(null, "", `#${l.id}`);
  $("#vg-caption").textContent = l.caption;
  const name = `q-${l.id}`;
  const verdict = h("div", { class: "verdict", "aria-live": "polite" });
  const options = l.options.map((o, i) => {
    const input = h("input", { type: "radio", name, value: String(i) });
    const label = h("label", {}, input, h("span", {}, o.t));
    input.addEventListener("change", () => {
      $$(`input[name="${name}"]`).forEach((inp) => inp.closest("label").classList.remove("correct", "wrong"));
      label.classList.add(o.ok ? "correct" : "wrong");
      clear(verdict, h("b", {}, o.ok ? "Right. " : "Not quite. "), l.explain);
      if (o.ok) { progress[l.id] = true; store.set(progress); renderList(all, l.id); }
      announce(o.ok ? "Correct" : "Not quite");
    });
    return label;
  });
  clear($("#lesson"),
    h("div", { class: "cluster" }, categoryBadge(l.cat), h("span", { class: "label" }, `Lesson ${l.n} of ${all.length}`)),
    h("h2", {}, l.title),
    l.body.map((p) => h("p", { class: "lede" }, p)),
    h("p", {}, h("a", { class: "btn primary", href: l.tool.href }, `${l.tool.label} →`)),
    h("div", { class: "challenge" }, h("fieldset", {}, h("legend", {}, `Challenge · ${l.q}`), options), verdict),
    h("div", { class: "cluster", style: { marginTop: "16px" } },
      l.n > 1 ? h("button", { class: "btn ghost", type: "button", onclick: () => openLesson(all, all[l.n - 2].id) }, "← Previous") : null,
      l.n < all.length ? h("button", { class: "btn", type: "button", onclick: () => openLesson(all, all[l.n].id) }, "Next lesson →") : null));
  stage?.play(l);
  window.__guided = { lesson: l.id, progress };
}

async function boot() {
  const [ev, or, fixture, inputs, csv, cross] = await Promise.all([lab.evidence(), lab.openrocket(), lab.telemetryFixture(), canonical.c5Inputs(), canonical.c5Csv(), canonical.c5Crosscheck()]);
  const all = lessons(ev, or, fixture, inputs);
  stage = makeStage(or, { c5: { csv: [], inputs, cross }, observation: or.lab_observations[0] });
  $("#vg-replay").addEventListener("click", () => { const id = location.hash.slice(1) || all[0].id; stage?.play(all.find((x) => x.id === id) || all[0]); });
  openLesson(all, location.hash.slice(1) || all[0].id);
  window.addEventListener("hashchange", () => { const id = location.hash.slice(1); if (id && id !== window.__guided?.lesson) openLesson(all, id); });
}

boot().catch((err) => { console.error(err); $("#lesson").textContent = `Lessons could not load: ${err.message}`; });
