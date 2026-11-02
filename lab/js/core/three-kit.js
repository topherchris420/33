// Shared 3D plumbing: renderer, perspective/orthographic camera rig with CAD-style
// orbit controls and standard views, studio lighting, blueprint grid, axis gizmo,
// labels, and stamped screenshots. Scene units are millimetres throughout.
import * as THREE from "../../lib/three-lab.min.js";
import { reducedMotion } from "./dom.js";

export { THREE };

export function createRenderer(container, { alpha = false, antialias = true, preserve = false } = {}) {
  const renderer = new THREE.WebGLRenderer({ antialias, alpha, preserveDrawingBuffer: preserve, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.localClippingEnabled = true;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  // Adaptive quality: software rasterisers (SwiftShader, llvmpipe) get no shadows and 1x pixels.
  try {
    const gl = renderer.getContext();
    const info = gl.getExtension("WEBGL_debug_renderer_info");
    const name = info ? gl.getParameter(info.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
    renderer.userData = { gpu: String(name), software: /swiftshader|llvmpipe|software|basic render/i.test(String(name)) };
  } catch { renderer.userData = { gpu: "unknown", software: false }; }
  if (renderer.userData.software) { renderer.shadowMap.enabled = false; renderer.setPixelRatio(1); }
  container.append(renderer.domElement);
  const labels = new THREE.CSS2DRenderer();
  labels.domElement.style.position = "absolute";
  labels.domElement.style.inset = "0";
  labels.domElement.style.pointerEvents = "none";
  container.append(labels.domElement);
  return { renderer, labels };
}

/** Perspective + orthographic cameras sharing one target, with OrbitControls. */
export class CameraRig {
  constructor(domElement, { fov = 35, near = 0.5, far = 20000 } = {}) {
    this.persp = new THREE.PerspectiveCamera(fov, 1, near, far);
    this.ortho = new THREE.OrthographicCamera(-1, 1, 1, -1, -far, far);
    this.camera = this.persp;
    this.aspect = 1;
    this.controls = new THREE.OrbitControls(this.persp, domElement);
    this.controls.enableDamping = !reducedMotion();
    this.controls.dampingFactor = 0.12;
    this.controls.screenSpacePanning = true;
    this.controls.zoomToCursor = true;
    this.controls.mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };
    this.home = null;
    this.tween = null;
  }

  get isOrtho() { return this.camera === this.ortho; }

  resize(width, height) {
    this.aspect = width / Math.max(height, 1);
    this.persp.aspect = this.aspect;
    this.persp.updateProjectionMatrix();
    this._fitOrtho();
  }

  _fitOrtho() {
    const distance = this.persp.position.distanceTo(this.controls.target);
    const halfH = Math.tan(THREE.MathUtils.degToRad(this.persp.fov / 2)) * distance;
    this.ortho.top = halfH; this.ortho.bottom = -halfH;
    this.ortho.left = -halfH * this.aspect; this.ortho.right = halfH * this.aspect;
    this.ortho.zoom = 1;
    this.ortho.updateProjectionMatrix();
  }

  setProjection(ortho) {
    if (ortho === this.isOrtho) return;
    if (ortho) {
      this.ortho.position.copy(this.persp.position);
      this.ortho.quaternion.copy(this.persp.quaternion);
      this.ortho.up.copy(this.persp.up);
      this._fitOrtho();
      this.camera = this.ortho;
    } else {
      // Map ortho zoom back to a perspective distance that frames the same height.
      const halfH = (this.ortho.top - this.ortho.bottom) / 2 / this.ortho.zoom;
      const dist = halfH / Math.tan(THREE.MathUtils.degToRad(this.persp.fov / 2));
      const dir = new THREE.Vector3().subVectors(this.ortho.position, this.controls.target).normalize();
      this.persp.position.copy(this.controls.target).addScaledVector(dir, dist);
      this.persp.up.copy(this.ortho.up);
      this.camera = this.persp;
    }
    this.controls.object = this.camera;
    this.controls.update();
  }

  /** Frame a bounding box from a direction (world vector from target to camera). */
  frame(box, direction = new THREE.Vector3(1, 0.7, 1.2), { animate = true, up = new THREE.Vector3(0, 1, 0), margin = 1.25 } = {}) {
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const dir = direction.clone().normalize();
    // Fit the box's projected extents (not its bounding sphere) so engineering views fill the frame.
    const right = new THREE.Vector3().crossVectors(up, dir);
    if (right.lengthSq() < 1e-8) right.set(1, 0, 0);
    right.normalize();
    const camUp = new THREE.Vector3().crossVectors(dir, right).normalize();
    let hw = 0, hh = 0, hd = 0;
    for (let i = 0; i < 8; i++) {
      const c = new THREE.Vector3(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z).sub(center);
      hw = Math.max(hw, Math.abs(c.dot(right))); hh = Math.max(hh, Math.abs(c.dot(camUp))); hd = Math.max(hd, Math.abs(c.dot(dir)));
    }
    const tanHalf = Math.tan(THREE.MathUtils.degToRad(this.persp.fov / 2));
    const dist = Math.max(hh / tanHalf, hw / (tanHalf * this.aspect), size.length() * 0.2) * margin + hd;
    const radius = Math.max(size.length() / 2, 1);
    const toPos = center.clone().addScaledVector(dir, dist);
    this.persp.near = Math.max(dist / 500, 0.05);
    this.persp.far = dist * 50;
    this.persp.updateProjectionMatrix();
    this._animateTo(toPos, center, up, animate);
  }

  _animateTo(pos, target, up, animate) {
    const cam = this.camera;
    if (!animate || reducedMotion()) {
      this.tween = null;
      cam.position.copy(pos); this.controls.target.copy(target); cam.up.copy(up);
      this.persp.position.copy(pos); this.persp.up.copy(up);
      if (this.isOrtho) this._syncOrthoFromPersp(pos, target, up);
      this.controls.update();
      return;
    }
    const fromPos = cam.position.clone(), fromTarget = this.controls.target.clone(), fromUp = cam.up.clone();
    const start = performance.now(), duration = 650;
    this.tween = (now) => {
      const t = Math.min((now - start) / duration, 1);
      const e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      cam.position.lerpVectors(fromPos, pos, e);
      this.controls.target.lerpVectors(fromTarget, target, e);
      cam.up.lerpVectors(fromUp, up, e).normalize();
      if (this.isOrtho) { this.persp.position.copy(cam.position); this.persp.up.copy(cam.up); this._fitOrtho(); }
      if (t >= 1) this.tween = null;
    };
  }

  _syncOrthoFromPersp(pos, target, up) {
    this.ortho.position.copy(pos); this.ortho.up.copy(up); this.ortho.lookAt(target); this._fitOrtho();
  }

  update(now = performance.now()) {
    if (this.tween) this.tween(now);
    this.controls.update();
  }
}

/** Standard engineering views. Model frame: +X along the specimen axis, +Y up, +Z toward the viewer. */
export const VIEWS = {
  front: { dir: [0, 0, 1], up: [0, 1, 0], label: "Front" },
  rear: { dir: [0, 0, -1], up: [0, 1, 0], label: "Rear" },
  left: { dir: [-1, 0, 0], up: [0, 1, 0], label: "Left" },
  right: { dir: [1, 0, 0], up: [0, 1, 0], label: "Right" },
  top: { dir: [0, 1, 0], up: [0, 0, -1], label: "Top" },
  bottom: { dir: [0, -1, 0], up: [0, 0, 1], label: "Bottom" },
  iso: { dir: [1, 0.8, 1.15], up: [0, 1, 0], label: "Isometric" },
};

export function studioLights(scene, { intensity = 1 } = {}) {
  const group = new THREE.Group();
  group.name = "studio-lights";
  const hemi = new THREE.HemisphereLight(0xdde9ef, 0x1a1410, 0.55 * intensity);
  const key = new THREE.DirectionalLight(0xfff1dc, 2.1 * intensity);
  key.position.set(1.2, 2.0, 1.4);
  const rim = new THREE.DirectionalLight(0x67d8cf, 0.9 * intensity);
  rim.position.set(-1.6, 0.6, -1.2);
  const fill = new THREE.DirectionalLight(0xc8d8ff, 0.45 * intensity);
  fill.position.set(-0.6, -0.4, 1.6);
  group.add(hemi, key, rim, fill);
  scene.add(group);
  return { group, hemi, key, rim, fill };
}

export function environment(renderer, scene, strength = 0.6) {
  const pmrem = new THREE.PMREMGenerator(renderer);
  const env = pmrem.fromScene(new THREE.RoomEnvironment(), 0.04).texture;
  scene.environment = env;
  scene.environmentIntensity = strength;
  pmrem.dispose();
  return env;
}

/** Blueprint grid on a plane, minor + major lines, sized to a model. */
export function blueprintGrid(size = 1000, minor = 10, { color = 0x67d8cf } = {}) {
  const group = new THREE.Group();
  group.name = "blueprint-grid";
  const divisions = Math.round(size / minor);
  const fine = new THREE.GridHelper(size, divisions, color, color);
  fine.material.transparent = true; fine.material.opacity = 0.07; fine.material.depthWrite = false;
  const major = new THREE.GridHelper(size, Math.max(1, Math.round(divisions / 10)), color, color);
  major.material.transparent = true; major.material.opacity = 0.18; major.material.depthWrite = false;
  group.add(fine, major);
  return group;
}

/** Axis gizmo rendered into a small corner viewport. */
export class AxisGizmo {
  constructor() {
    this.scene = new THREE.Scene();
    this.camera = new THREE.OrthographicCamera(-1.6, 1.6, 1.6, -1.6, 0.1, 10);
    const axes = [[1, 0, 0, 0xe07650, "X"], [0, 1, 0, 0x4cc9bb, "Y"], [0, 0, 1, 0x6aa8ff, "Z"]];
    for (const [x, y, z, c, name] of axes) {
      const dir = new THREE.Vector3(x, y, z);
      const arrow = new THREE.ArrowHelper(dir, new THREE.Vector3(), 1, c, 0.28, 0.14);
      this.scene.add(arrow);
      const sprite = textSprite(name, c);
      sprite.position.copy(dir.multiplyScalar(1.32));
      this.scene.add(sprite);
    }
  }
  render(renderer, mainCamera, x, y, size) {
    this.camera.position.set(0, 0, 4).applyQuaternion(mainCamera.quaternion);
    this.camera.quaternion.copy(mainCamera.quaternion);
    const prevAuto = renderer.autoClear;
    renderer.autoClear = false;
    renderer.clearDepth();
    renderer.setScissorTest(true);
    renderer.setScissor(x, y, size, size);
    renderer.setViewport(x, y, size, size);
    renderer.render(this.scene, this.camera);
    renderer.setScissorTest(false);
    renderer.autoClear = prevAuto;
  }
}

export function textSprite(text, color = 0xffffff, { size = 64, font = "500 40px 'Plex Mono', monospace" } = {}) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d");
  ctx.font = font;
  ctx.fillStyle = `#${new THREE.Color(color).getHexString()}`;
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.fillText(text, size / 2, size / 2 + 2);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false }));
  sprite.scale.setScalar(0.42);
  return sprite;
}

