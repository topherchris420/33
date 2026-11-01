// A miniature museum diorama of a generic single-seat cockpit, modelled in clay. It is a
// conceptual educational environment — not an F-117A display format, not a simulator — and
// its three displays draw original generic symbology from symbology.js.
import { THREE, createRenderer, CameraRig, studioLights, label3D, autoResize, loop } from "../core/three-kit.js";
import { clayMaterial } from "../core/materials.js";
import { makeTally, signTexture } from "../core/claymates.js";
import { reducedMotion } from "../core/dom.js";
import { flightState, drawHUD, drawMap, drawStatus } from "./symbology.js";

function clay(color, opts = {}) { return clayMaterial({ color, bump: 0.8, scale: 0.08, ...opts }); }

function screenTexture(size = 512) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  return { canvas, ctx: canvas.getContext("2d"), tex };
}

export function mountCockpit({ viewport, store, onSelect }) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x070c12);
  const { renderer, labels } = createRenderer(viewport);
  renderer.shadowMap.enabled = false; // a soft contact shadow is drawn instead (cheaper, calmer)
  const rig = new CameraRig(renderer.domElement, { fov: 30 });
  rig.controls.maxPolarAngle = Math.PI * 0.49;
  const lights = studioLights(scene, { intensity: 0.85 });
  const spot = new THREE.SpotLight(0xfff0d8, 5.2e4, 0, 0.5, 0.6, 1.6);
  spot.position.set(-90, 420, 260);
  spot.target.position.set(0, 40, 0);
  scene.add(spot, spot.target);
  lights.key.intensity = 1.4;
  const cabin = new THREE.PointLight(0xffd9a8, 2600, 0, 1.4); cabin.position.set(0, 150, 10); scene.add(cabin);
  let onScreen = false;
  new IntersectionObserver((entries) => { onScreen = entries.some((e) => e.isIntersecting); }).observe(viewport);

  // Museum plinth and placard
  const plinth = new THREE.Mesh(new THREE.BoxGeometry(420, 30, 300), clay(0x1d252c, { bump: 0.35 }));
  plinth.position.y = -15; plinth.receiveShadow = true; scene.add(plinth);
  const top = new THREE.Mesh(new THREE.BoxGeometry(400, 2, 280), new THREE.MeshStandardMaterial({ color: 0x2a221b, roughness: 0.75 }));
  top.position.y = 1; top.receiveShadow = true; scene.add(top);
  const placardTex = signTexture("CONCEPTUAL COCKPIT\nnot an F-117A display format", { width: 768, height: 220, bg: "#c8a46a", ink: "#21180e" });
  const placard = new THREE.Mesh(new THREE.PlaneGeometry(150, 43), new THREE.MeshStandardMaterial({ map: placardTex, roughness: 0.4, metalness: 0.5 }));
  placard.position.set(0, -14, 151); scene.add(placard);

  const shadowCanvas = document.createElement("canvas");
  shadowCanvas.width = shadowCanvas.height = 128;
  const sctx = shadowCanvas.getContext("2d");
  const grad = sctx.createRadialGradient(64, 64, 4, 64, 64, 64);
  grad.addColorStop(0, "rgba(0,0,0,0.75)"); grad.addColorStop(1, "rgba(0,0,0,0)");
  sctx.fillStyle = grad; sctx.fillRect(0, 0, 128, 128);
  const contact = new THREE.Mesh(new THREE.PlaneGeometry(300, 360), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(shadowCanvas), transparent: true, depthWrite: false }));
  contact.rotation.x = -Math.PI / 2; contact.position.set(0, 2.2, -20);
  const tallyShadow = contact.clone(); tallyShadow.scale.set(0.18, 0.15, 1); tallyShadow.position.set(146, 2.3, -52);
  scene.add(contact, tallyShadow);
  const cockpit = new THREE.Group();
  scene.add(cockpit);
  const hull = clay(0x5d6b78, { bump: 0.35, scale: 0.035 }), dark = clay(0x2a3238, { bump: 0.35, scale: 0.05 }), seatM = clay(0x8a4a30, { bump: 0.5, scale: 0.06 }), trim = clay(0xc47a45, { bump: 0.4 });
  // Tub: a U-section extruded fore-aft (+z is aft, toward the viewer's home position).
  const u = new THREE.Shape();
  u.moveTo(-70, 0); u.lineTo(70, 0); u.lineTo(76, 68); u.lineTo(62, 68); u.lineTo(58, 12); u.lineTo(-58, 12); u.lineTo(-62, 68); u.lineTo(-76, 68); u.closePath();
  const tubGeo = new THREE.ExtrudeGeometry(u, { depth: 210, bevelEnabled: true, bevelThickness: 3, bevelSize: 3, bevelSegments: 3 });
  tubGeo.translate(0, 0, -120);
  const tub = new THREE.Mesh(tubGeo, hull); tub.castShadow = true; tub.receiveShadow = true; cockpit.add(tub);
  // Forward bulkhead and nose fairing
  const nose = new THREE.Mesh(new THREE.CylinderGeometry(50, 74, 70, 6, 1, false), hull);
  nose.rotation.x = Math.PI / 2; nose.position.set(0, 40, -155); nose.castShadow = true; cockpit.add(nose);
  // Side consoles
  for (const side of [-1, 1]) {
    const con = new THREE.Mesh(new THREE.RoundedBoxGeometry(22, 30, 120, 3, 3), dark);
    con.position.set(side * 46, 27, 10); con.castShadow = true; cockpit.add(con);
    for (let k = 0; k < 5; k++) {
      const knob = new THREE.Mesh(new THREE.CylinderGeometry(2.4, 2.4, 3, 12), trim);
      knob.position.set(side * 46 + (k % 2 ? 4 : -4), 43.5, -30 + k * 22); cockpit.add(knob);
    }
  }
  // Seat
  const seat = new THREE.Group();
  const pan = new THREE.Mesh(new THREE.RoundedBoxGeometry(56, 14, 52, 3, 5), seatM); pan.position.set(0, 22, 40);
  const back = new THREE.Mesh(new THREE.RoundedBoxGeometry(56, 86, 14, 3, 5), seatM); back.position.set(0, 64, 72); back.rotation.x = -0.18;
  const head = new THREE.Mesh(new THREE.RoundedBoxGeometry(40, 26, 16, 3, 5), dark); head.position.set(0, 112, 82); head.rotation.x = -0.18;
  for (const m of [pan, back, head]) { m.castShadow = true; seat.add(m); }
  cockpit.add(seat);
  // Centre stick and throttle
  const stick = new THREE.Mesh(new THREE.CylinderGeometry(2.4, 3, 38, 12), dark); stick.position.set(0, 34, 2); stick.rotation.x = -0.2; cockpit.add(stick);
  const grip = new THREE.Mesh(new THREE.CapsuleGeometry(5, 10, 6, 12), dark); grip.position.set(0, 55, -2); cockpit.add(grip);
  const thr = new THREE.Mesh(new THREE.RoundedBoxGeometry(8, 16, 12, 2, 3), trim); thr.position.set(-46, 50, -6); cockpit.add(thr);
  // Instrument panel (sloped) with two multipurpose displays
  const panel = new THREE.Group(); panel.position.set(0, 58, -88); panel.rotation.x = -0.32; cockpit.add(panel);
  const face = new THREE.Mesh(new THREE.RoundedBoxGeometry(128, 56, 8, 3, 3), dark); face.castShadow = true; panel.add(face);
  const displays = {};
  const mkDisplay = (id, x, label) => {
    const s = screenTexture(512);
    const bezel = new THREE.Mesh(new THREE.RoundedBoxGeometry(50, 50, 4, 2, 2), clay(0x15191d, { bump: 0.25 }));
    bezel.position.set(x, 0, 5); panel.add(bezel);
    const screen = new THREE.Mesh(new THREE.PlaneGeometry(42, 42), new THREE.MeshBasicMaterial({ map: s.tex, toneMapped: false }));
    screen.position.set(x, 0, 7.2); screen.userData.display = id; panel.add(screen);
    for (let k = 0; k < 5; k++) for (const side of [-1, 1]) {
      const btn = new THREE.Mesh(new THREE.BoxGeometry(4, 3, 2), clay(0x8c949a, { bump: 0.2 }));
      btn.position.set(x + side * 23.2, -16 + k * 8, 7.6); panel.add(btn);
    }
    const tag = label3D(label, { className: "css2d-label ck-tag" });
    tag.position.set(x, -31, 8); panel.add(tag);
    displays[id] = { ...s, mesh: screen, tag };
  };
  mkDisplay("map", -31, "Navigation display");
  mkDisplay("status", 31, "Status & advisory display");
  // Glare shield and HUD combiner
  // Glare shield: a low hood over the panel that keeps reflections off the screens.
  const shield = new THREE.Mesh(new THREE.RoundedBoxGeometry(136, 9, 34, 3, 4), dark);
  shield.position.set(0, 91, -98); shield.rotation.x = 0.12; cockpit.add(shield);
  const hud = screenTexture(512);
  const hudFrame = new THREE.Mesh(new THREE.TorusGeometry(26, 1.3, 8, 4, Math.PI * 2), clay(0x15191d, { bump: 0.2 }));
  hudFrame.rotation.z = Math.PI / 4; hudFrame.scale.set(1.15, 1.15, 1);
  const hudGroup = new THREE.Group(); hudGroup.position.set(0, 118, -90); hudGroup.rotation.x = 0.22;
  const glass = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.MeshBasicMaterial({ map: hud.tex, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false }));
  glass.userData.display = "hud";
  const tint = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.MeshBasicMaterial({ color: 0x67d8cf, transparent: true, opacity: 0.06, depthWrite: false }));
  tint.position.z = -0.2;
  hudGroup.add(tint, glass, hudFrame);
  cockpit.add(hudGroup);
  const hudTag = label3D("Head-up combiner", { className: "css2d-label ck-tag" }); hudTag.position.set(0, 26, 0); hudGroup.add(hudTag);
  displays.hud = { ...hud, mesh: glass, tag: hudTag };
  // Canopy bows
  for (const z of [-110, -40]) {
    const bow = new THREE.Mesh(new THREE.TorusGeometry(74, 2.6, 8, 32, Math.PI), clay(0x2f383f, { bump: 0.3 }));
    bow.position.set(0, 66, z); cockpit.add(bow);
  }
  cockpit.rotation.y = 0;

  // The guide stands on the plinth, at diorama scale.
  const tally = makeTally({ scale: 0.95 });
  tally.position.set(146, 2, -52); tally.rotation.y = 0.75;
  scene.add(tally);

  // Camera presets
  const home = { box: new THREE.Box3(new THREE.Vector3(-200, -10, -175), new THREE.Vector3(200, 150, 140)), dir: new THREE.Vector3(0.42, 1.08, 0.86), margin: 0.62 };
  // Camera distances chosen so the eye sits roughly where a seated viewer's would.
  const focus = {
    map: { up: 0.42, margin: 1.28 },
    status: { up: 0.42, margin: 1.28 },
    hud: { fixed: new THREE.Vector3(0, -0.1, 1), margin: 0.92 },
  };
  autoResize(viewport, renderer, labels, rig);
  rig.frame(home.box, home.dir, { animate: false, margin: home.margin });

  let selected = null;
  function select(id) {
    selected = id;
    if (!id) { rig.frame(home.box, home.dir, { margin: home.margin }); tally.play("idle"); tally.update(0.1); onSelect?.(null); return; }
    const mesh = displays[id].mesh;
    mesh.updateWorldMatrix(true, false);
    const box = new THREE.Box3().setFromObject(mesh);
    const normal = new THREE.Vector3(0, 0, 1).applyQuaternion(mesh.getWorldQuaternion(new THREE.Quaternion()));
    const dir = focus[id].fixed ? focus[id].fixed.clone().normalize() : normal.clone().add(new THREE.Vector3(0, focus[id].up, 0)).normalize();
    rig.frame(box, dir, { margin: focus[id].margin });
    tally.lookAt3(box.getCenter(new THREE.Vector3()));
    tally.play("point");
    tally.update(0.1);
    onSelect?.(id);
  }

  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
  let down = null;
  renderer.domElement.addEventListener("pointerdown", (e) => { down = [e.clientX, e.clientY]; });
  renderer.domElement.addEventListener("pointerup", (e) => {
    if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 5) return;
    const r = renderer.domElement.getBoundingClientRect();
    ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, rig.camera);
    const hit = ray.intersectObjects([displays.map.mesh, displays.status.mesh, displays.hud.mesh], false)[0];
    if (hit) select(hit.object.userData.display);
  });
  for (const [id, d] of Object.entries(displays)) {
    d.tag.element.style.pointerEvents = "auto"; d.tag.element.style.cursor = "pointer";
    d.tag.element.addEventListener("click", () => select(id));
  }

  // Display redraw at 10 Hz, scene at ≤30 fps while visible.
  let t = 0, lastDraw = -1, lastFrame = 0;
  const motion = !reducedMotion();
  function drawDisplays() {
    const s = flightState(t);
    const st = store.get();
    const flags = {
      attitudeLost: st.sources.inertial.state === "unavailable",
      speed: st.sources.airdata.state, altitude: st.sources.airdata.state,
    };
    drawHUD(displays.hud.ctx, 512, 512, s, st.declutter, { flags });
    drawMap(displays.map.ctx, 512, 512, s, st.declutter, { navFlag: st.sources.gnss.state });
    drawStatus(displays.status.ctx, 512, 512, st.messages, st.declutter);
    for (const d of Object.values(displays)) d.tex.needsUpdate = true;
  }
  // Render on demand: camera moves, display redraws, or a new stop-motion pose.
  let dirty = true;
  rig.controls.addEventListener("change", () => { dirty = true; });
  drawDisplays();
  store.subscribe(() => { drawDisplays(); dirty = true; });
  tally.lookAt3(new THREE.Vector3(0, 60, 400));
  tally.update(0.1);
  // Compile shaders off the main thread where the browser supports it, then render.
  let compiled = false;
  viewport.dataset.compiled = "false";
  Promise.resolve(renderer.compileAsync ? renderer.compileAsync(scene, rig.camera) : null).catch(() => {}).finally(() => { compiled = true; dirty = true; viewport.dataset.compiled = "true"; });
  loop((now) => {
    if (!compiled || !onScreen || document.hidden) { lastFrame = now; return; }
    if (now - lastFrame < 40) return;
    const step = Math.min((now - lastFrame) / 1000, 0.1);
    lastFrame = now;
    if (motion) {
      t += step;
      if (t - lastDraw > 0.2 || lastDraw < 0) { drawDisplays(); lastDraw = t; dirty = true; }
      const before = tally._frame;
      tally.update(step);
      if (tally._frame !== before) dirty = true;
    }
    const moving = !!rig.tween;
    rig.update(now);
    if (moving || rig.tween) dirty = true;
    if (!dirty) return;
    dirty = false;
    renderer.render(scene, rig.camera);
    labels.render(scene, rig.camera);
  });
  return { select, displays, get selected() { return selected; } };
}
