// The home page's hero rocket. Built from the OpenRocket design file's own parameters
// (lab/data/openrocket.json) through the same geometry and materials as the workbench, and
// drawn on a transparent canvas so the hero's spotlight shows through. It turns slowly unless
// reduced motion is requested; drag sideways to turn it, or pause it. Nothing is invented here:
// the folding mechanism and joints, which the file does not describe, are not drawn.
import { THREE, studioLights, environment } from "../core/three-kit.js";
import { partVisuals, clayMaterial, applyMode } from "../core/materials.js";
import { rocketParts, buildPartGeometry, latheFeatureLines } from "../core/rocket-geometry.js";
import { lab } from "../core/data.js";

// Same palette as the workbench specimen (lab/js/workbench/specimens.js).
const CLAY = { nosecone: 0xd9b08c, bodytube: 0x2f7f80, trapezoidfinset: 0xc8794a, motor: 0x8a8f96 };
const SOLID = { nosecone: 0xe4ddcf, bodytube: 0x8ea3ae, trapezoidfinset: 0xc4cfd5, motor: 0x5d636b };
const AUTO_SPEED = 0.3; // rad/s turntable
const LEAN = -0.38; // rad: nose toward the upper right
const PITCH = 0.14; // rad: top tipped slightly toward the viewer

function buildRocket(or) {
  const model = or.current;
  const length = model.overall_length_m * 1000;
  const rocket = new THREE.Group();
  rocket.position.x = -length / 2;
  const visuals = [];
  for (const part of rocketParts(or)) {
    const clay = clayMaterial({ color: CLAY[part.kind] ?? 0xc9a27e, scale: 0.05, bump: 0.8 });
    const lathe = part.kind === "nosecone" || part.kind === "bodytube" || part.kind === "motor";
    for (const { geometry } of buildPartGeometry(THREE, part)) {
      const edgePositions = lathe ? new Float32Array(latheFeatureLines(part)) : null;
      const v = partVisuals(geometry, {
        color: SOLID[part.kind] ?? 0x9fb3bf, clay, edgePositions,
        edgeThreshold: part.kind === "trapezoidfinset" ? 30 : 20,
      });
      rocket.add(v);
      visuals.push(v);
    }
  }
  // Station axis (+X from the nose tip) -> screen down, so the nose points up; then spin
  // about that axis; then lean.
  const axis = new THREE.Group();
  axis.rotation.z = -Math.PI / 2;
  axis.add(rocket);
  const spin = new THREE.Group();
  spin.add(axis);
  const lean = new THREE.Group();
  lean.add(spin);
  return { model, length, visuals, spin, lean };
}