/** DOM label anchored in 3D. */
export function label3D(text, { className = "css2d-label", sub } = {}) {
  const el = document.createElement("div");
  el.className = className;
  el.textContent = text;
  if (sub) { const s = document.createElement("small"); s.textContent = sub; el.append(s); }
  return new THREE.CSS2DObject(el);
}

/** Observe container size and keep renderer/camera in sync. */
export function autoResize(container, renderer, labels, rig, onResize) {
  const apply = () => {
    const w = container.clientWidth, hgt = container.clientHeight;
    if (!w || !hgt) return;
    renderer.setSize(w, hgt, false);
    labels.setSize(w, hgt);
    rig.resize(w, hgt);
    onResize?.(w, hgt);
  };
  new ResizeObserver(apply).observe(container);
  apply();
  return apply;
}

/** Render one frame and return a PNG blob with a provenance stamp burned into the image. */
export async function stampedScreenshot(renderer, renderFn, stampLines) {
  renderFn();
  const src = renderer.domElement;
  const band = Math.round(22 * (stampLines.length + 0.6) * Math.min(window.devicePixelRatio || 1, 2));
  const out = document.createElement("canvas");
  out.width = src.width; out.height = src.height + band;
  const ctx = out.getContext("2d");
  ctx.fillStyle = "#060a10"; ctx.fillRect(0, 0, out.width, out.height);
  ctx.drawImage(src, 0, 0);
  const scale = Math.min(window.devicePixelRatio || 1, 2);
  ctx.fillStyle = "#0b5d63"; ctx.fillRect(0, src.height, out.width, 2 * scale);
  ctx.font = `${12 * scale}px 'Plex Mono', monospace`;
  stampLines.forEach((line, i) => {
    ctx.fillStyle = i === 0 ? "#f1e9d6" : "#8fa2ad";
    ctx.fillText(line, 12 * scale, src.height + (20 + i * 20) * scale);
  });
  return new Promise((resolve) => out.toBlob(resolve, "image/png"));
}

/** A frame loop that pauses when the tab is hidden and can be stopped. */
export function loop(fn) {
  let id = 0, running = true, last = performance.now();
  const tick = (now) => {
    if (!running) return;
    const dt = Math.min((now - last) / 1000, 0.1);
    last = now;
    fn(now, dt);
    id = requestAnimationFrame(tick);
  };
  id = requestAnimationFrame(tick);
  return { stop() { running = false; cancelAnimationFrame(id); } };
}
