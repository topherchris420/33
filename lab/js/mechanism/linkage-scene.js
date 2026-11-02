// The investigation stage: the C1 baseline linkage as clay bars on a drafting board.
// Dimensions come from the recorded configuration; bar section (5 × 2 mm) and pin-hole
// diameter (2 mm) follow CAD Files/FusionScripts/Project33FourBar/Project33FourBar.py.
// Model plane (x, y) maps to scene (x, height, −y). Units: millimetres.
import { THREE, createRenderer, CameraRig, studioLights, environment, autoResize, label3D, loop } from "../core/three-kit.js";
import { clayMaterial } from "../core/materials.js";
import { makeWren, makeTally } from "../core/claymates.js";
import { reducedMotion } from "../core/dom.js";
import { displayPose } from "./pose.js";

const BAR_W = 5, BAR_T = 2, HOLE_R = 1;
const LAYER = { ground: 1, input: 3, output: 3, coupler: 5 }; // bar centre heights (STEP stacking)
const COLORS = { ground: 0x8d8a82, input: 0xc86b4e, coupler: 0x4f9db8, output: 0x7fae8a };

const toScene = (pt, h = 0) => new THREE.Vector3(pt[0], h, -pt[1]);

function barGeometry(length) {
  const g = new THREE.RoundedBoxGeometry(length + BAR_W, BAR_T, BAR_W, 3, 0.9);
  g.translate(length / 2, 0, 0);
  return g;
}

/** True on software rasterisers (SwiftShader, llvmpipe), which get a lighter scene. */
function softwareRenderer() {
  try {
    const c = document.createElement("canvas");
    const gl = c.getContext("webgl2") || c.getContext("webgl");
    if (!gl) return false;
    const info = gl.getExtension("WEBGL_debug_renderer_info");
    const name = info ? String(gl.getParameter(info.UNMASKED_RENDERER_WEBGL)) : "";
    gl.getExtension("WEBGL_lose_context")?.loseContext();
    return /swiftshader|llvmpipe|software/i.test(name);
  } catch { return false; }
}