export async function mountHeroRocket(stage, { card, motionQuery, finePointer }) {
  const or = await lab.openrocket();
  const host = stage.querySelector("#stage-canvas");
  const controls = stage.querySelector("#stage-controls");
  const pause = stage.querySelector("#stage-pause");
  const readout = stage.querySelector("#stage-readout");

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.setClearColor(0x000000, 0);
  try {
    const gl = renderer.getContext();
    const info = gl.getExtension("WEBGL_debug_renderer_info");
    const name = String(info ? gl.getParameter(info.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER));
    if (/swiftshader|llvmpipe|software|basic render/i.test(name)) renderer.setPixelRatio(1);
  } catch { /* keep defaults */ }

  const scene = new THREE.Scene();
  studioLights(scene, { intensity: 1.1 });
  environment(renderer, scene, 0.6);
  const { model, length, visuals, spin, lean } = buildRocket(or);
  scene.add(lean);
  const camera = new THREE.PerspectiveCamera(26, 1, 10, 20000);

  const canvas = renderer.domElement;
  canvas.setAttribute("role", "img");
  canvas.setAttribute("aria-label", `${model.rocket_name}: a 3D model generated from the OpenRocket design file ${model.source.path}. Drag sideways to turn it.`);
  host.append(canvas);

  // ---- State ----
  let mode = "solid";
  let angle = 0.9;
  let velocity = 0;
  let paused = motionQuery.matches;
  let dragging = false;
  let lastX = 0, lastMove = 0;
  let visible = true;
  let frame = 0;
  let last = performance.now();
  const tilt = { x: 0, y: 0 }, target = { x: 0, y: 0 };

  // ---- Framing: fit the leaning rocket into the band between the caption and the controls ----
  // The box is the envelope over a full turn, so the fins never clip while it spins.
  const box = new THREE.Box3();
  const turn = new THREE.Box3();
  const size = new THREE.Vector3();
  const center = new THREE.Vector3();
  const hud = stage.querySelector("#stage-hud");
  lean.rotation.set(PITCH, 0, LEAN);
  box.makeEmpty();
  for (let k = 0; k < 12; k++) {
    spin.rotation.y = (k / 12) * Math.PI * 2;
    lean.updateMatrixWorld(true);
    box.union(turn.setFromObject(lean));
  }
  box.getSize(size);
  box.getCenter(center);

  function fit() {
    const width = host.clientWidth, height = host.clientHeight;
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    const rect = host.getBoundingClientRect();
    const top = hud ? Math.max(0, hud.getBoundingClientRect().bottom - rect.top) + 10 : 56;
    const bottom = controls.hidden ? 64 : Math.max(0, rect.bottom - controls.getBoundingClientRect().top) + 10;
    const usable = Math.max(height * 0.45, height - top - bottom);
    const vfov = THREE.MathUtils.degToRad(camera.fov);
    const hfov = 2 * Math.atan(Math.tan(vfov / 2) * camera.aspect);
    const byHeight = (size.y / 2) / Math.tan(vfov / 2) * (height / usable);
    const byWidth = (size.x / 2) / Math.tan(hfov / 2) * (width / Math.max(width - 32, 1));
    const distance = Math.max(byHeight, byWidth) * 1.06 + size.z / 2;
    // Shift the view so the model sits in the middle of the free band, not the canvas.
    const worldPerPixel = (2 * (distance - size.z / 2) * Math.tan(vfov / 2)) / height;
    const lift = ((top - bottom) / 2) * worldPerPixel;
    camera.position.set(center.x, center.y + lift, center.z + distance);
    camera.lookAt(center.x, center.y + lift, center.z);
    camera.near = Math.max(1, distance / 50);
    camera.far = distance * 4;
    camera.updateProjectionMatrix();
    request();
  }

  function render() {
    spin.rotation.y = angle;
    lean.rotation.set(PITCH + tilt.y * 0.12, 0, LEAN + tilt.x * 0.1);
    renderer.render(scene, camera);
  }

  function tick(now) {
    frame = 0;
    const dt = Math.min((now - last) / 1000, 0.05);
    last = now;
    let busy = dragging;
    if (!dragging) {
      const goal = paused ? 0 : AUTO_SPEED;
      velocity += (goal - velocity) * Math.min(1, dt * 2.2);
      if (Math.abs(velocity) > 1e-3) { angle += velocity * dt; busy = true; } else velocity = 0;
    }
    const ease = Math.min(1, dt * 4);
    tilt.x += (target.x - tilt.x) * ease;
    tilt.y += (target.y - tilt.y) * ease;
    if (Math.abs(target.x - tilt.x) + Math.abs(target.y - tilt.y) > 1e-3) busy = true;
    render();
    if (busy) request();
  }

  function request() {
    if (!frame && visible && !document.hidden) {
      last = performance.now();
      frame = requestAnimationFrame(tick);
    }
  }

  // ---- Interaction ----
  canvas.addEventListener("pointerdown", (event) => {
    dragging = true;
    lastX = event.clientX;
    lastMove = performance.now();
    velocity = 0;
    canvas.setPointerCapture?.(event.pointerId);
    request();
  });
  canvas.addEventListener("pointermove", (event) => {
    if (!dragging) return;
    const now = performance.now();
    const delta = (event.clientX - lastX) * 0.011;
    angle += delta;
    velocity = Math.max(-6, Math.min(6, delta / Math.max((now - lastMove) / 1000, 0.008)));
    lastX = event.clientX;
    lastMove = now;
    request();
  });
  const release = () => {
    if (!dragging) return;
    dragging = false;
    if (performance.now() - lastMove > 80) velocity = 0;
    request();
  };
  canvas.addEventListener("pointerup", release);
  canvas.addEventListener("pointercancel", release);
  canvas.addEventListener("lostpointercapture", release);

  if (card && finePointer.matches && !motionQuery.matches) {
    card.addEventListener("pointermove", (event) => {
      if (event.pointerType !== "mouse") return;
      const rect = card.getBoundingClientRect();
      target.x = ((event.clientX - rect.left) / rect.width - 0.5) * 2;
      target.y = ((event.clientY - rect.top) / rect.height - 0.5) * 2;
      request();
    });
    card.addEventListener("pointerleave", () => { target.x = 0; target.y = 0; request(); });
  }

  const setPaused = (next) => {
    paused = next;
    pause.setAttribute("aria-pressed", String(paused));
    pause.setAttribute("aria-label", paused ? "Resume rotation" : "Pause rotation");
    request();
  };
  pause.addEventListener("click", () => setPaused(!paused));
  motionQuery.addEventListener?.("change", () => { if (motionQuery.matches) setPaused(true); });

  const setMode = (next) => {
    mode = next;
    for (const v of visuals) applyMode(v, mode);
    controls.querySelectorAll("[data-mode]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.mode === mode)));
    stage.dataset.mode = mode;
    request();
  };
  controls.addEventListener("click", (event) => {
    const button = event.target.closest("[data-mode]");
    if (button) setMode(button.dataset.mode);
  });

  new IntersectionObserver((entries) => {
    visible = entries[0].isIntersecting;
    if (visible) request();
  }).observe(stage);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) request(); });
  new ResizeObserver(fit).observe(host);
  canvas.addEventListener("webglcontextlost", (event) => {
    event.preventDefault();
    stage.dataset.state = "fallback";
  });

  // ---- First frame (after the caption and controls are laid out, so fit() sees them) ----
  readout.textContent = `${Math.round(length)} mm long · Ø ${(model.reference_diameter_m * 1000).toFixed(1)} mm reference diameter`;
  readout.hidden = false;
  controls.hidden = false;
  setMode(mode);
  setPaused(paused);
  fit();
  render();
  stage.dataset.state = "ready";
  return { setMode, setPaused, get mode() { return mode; } };
}
