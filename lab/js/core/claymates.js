// The laboratory's two clay guides, built procedurally so they stay light and original.
// WREN — the engineer (teal overalls, copper hair, goggles).
// TALLY — the research assistant (round spectacles, notebook, a habit of asking for sources).
// They animate "on twos" (12 poses per second) with per-frame surface boil, like stop motion.
import { THREE } from "./three-kit.js";
import { clayMaterial } from "./materials.js";

const FPS = 12;

function mat(color, boil = 0.25, bump = 1.0) {
  return clayMaterial({ color, boil, bump, scale: 0.35 });
}

function mesh(geometry, material) {
  const m = new THREE.Mesh(geometry, material);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

/** A soft bean body made by lathing a profile. */
function beanGeometry(radius, height) {
  const pts = [];
  for (let i = 0; i <= 16; i++) {
    const t = i / 16;
    const y = t * height;
    const r = radius * (0.72 + 0.34 * Math.sin(Math.PI * Math.min(t * 1.05, 1))) * (t > 0.92 ? Math.sqrt(Math.max(0, (1 - t) / 0.08)) : 1);
    pts.push(new THREE.Vector2(Math.max(r, 0.001), y));
  }
  return new THREE.LatheGeometry(pts, 28);
}

function limb(length, radius, material) {
  const pivot = new THREE.Group();
  const capsule = mesh(new THREE.CapsuleGeometry(radius, length, 6, 14), material);
  capsule.position.y = -length / 2;
  pivot.add(capsule);
  const end = new THREE.Group();
  end.position.y = -length;
  pivot.add(end);
  pivot.userData.end = end;
  return pivot;
}

function signTexture(text, { width = 512, height = 300, bg = "#f1e9d6", ink = "#1d1a14" } = {}) {
  const canvas = document.createElement("canvas");
  canvas.width = width; canvas.height = height;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = bg; ctx.fillRect(0, 0, width, height);
  // hand-cut cardboard edge
  ctx.strokeStyle = "rgba(60,40,20,0.35)"; ctx.lineWidth = 10; ctx.strokeRect(8, 8, width - 16, height - 16);
  ctx.fillStyle = ink;
  const lines = String(text).split("\n");
  let size = 78;
  ctx.font = `700 ${size}px Fraunces, Georgia, serif`;
  while (lines.some((l) => ctx.measureText(l).width > width - 60) && size > 26) {
    size -= 4; ctx.font = `700 ${size}px Fraunces, Georgia, serif`;
  }
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  const lh = size * 1.12, y0 = height / 2 - ((lines.length - 1) * lh) / 2;
  lines.forEach((l, i) => {
    ctx.save();
    ctx.translate(width / 2, y0 + i * lh);
    ctx.rotate((i % 2 ? 1 : -1) * 0.012);
    ctx.fillText(l, 0, 0);
    ctx.restore();
  });
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

export class Claymate extends THREE.Group {
  constructor({ name = "Wren", body = 0x0b5d63, skin = 0xd9a882, accent = 0xc47a45, hair = 0xb3612f, glasses = false, goggles = true, scale = 1 } = {}) {
    super();
    this.name = name;
    this.time = 0;
    this.action = "idle";
    this.actionStart = 0;
    this.target = new THREE.Vector3(0, 40, 100);
    this.signText = null;
    this.materials = [];
    const m = (c, boil, bump) => { const x = mat(c, boil, bump); this.materials.push(x); return x; };
    const skinM = m(skin, 0.22), bodyM = m(body, 0.3), accentM = m(accent, 0.25), dark = m(0x1d1a17, 0.12), white = m(0xf6f1e6, 0.08);

    const root = new THREE.Group(); this.add(root); this.root = root;
    root.scale.setScalar(scale);
    // legs
    this.legL = limb(10, 3.2, dark); this.legL.position.set(-4.2, 12, 0);
    this.legR = limb(10, 3.2, dark); this.legR.position.set(4.2, 12, 0);
    for (const leg of [this.legL, this.legR]) {
      const shoe = mesh(new THREE.SphereGeometry(4, 16, 12), accentM);
      shoe.scale.set(1, 0.6, 1.5); shoe.position.set(0, 0.5, 1.6);
      leg.userData.end.add(shoe);
      root.add(leg);
    }
    // body
    this.torso = new THREE.Group(); this.torso.position.y = 11; root.add(this.torso);
    const bean = mesh(beanGeometry(10, 26), bodyM); this.torso.add(bean);
    const pocket = mesh(new THREE.BoxGeometry(7, 5, 1.6), accentM); pocket.position.set(0, 12, 9.4); pocket.rotation.x = -0.12; this.torso.add(pocket);
    const pencil = mesh(new THREE.CylinderGeometry(0.5, 0.5, 6, 8), m(0xe3c27a, 0.05)); pencil.position.set(2, 15.5, 9.2); pencil.rotation.z = 0.25; this.torso.add(pencil);
    // arms
    this.shoulderL = new THREE.Group(); this.shoulderL.position.set(-9.5, 21, 0); this.torso.add(this.shoulderL);
    this.shoulderR = new THREE.Group(); this.shoulderR.position.set(9.5, 21, 0); this.torso.add(this.shoulderR);
    this.armL = limb(9, 2.5, bodyM); this.shoulderL.add(this.armL);
    this.armR = limb(9, 2.5, bodyM); this.shoulderR.add(this.armR);
    this.foreL = limb(8, 2.2, skinM); this.armL.userData.end.add(this.foreL);
    this.foreR = limb(8, 2.2, skinM); this.armR.userData.end.add(this.foreR);
    for (const fore of [this.foreL, this.foreR]) {
      const hand = mesh(new THREE.SphereGeometry(3, 14, 10), skinM);
      hand.scale.set(1, 1.1, 0.8);
      fore.userData.end.add(hand);
      fore.userData.hand = hand;
    }
    // head
    this.neck = new THREE.Group(); this.neck.position.y = 25; this.torso.add(this.neck);
    this.head = new THREE.Group(); this.head.position.y = 11; this.neck.add(this.head);
    const skull = mesh(new THREE.SphereGeometry(12, 30, 22), skinM); skull.scale.set(1, 0.94, 0.96); this.head.add(skull);
    const nose = mesh(new THREE.SphereGeometry(2.6, 14, 10), skinM); nose.position.set(0, -1, 11.6); nose.scale.set(1, 0.9, 1.1); this.head.add(nose);
    // eyes
    this.eyes = [];
    for (const side of [-1, 1]) {
      const eye = new THREE.Group(); eye.position.set(side * 4.4, 3, 10.4);
      const ball = mesh(new THREE.SphereGeometry(2.9, 18, 14), white);
      const pupil = mesh(new THREE.SphereGeometry(1.35, 12, 10), dark); pupil.position.z = 2.2;
      const lid = mesh(new THREE.SphereGeometry(3.05, 18, 10, 0, Math.PI * 2, 0, Math.PI / 2), skinM);
      lid.rotation.x = -1.35;
      eye.add(ball, pupil, lid);
      eye.userData = { pupil, lid };
      this.head.add(eye);
      this.eyes.push(eye);
      const brow = mesh(new THREE.CapsuleGeometry(0.7, 3.6, 4, 8), m(hair, 0.15)); brow.rotation.z = Math.PI / 2; brow.position.set(side * 4.4, 7.4, 10.6);
      this.head.add(brow);
      eye.userData.brow = brow;
    }
    this.mouth = mesh(new THREE.TorusGeometry(2.6, 0.55, 8, 20, Math.PI), m(0x6e2f22, 0.05));
    this.mouth.position.set(0, -5.6, 10.6); this.mouth.rotation.set(0.15, 0, Math.PI);
    this.head.add(this.mouth);
    // hair tuft
    for (let i = 0; i < 5; i++) {
      const tuft = mesh(new THREE.ConeGeometry(2.2, 7, 10), m(hair, 0.35));
      tuft.position.set(-4 + i * 2, 11.5, -1 + (i % 2) * 2); tuft.rotation.set(-0.3 + (i % 2) * 0.5, 0, -0.5 + i * 0.25);
      this.head.add(tuft);
    }
    if (goggles) {
      const band = mesh(new THREE.TorusGeometry(12.2, 1.1, 8, 40), dark); band.rotation.x = Math.PI / 2 - 0.35; band.position.y = 6.5; this.head.add(band);
      for (const side of [-1, 1]) {
        const lens = mesh(new THREE.CylinderGeometry(3.3, 3.3, 2.4, 20), m(0x67d8cf, 0.05, 0.2)); lens.rotation.x = Math.PI / 2 - 0.35; lens.position.set(side * 4.6, 10.4, 9.0);
        this.head.add(lens);
      }
    }
    if (glasses) {
      for (const side of [-1, 1]) {
        const rim = mesh(new THREE.TorusGeometry(3.7, 0.55, 8, 24), dark); rim.position.set(side * 4.4, 3, 12.6);
        this.head.add(rim);
      }
      const bridge = mesh(new THREE.CapsuleGeometry(0.45, 1.6, 4, 8), dark); bridge.rotation.z = Math.PI / 2; bridge.position.set(0, 3.4, 13); this.head.add(bridge);
    }
    // sign (hidden until held)
    // The sign is mounted on the body (not the forearm) so it always faces forward and stays legible;
    // the raised right hand meets the stick in the "sign" pose.
    this.sign = new THREE.Group();
    const stick = mesh(new THREE.CylinderGeometry(0.8, 0.8, 30, 8), m(0x9a6b3f, 0.05)); stick.position.y = -6;
    this.signBoard = new THREE.Mesh(new THREE.BoxGeometry(34, 20, 1.2), [m(0xb58a5c, 0.05), m(0xb58a5c, 0.05), m(0xb58a5c, 0.05), m(0xb58a5c, 0.05), new THREE.MeshStandardMaterial({ roughness: 0.9 }), m(0xb58a5c, 0.05)]);
    this.signBoard.position.y = 18; this.signBoard.castShadow = true;
    this.sign.add(stick, this.signBoard);
    this.sign.visible = false;
    this.root.add(this.sign);
    this.sign.position.set(16, 52, 6);
    this.blinkAt = 1 + Math.random() * 3;
  }

  holdSign(text) {
    this.signText = text;
    const face = this.signBoard.material[4];
    face.map?.dispose();
    face.map = signTexture(text);
    face.needsUpdate = true;
    this.sign.visible = true;
    this.play("sign");
  }

  dropSign() { this.sign.visible = false; if (this.action === "sign") this.play("idle"); }

  play(action) { this.action = action; this.actionStart = this.time; }

  lookAt3(target) { this.target.copy(target); }

  /** Advance the puppet. dt in seconds. Poses change only on stop-motion frames. */
  update(dt) {
    this.time += dt;
    const frame = Math.floor(this.time * FPS);
    if (frame === this._frame) return;
    this._frame = frame;
    const t = frame / FPS;
    const a = t - this.actionStart;
    for (const mtl of this.materials) mtl.userData.uniforms.uStep.value = frame % 997;
    // defaults
    const breathe = Math.sin(t * 2.1) * 0.035;
    this.torso.scale.set(1 + breathe * 0.4, 1 - breathe * 0.2, 1 + breathe * 0.4);
    this.torso.rotation.set(0, 0, Math.sin(t * 1.3) * 0.03);
    this.root.position.y = 0;
    let lA = [0.15, 0, 0.18], rA = [0.15, 0, -0.18], lF = [-0.35, 0, 0], rF = [-0.35, 0, 0];
    let headTilt = Math.sin(t * 0.9) * 0.06, mouthOpen = 1, browLift = 0;
    switch (this.action) {
      case "wave": {
        rA = [0, 0, -2.5]; rF = [0, 0, -0.4 + Math.sin(a * 9) * 0.55]; mouthOpen = 1.3; browLift = 0.6; break;
      }
      case "point": {
        rA = [-1.45, 0.3, -0.25]; rF = [-0.12, 0, 0]; browLift = 0.3; break;
      }
      case "push": {
        const s = Math.sin(a * 4.2);
        lA = [-1.35 - 0.12 * s, 0, 0.12]; rA = [-1.35 - 0.12 * s, 0, -0.12]; lF = [-0.2, 0, 0]; rF = [-0.2, 0, 0];
        this.torso.rotation.x = 0.22 + 0.06 * s; this.root.position.z = 2 * s; mouthOpen = 0.4; browLift = -0.6; break;
      }
      case "sign": {
        rA = [-0.35, 0, -2.45]; rF = [0, 0, 0.35]; lA = [-0.6, 0, 0.4]; lF = [-1.4, 0, 0]; mouthOpen = 0.6; browLift = 0.8; headTilt = 0.18; break;
      }
      case "lever": {
        const k = Math.min(a / 0.9, 1);
        rA = [-2.4 + 1.6 * k, 0, -0.15]; rF = [-0.3, 0, 0]; lA = [-2.4 + 1.6 * k, 0, 0.15]; lF = [-0.3, 0, 0];
        this.torso.rotation.x = 0.25 * k; this.root.position.y = -1.5 * k; mouthOpen = 0.4 + k; break;
      }
      case "surprised": {
        lA = [0, 0, 1.1]; rA = [0, 0, -1.1]; lF = [-0.6, 0, 0]; rF = [-0.6, 0, 0]; mouthOpen = 2.2; browLift = 1.4;
        this.root.position.y = a < 0.25 ? 3 : 0; break;
      }
      case "shrug": {
        lA = [0.2, 0, 0.9]; rA = [0.2, 0, -0.9]; lF = [-1.6, 0.4, 0]; rF = [-1.6, -0.4, 0]; this.torso.position.y = 11 + 1.2; headTilt = 0.25; mouthOpen = 0.5; browLift = 0.9; break;
      }
      case "think": {
        rA = [-1.2, 0, -0.4]; rF = [-2.2, 0, 0]; headTilt = -0.2; mouthOpen = 0.3; browLift = 0.5; break;
      }
      case "notebook": {
        lA = [-1.0, 0, 0.3]; lF = [-1.3, 0.3, 0]; rA = [-0.9, 0, -0.3]; rF = [-1.5, -0.3, 0]; headTilt = 0.3; this.neck.rotation.x = 0.35; mouthOpen = 0.4; break;
      }
      default: break;
    }
    if (this.action !== "shrug") this.torso.position.y = 11;
    if (this.action !== "notebook") this.neck.rotation.x = 0;
    this.armL.rotation.set(...lA); this.armR.rotation.set(...rA);
    this.foreL.rotation.set(...lF); this.foreR.rotation.set(...rF);
    // head looks toward target (in world space)
    const headWorld = this.head.getWorldPosition(new THREE.Vector3());
    const local = this.worldToLocal(this.target.clone());
    const from = this.worldToLocal(headWorld.clone());
    const d = local.sub(from);
    this.head.rotation.set(THREE.MathUtils.clamp(-Math.atan2(d.y, Math.hypot(d.x, d.z)) * 0.6, -0.5, 0.5),
      THREE.MathUtils.clamp(Math.atan2(d.x, d.z) * 0.7, -0.9, 0.9), headTilt);
    // eyes: pupils follow, blink occasionally
    const blinking = t > this.blinkAt && t < this.blinkAt + 0.17;
    if (t > this.blinkAt + 0.17) this.blinkAt = t + 2 + Math.random() * 3.5;
    for (const eye of this.eyes) {
      eye.userData.lid.rotation.x = blinking ? -0.15 : -1.35;
      eye.userData.brow.position.y = 7.4 + browLift;
    }
    this.mouth.scale.set(1, Math.max(0.3, mouthOpen), 1);
  }

  dispose() {
    this.traverse((o) => { if (o.geometry) o.geometry.dispose(); });
    for (const m of this.materials) m.dispose();
  }
}

export function makeWren(opts = {}) {
  return new Claymate({ name: "Wren", body: 0x0f6a70, skin: 0xd6a37d, accent: 0xc47a45, hair: 0xa6542a, goggles: true, ...opts });
}

export function makeTally(opts = {}) {
  return new Claymate({ name: "Tally", body: 0x3a4652, skin: 0xb98563, accent: 0xe3c27a, hair: 0x2a1d16, goggles: false, glasses: true, ...opts });
}

export { signTexture };