export function createLinkageScene(container, { onAttemptDone } = {}) {
  const lowPower = softwareRenderer();
  const { renderer, labels } = createRenderer(container, { alpha: true, antialias: !lowPower });
  renderer.setClearColor(0x000000, 0);
  const scene = new THREE.Scene();
  const lights = studioLights(scene, { intensity: 1.05 });
  lights.key.castShadow = true;
  lights.key.position.set(60, 160, 90);
  Object.assign(lights.key.shadow.camera, { left: -140, right: 140, top: 140, bottom: -140, near: 1, far: 600 });
  lights.key.shadow.mapSize.set(1024, 1024);
  lights.key.shadow.bias = -0.0005;
  if (!lowPower) environment(renderer, scene, 0.45);

  // Drafting board
  const board = new THREE.Mesh(new THREE.PlaneGeometry(420, 420), new THREE.MeshStandardMaterial({ color: 0x0d1b27, roughness: 0.95 }));
  board.rotation.x = -Math.PI / 2;
  board.receiveShadow = true;
  scene.add(board);
  const fine = new THREE.GridHelper(400, 80, 0x67d8cf, 0x67d8cf);
  fine.material.transparent = true; fine.material.opacity = 0.06; fine.position.y = 0.02;
  const major = new THREE.GridHelper(400, 8, 0x67d8cf, 0x67d8cf);
  major.material.transparent = true; major.material.opacity = 0.16; major.position.y = 0.03;
  scene.add(fine, major);

  // Software rasterisers: no MSAA, environment map, or shadows; guides rest when idle.
  if (lowPower) { renderer.shadowMap.enabled = false; renderer.setPixelRatio(1); }

  const rig = new CameraRig(renderer.domElement, { fov: 32 });
  let dirty = true;
  rig.controls.addEventListener("change", () => { dirty = true; });
  const linkage = new THREE.Group();
  scene.add(linkage);

  const holeMat = new THREE.MeshStandardMaterial({ color: 0x0a0806, roughness: 1 });
  const pinMat = new THREE.MeshStandardMaterial({ color: 0xcfd8dc, metalness: 0.85, roughness: 0.3 });
  const holeGeom = new THREE.CylinderGeometry(HOLE_R, HOLE_R, BAR_T + 0.08, 20);

  let cfg = null, theta = 0, bars = {}, mats = {};
  const pins = {}, ghosts = {};
  const pinGeom = new THREE.CylinderGeometry(HOLE_R * 0.95, HOLE_R * 0.95, 1, 16);
  for (const id of ["A", "D", "B"]) {
    pins[id] = new THREE.Mesh(pinGeom, pinMat);
    pins[id].castShadow = true;
    linkage.add(pins[id]);
  }
  // Floating copper rings marking the two pins that should coincide.
  for (const id of ["P", "Q"]) {
    const ring = new THREE.Mesh(new THREE.TorusGeometry(2.1, 0.32, 10, 32), new THREE.MeshBasicMaterial({ color: id === "P" ? 0xe07650 : 0xe0a274 }));
    ring.rotation.x = Math.PI / 2;
    ghosts[id] = ring;
    linkage.add(ring);
  }

  // Circles: coupler circle about B, output circle about D.
  const ringMat = (color, opacity) => new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthWrite: false, side: THREE.DoubleSide });
  const couplerRing = new THREE.Group(), outputRing = new THREE.Group();
  linkage.add(couplerRing, outputRing);

  // Gap dimension
  const gapGroup = new THREE.Group();
  const gapLine = new THREE.Mesh(new THREE.BoxGeometry(1, 0.35, 0.35), new THREE.MeshBasicMaterial({ color: 0xe07650 }));
  const coneGeom = new THREE.ConeGeometry(0.9, 2.4, 14);
  const coneA = new THREE.Mesh(coneGeom, gapLine.material), coneB = new THREE.Mesh(coneGeom, gapLine.material);
  gapGroup.add(gapLine, coneA, coneB);
  linkage.add(gapGroup);

  const lbl = {};
  const addLabel = (key, text, cls = "css2d-label") => { lbl[key] = label3D(text, { className: cls }); linkage.add(lbl[key]); };
  addLabel("A", "A · ground pivot"); addLabel("D", "D · ground pivot"); addLabel("B", "B");
  addLabel("P", "C₁ · coupler pin", "css2d-label warn"); addLabel("Q", "C₂ · output pin", "css2d-label warn");
  addLabel("gap", "ε", "css2d-label warn");
  addLabel("input", "input b", "css2d-label dim"); addLabel("coupler", "coupler c", "css2d-label dim");
  addLabel("output", "output d", "css2d-label dim"); addLabel("ground", "ground a", "css2d-label dim");
  addLabel("cring", "coupler circle (r = c about B)", "css2d-label dim"); addLabel("oring", "output circle (r = d about D)", "css2d-label dim");

  // Clay guides
  const wren = makeWren({ scale: 0.34 });
  const tally = makeTally({ scale: 0.3 });
  tally.visible = false;
  scene.add(wren, tally);

  function makeRing(group, radius, color) {
    group.clear();
    const thin = new THREE.Mesh(new THREE.RingGeometry(radius - 0.32, radius + 0.32, 256), ringMat(color, 0.95));
    const glow = new THREE.Mesh(new THREE.RingGeometry(Math.max(radius - 2.6, 0.1), radius + 2.6, 256), ringMat(color, 0.12));
    for (const m of [thin, glow]) { m.rotation.x = -Math.PI / 2; group.add(m); }
  }

  function setConfig(next) {
    cfg = { ...next };
    for (const bar of Object.values(bars)) { bar.traverse((o) => o.geometry && o.geometry !== holeGeom && o.geometry.dispose()); linkage.remove(bar); }
    bars = {};
    const lengths = { ground: cfg.a, input: cfg.b, coupler: cfg.c, output: cfg.d };
    for (const [id, len] of Object.entries(lengths)) {
      mats[id] = mats[id] || clayMaterial({ color: COLORS[id], bump: 0.55, scale: 0.6, roughness: 0.82 });
      const g = new THREE.Group();
      const body = new THREE.Mesh(barGeometry(len), mats[id]);
      body.castShadow = true; body.receiveShadow = true;
      g.add(body);
      for (const x of [0, len]) { const hole = new THREE.Mesh(holeGeom, holeMat); hole.position.x = x; g.add(hole); }
      g.userData.body = body;
      g.position.y = LAYER[id];
      bars[id] = g;
      linkage.add(g);
    }
    makeRing(couplerRing, cfg.c, 0x67d8cf);
    makeRing(outputRing, cfg.d, 0xe0a274);
    lbl.input.element.textContent = `input b = ${cfg.b} mm`;
    lbl.coupler.element.textContent = `coupler c = ${cfg.c} mm`;
    lbl.output.element.textContent = `output d = ${cfg.d} mm`;
    lbl.ground.element.textContent = `ground a = ${cfg.a} mm`;
    update();
  }

  function orient(group, from, to) {
    const dx = to[0] - from[0], dy = to[1] - from[1];
    group.position.x = from[0]; group.position.z = -from[1];
    group.rotation.y = Math.atan2(dy, dx);
  }

  let strain = 0; // 0..1, used during the assembly attempt
  let last = null;
  function update() {
    if (!cfg) return;
    dirty = true;
    const p = displayPose(cfg, theta);
    last = p;
    orient(bars.ground, p.A, p.D);
    orient(bars.input, p.A, p.B);
    orient(bars.coupler, p.B, p.P);
    orient(bars.output, p.D, p.Q);
    // Strain: the coupler squashes and the output stretches toward each other, then relaxes.
    const g = p.gap;
    const cs = 1 - (strain * 0.6 * g) / cfg.c, os = 1 + (strain * 0.12 * g) / cfg.d;
    bars.coupler.userData.body.scale.set(1, 1 + strain * 0.25, 1 + strain * 0.3);
    bars.coupler.scale.x = p.closed ? 1 : cs;
    bars.output.scale.x = p.closed ? 1 : os;
    for (const id of ["coupler", "output"]) mats[id].emissive?.setHex(strain > 0.02 ? 0x3a1608 : 0x000000).multiplyScalar(1);
    if (mats.coupler.emissive) mats.coupler.emissiveIntensity = strain * 1.6;
    if (mats.output.emissive) mats.output.emissiveIntensity = strain * 1.6;
    pins.A.position.copy(toScene(p.A, 2.6)); pins.A.scale.y = 5.2;
    pins.D.position.copy(toScene(p.D, 2.6)); pins.D.scale.y = 5.2;
    pins.B.position.copy(toScene(p.B, 4.2)); pins.B.scale.y = 4.4;
    couplerRing.position.copy(toScene(p.B, 6.3));
    outputRing.position.copy(toScene(p.D, 6.35));
    // effective free-end positions after strain
    const P = p.closed ? p.P : [p.B[0] + (p.P[0] - p.B[0]) * cs, p.B[1] + (p.P[1] - p.B[1]) * cs];
    const Q = p.closed ? p.Q : [p.D[0] + (p.Q[0] - p.D[0]) * os, p.D[1] + (p.Q[1] - p.D[1]) * os];
    ghosts.P.position.copy(toScene(P, 7.4)); ghosts.Q.position.copy(toScene(Q, 7.4));
    ghosts.P.visible = ghosts.Q.visible = !p.closed;
    gapGroup.visible = !p.closed && p.gap > 0.05;
    if (gapGroup.visible) {
      const a3 = toScene(Q, 8.6), b3 = toScene(P, 8.6);
      const dir = new THREE.Vector3().subVectors(b3, a3);
      const len = dir.length();
      const mid = a3.clone().addScaledVector(dir, 0.5);
      gapLine.position.copy(mid);
      gapLine.scale.x = Math.max(len - 4.8, 0.1);
      gapLine.rotation.set(0, Math.atan2(-dir.z, dir.x), 0);
      const n = dir.clone().normalize();
      const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), n);
      coneB.position.copy(b3).addScaledVector(n, -1.2); coneB.quaternion.copy(q);
      coneA.position.copy(a3).addScaledVector(n, 1.2); coneA.quaternion.copy(q.clone().multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI)));
      lbl.gap.position.copy(mid).add(new THREE.Vector3(0, 3, 0));
      lbl.gap.element.textContent = `ε = ${Math.hypot(P[0] - Q[0], P[1] - Q[1]).toFixed(2)} mm`;
    }
    lbl.gap.visible = gapGroup.visible && labelsOn;
    lbl.A.position.copy(toScene(p.A, 6)).add(new THREE.Vector3(-4, 0, 6));
    lbl.D.position.copy(toScene(p.D, 6)).add(new THREE.Vector3(5, 0, 6));
    lbl.B.position.copy(toScene(p.B, 8));
    lbl.P.position.copy(toScene(P, 10)); lbl.Q.position.copy(toScene(Q, 10));
    lbl.P.visible = lbl.Q.visible = !p.closed && labelsOn;
    const mid2 = (u, v, h) => toScene([(u[0] + v[0]) / 2, (u[1] + v[1]) / 2], h);
    lbl.input.position.copy(mid2(p.A, p.B, 6));
    lbl.coupler.position.copy(mid2(p.B, P, 9));
    lbl.output.position.copy(mid2(p.D, Q, 6)).add(new THREE.Vector3(0, 0, 5));
    lbl.ground.position.copy(mid2(p.A, p.D, 3)).add(new THREE.Vector3(0, 0, 7));
    lbl.cring.position.copy(toScene([p.B[0] + cfg.c * 0.5, p.B[1] - cfg.c * 0.866], 7));
    lbl.oring.position.copy(toScene([p.D[0], p.D[1] - cfg.d - 3], 7));
    for (const k of ["A", "D", "B"]) lbl[k].visible = labelsOn;
    // In the perspective close-up only the pins and the gap stay labelled.
    for (const k of ["input", "coupler", "output", "ground", "cring", "oring"]) lbl[k].visible = labelsOn && framedTop;
    // Wren stands just past the coupler pin, facing back along it.
    const u = p.u || [1, 0];
    const stand = [P[0] + u[0] * 9, P[1] + u[1] * 9];
    wren.position.copy(toScene(stand, 0));
    wren.rotation.y = Math.atan2(-u[0], u[1]);
    tally.position.copy(toScene([p.A[0] - 12, p.A[1] - 22], 0));
    tally.rotation.y = 0.5;
  }

  let labelsOn = true;
  function setLabels(on) { labelsOn = on; update(); }
  function setTheta(t) { theta = t; update(); }

  function bounds() {
    const p = displayPose(cfg, theta);
    const box = new THREE.Box3();
    box.expandByPoint(toScene([p.B[0] - cfg.c, p.B[1] - cfg.c], 0));
    box.expandByPoint(toScene([p.B[0] + cfg.c, p.B[1] + cfg.c], 10));
    box.expandByPoint(toScene([p.D[0] + cfg.d + 4, p.D[1] - cfg.d], 0));
    box.expandByPoint(toScene([p.A[0] - 6, p.A[1]], 0));
    return box;
  }

  let framedTop = true;
  function viewTop() {
    // Fit the whole coupler circle in an orthographic plan view.
    framedTop = true;
    if (rig.isOrtho) rig.setProjection(false);
    rig.tween = null;
    const box = bounds();
    const c = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3());
    const halfH = Math.max(size.z / 2, size.x / 2 / Math.max(rig.aspect, 0.1)) * 1.08;
    const dist = halfH / Math.tan(THREE.MathUtils.degToRad(rig.persp.fov / 2));
    rig.persp.position.set(c.x, c.y + dist, c.z + 0.001);
    rig.persp.up.set(0, 0, -1);
    rig.controls.target.copy(c);
    rig.persp.near = Math.max(dist / 500, 0.05); rig.persp.far = dist * 50; rig.persp.updateProjectionMatrix();
    rig.controls.update();
    rig.setProjection(true);
    update();
  }
  function view34(animate = true) {
    framedTop = false;
    rig.setProjection(false);
    const p = displayPose(cfg, theta);
    const box = new THREE.Box3();
    const u = p.u || [1, 0];
    for (const pt of [p.D, p.B, p.P, p.Q, [p.P[0] + u[0] * 9, p.P[1] + u[1] * 9]]) box.expandByPoint(toScene(pt, 0));
    box.expandByPoint(toScene(p.P, 20));
    box.min.addScalar(-6); box.max.addScalar(6);
    const dir = new THREE.Vector3(u[0] * 0.55 + 0.45, 0.85, -u[1] * 0.55 + 0.95);
    rig.frame(box, dir, { animate: animate && !reducedMotion(), margin: 0.8 });
    update();
  }

  // Attempt-assembly choreography
  let attempt = null;
  let guidesUntil = 0;
  function startAttempt() {
    if (!cfg) return Promise.resolve();
    guidesUntil = performance.now() + 1e9;
    tally.visible = false; tally.dropSign();
    view34(true);
    wren.play("push");
    const quick = reducedMotion();
    return new Promise((resolve) => {
      attempt = { start: performance.now(), duration: quick ? 0 : 3.4, resolve };
    });
  }
  function finishAttempt() {
    const a = attempt;
    attempt = null;
    strain = 0;
    update();
    wren.play("shrug");
    const p = last;
    tally.visible = true;
    tally.holdSign(p.closed ? "IT CLOSES" : `STILL ${p.gap.toFixed(1)} mm\nSHORT`);
    tally.lookAt3(toScene(p.P, 6));
    wren.lookAt3(toScene(p.Q, 4));
    guidesUntil = performance.now() + 3500;
    a.resolve();
    onAttemptDone?.(p);
  }

  const resize = autoResize(container, renderer, labels, rig, () => { dirty = true; if (cfg && framedTop && rig.isOrtho) viewTop(); });

  const ticker = loop((now, dt) => {
    if (attempt) {
      // wall-clock timing so slow devices finish on time instead of in slow motion
      const k = attempt.duration ? (now - attempt.start) / 1000 / attempt.duration : 1;
      if (k >= 1) finishAttempt();
      else {
        // two shoves, each straining toward closure and springing back with a clay wobble
        const phase = (k * 2) % 1;
        const push = Math.sin(Math.min(phase / 0.55, 1) * Math.PI / 2);
        const back = phase > 0.55 ? Math.exp(-(phase - 0.55) * 9) * Math.cos((phase - 0.55) * 30) : 1;
        strain = Math.max(0, phase < 0.55 ? push : back);
        update();
      }
    }
    rig.update(now);
    // Guides animate on twos; on software renderers they rest when nothing is happening.
    const animateGuides = !lowPower || attempt || now < guidesUntil;
    if (animateGuides) {
      const f0 = wren._frame, f1 = tally._frame;
      wren.update(dt);
      if (tally.visible) tally.update(dt);
      if (wren._frame !== f0 || (tally.visible && tally._frame !== f1)) dirty = true;
    }
    if (rig.tween) dirty = true;
    if (!dirty) return;
    dirty = false;
    renderer.render(scene, rig.camera);
    labels.render(scene, rig.camera);
  });

  return {
    setConfig, setTheta, setLabels, viewTop, view34, attempt: startAttempt, resize,
    get pose() { return last; },
    resetGuides() { tally.visible = false; tally.dropSign(); wren.play("idle"); wren.lookAt3(new THREE.Vector3(0, 40, 200)); guidesUntil = performance.now() + 1500; dirty = true; },
    invalidate() { dirty = true; },
    lowPower,
    dispose() { ticker.stop(); renderer.dispose(); },
  };
}
