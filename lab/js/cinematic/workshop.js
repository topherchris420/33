// The miniature workshop: a hangar, a drafting table, blueprint paper that draws itself from
// the rocket's OpenRocket elevation, a pencil, a lever, a turntable, and a historical
// miniature with a museum placard. Scene units: 1 unit ≈ 1 cm of the miniature set.
import { THREE } from "../core/three-kit.js";
import { clayMaterial } from "../core/materials.js";
import { elevationPaths } from "../core/rocket-geometry.js";

export function buildHangar(scene) {
  const g = new THREE.Group();
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(4000, 4000), clayMaterial({ color: 0x3a3f45, scale: 0.004, bump: 0.25 }));
  floor.rotation.x = -Math.PI / 2; floor.position.y = -120; floor.receiveShadow = true;
  const wall = new THREE.Mesh(new THREE.BoxGeometry(2400, 900, 20), clayMaterial({ color: 0x2a3036, scale: 0.006, bump: 0.3 }));
  wall.position.set(0, 300, -700); wall.receiveShadow = true;
  g.add(floor, wall);
  for (let i = -6; i <= 6; i++) {
    const rib = new THREE.Mesh(new THREE.BoxGeometry(22, 900, 30), clayMaterial({ color: 0x1f252b, scale: 0.03 }));
    rib.position.set(i * 180, 300, -680); g.add(rib);
  }
  const door = new THREE.Mesh(new THREE.PlaneGeometry(900, 420), new THREE.MeshBasicMaterial({ color: 0x0f2a33 }));
  door.position.set(0, 140, -688);
  g.add(door);
  scene.add(g);
  return g;
}

export function buildTable(scene) {
  const g = new THREE.Group();
  const wood = clayMaterial({ color: 0x7a5233, scale: 0.012, bump: 0.35 });
  const top = new THREE.Mesh(new THREE.RoundedBoxGeometry(520, 12, 300, 4, 3), wood);
  top.position.y = -6; top.receiveShadow = true; top.castShadow = true;
  g.add(top);
  for (const [x, z] of [[-240, -130], [240, -130], [-240, 130], [240, 130]]) {
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(7, 6, 110, 14), wood);
    leg.position.set(x, -66, z); leg.castShadow = true; g.add(leg);
  }
  scene.add(g);
  return g;
}

/** Blueprint paper whose drawing is the rocket's side elevation from the OpenRocket file. */
export function buildPaper(scene, or) {
  const W = 2048, H = 1024;
  const canvas = document.createElement("canvas");
  canvas.width = W; canvas.height = H;
  const ctx = canvas.getContext("2d");
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  const { paths, length } = elevationPaths(or);
  const scale = (W * 0.72) / length;
  const ox = W * 0.12, oy = H * 0.5;
  const segs = [];
  let total = 0;
  for (const p of paths) {
    const pts = p.closed ? [...p.points, p.points[0]] : p.points;
    for (let i = 0; i + 1 < pts.length; i++) {
      const a = [ox + pts[i][0] * scale, oy - pts[i][1] * scale], b = [ox + pts[i + 1][0] * scale, oy - pts[i + 1][1] * scale];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      segs.push({ a, b, len, start: total, fin: !!p.fin, thin: !!p.thin });
      total += len;
    }
  }
  function background() {
    ctx.fillStyle = "#0e3a52"; ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = "rgba(200,235,255,0.10)"; ctx.lineWidth = 1;
    for (let x = 0; x < W; x += 32) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (let y = 0; y < H; y += 32) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
    ctx.strokeStyle = "rgba(200,235,255,0.22)";
    for (let x = 0; x < W; x += 160) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (let y = 0; y < H; y += 160) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
    ctx.strokeStyle = "rgba(230,245,255,0.7)"; ctx.lineWidth = 3; ctx.strokeRect(24, 24, W - 48, H - 48);
    ctx.fillStyle = "rgba(230,245,255,0.85)";
    ctx.font = "500 30px 'Plex Mono', monospace";
    ctx.fillText("PROJECT 33 · FOLDING STABILIZED ROCKET · SIDE ELEVATION", 60, H - 92);
    ctx.font = "22px 'Plex Mono', monospace";
    ctx.fillStyle = "rgba(230,245,255,0.6)";
    ctx.fillText(`SOURCE: ${or.current.source.path} · ${length.toFixed(1)} MM OVERALL · DRAWN FROM DESIGN-FILE PARAMETERS`, 60, H - 56);
  }
  function tipAt(progress) {
    const limit = progress * total;
    let tip = segs[0]?.a || [ox, oy];
    for (const s of segs) {
      if (s.start > limit) break;
      const k = Math.min((limit - s.start) / s.len, 1);
      tip = [s.a[0] + (s.b[0] - s.a[0]) * k, s.a[1] + (s.b[1] - s.a[1]) * k];
    }
    return tip;
  }
  function draw(progress) {
    background();
    const limit = progress * total;
    ctx.lineCap = "round"; ctx.lineJoin = "round";
    let tip = segs[0]?.a || [ox, oy];
    for (const s of segs) {
      if (s.start > limit) break;
      const k = Math.min((limit - s.start) / s.len, 1);
      const b = [s.a[0] + (s.b[0] - s.a[0]) * k, s.a[1] + (s.b[1] - s.a[1]) * k];
      ctx.strokeStyle = s.fin ? "rgba(255,214,170,0.95)" : "rgba(240,250,255,0.95)";
      ctx.lineWidth = s.thin ? 2 : 4;
      ctx.beginPath(); ctx.moveTo(s.a[0], s.a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
      tip = b;
    }
    if (progress >= 1) {
      ctx.setLineDash([26, 8, 4, 8]); ctx.strokeStyle = "rgba(255,190,140,0.75)"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(ox - 30, oy); ctx.lineTo(ox + length * scale + 30, oy); ctx.stroke(); ctx.setLineDash([]);
    }
    tex.needsUpdate = true;
    return tip;
  }
  const paperW = 240, paperH = 120;
  const paper = new THREE.Mesh(new THREE.PlaneGeometry(paperW, paperH), new THREE.MeshStandardMaterial({ map: tex, roughness: 0.92 }));
  paper.rotation.x = -Math.PI / 2; paper.position.set(-40, 0.3, 40); paper.receiveShadow = true;
  scene.add(paper);
  const toWorld = ([px, py]) => new THREE.Vector3(paper.position.x - paperW / 2 + (px / W) * paperW, 0.3, paper.position.z - paperH / 2 + (py / H) * paperH);
  return { paper, draw, toWorld, tipAt };
}

export function buildPencil(scene) {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.CylinderGeometry(1.6, 1.6, 34, 6), clayMaterial({ color: 0xe3b53f, scale: 0.4, bump: 0.5 }));
  body.position.y = 19;
  const wood = new THREE.Mesh(new THREE.ConeGeometry(1.6, 4, 6), clayMaterial({ color: 0xe8c9a0, scale: 0.4 }));
  wood.position.y = 0.6 + 1.4; wood.rotation.x = Math.PI;
  const lead = new THREE.Mesh(new THREE.ConeGeometry(0.55, 1.4, 6), new THREE.MeshStandardMaterial({ color: 0x222222 }));
  lead.position.y = 0.2; lead.rotation.x = Math.PI;
  const eraser = new THREE.Mesh(new THREE.CylinderGeometry(1.65, 1.65, 3.2, 12), clayMaterial({ color: 0xd98a8a, scale: 0.4 }));
  eraser.position.y = 37.6;
  g.add(body, wood, lead, eraser);
  g.traverse((o) => { o.castShadow = true; });
  const pivot = new THREE.Group();
  pivot.add(g);
  g.rotation.z = -0.45;
  scene.add(pivot);
  return pivot;
}

/**
 * A pump-handle lever sized for the clay characters: the handle points back toward the operator
 * and swings about a horizontal pivot, so pushing the knob down moves it down, not sideways.
 * The arm rotates about Z; negative angles raise the knob.
 */
export const LEVER = { pivotY: 11, reach: 15, up: -0.47, down: 0.33 };
export function buildLever(scene) {
  const g = new THREE.Group();
  const metal = clayMaterial({ color: 0x3b4650, scale: 0.3 });
  const base = new THREE.Mesh(new THREE.RoundedBoxGeometry(12, 5, 11, 3, 1.6), metal);
  base.position.y = 2.5;
  const cheeks = [-3, 3].map((z) => {
    const c = new THREE.Mesh(new THREE.RoundedBoxGeometry(5, 10, 1.4, 2, 0.5), metal);
    c.position.set(0, 7.5, z);
    return c;
  });
  const hub = new THREE.Mesh(new THREE.CylinderGeometry(1.7, 1.7, 7.6, 14), clayMaterial({ color: 0x6f7b84, scale: 0.4 }));
  hub.rotation.x = Math.PI / 2; hub.position.y = LEVER.pivotY;
  const arm = new THREE.Group(); arm.position.y = LEVER.pivotY;
  const stick = new THREE.Mesh(new THREE.CylinderGeometry(1.05, 1.15, LEVER.reach, 10), clayMaterial({ color: 0x9aa4ab, scale: 0.4 }));
  stick.rotation.z = Math.PI / 2; stick.position.x = -LEVER.reach / 2;
  const knob = new THREE.Mesh(new THREE.SphereGeometry(2.6, 16, 12), clayMaterial({ color: 0xc8463a, scale: 0.4 }));
  knob.position.x = -LEVER.reach;
  arm.add(stick, knob);
  arm.rotation.z = LEVER.up;
  g.add(base, ...cheeks, hub, arm);
  g.traverse((o) => { o.castShadow = true; });
  g.position.set(150, 0, 60);
  scene.add(g);
  return { group: g, arm, knob };
}

export function buildTurntable(scene) {
  const g = new THREE.Group();
  const disc = new THREE.Mesh(new THREE.CylinderGeometry(70, 74, 6, 48), clayMaterial({ color: 0x2c3a44, scale: 0.03, bump: 0.35 }));
  disc.position.y = 3; disc.receiveShadow = true; disc.castShadow = true;
  const top = new THREE.Group(); top.position.y = 6;
  for (const x of [-40, 40]) {
    const cradle = new THREE.Mesh(new THREE.BoxGeometry(6, 9, 18), clayMaterial({ color: 0x8a6a4a, scale: 0.3 }));
    cradle.position.set(x, 4.5, 0); top.add(cradle);
  }
  g.add(disc, top);
  g.position.set(120, 0, -60);
  scene.add(g);
  return { group: g, top };
}

/**
 * An original low-poly miniature of a retired, publicly displayed aircraft shape (faceted
 * flying wing with a V-tail). It is a museum prop for the historical exhibit only: no
 * dimensions, no technical data, and nothing derived from the restricted manual.
 */
export function buildHistoricalMiniature(scene) {
  const P = {
    N: [62, 0, 0], RF: [20, 6.5, 0], RR: [-26, 5, 0], LR: [26, 0.6, 7], WR: [-40, 0, 44], N1: [-26, 0.5, 24], X1: [-44, 1, 8], C: [-36, 1, 0],
    B: [10, -2.5, 0], BR: [-28, -1.6, 0],
  };
  const tris = [
    ["N", "LR", "RF"], ["LR", "WR", "RF"], ["RF", "WR", "RR"], ["RR", "WR", "N1"], ["RR", "N1", "X1"], ["RR", "X1", "C"],
    ["N", "B", "LR"], ["LR", "B", "WR"], ["B", "BR", "WR"], ["BR", "N1", "WR"], ["BR", "X1", "N1"], ["BR", "C", "X1"],
  ];
  const pos = [];
  const push = (a, b, c, mirror) => {
    const f = (v) => (mirror ? [v[0], v[1], -v[2]] : v);
    const tri = mirror ? [f(a), f(c), f(b)] : [a, b, c];
    tri.forEach((v) => pos.push(...v));
  };
  tris.forEach((t, i) => {
    const [a, b, c] = t.map((k) => P[k]);
    const bottom = i >= 6;
    const ordered = bottom ? [a, c, b] : [a, b, c];
    push(...ordered, false); push(...ordered, true);
  });
  // V-tail
  const fin = (s) => [[-24, 4.5, 4 * s], [-42, 2, 6 * s], [-47, 17, 15 * s]];
  for (const s of [1, -1]) {
    const [a, b, c] = fin(s);
    pos.push(...a, ...b, ...c, ...a, ...c, ...b);
  }
  const geom = new THREE.BufferGeometry();
  geom.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  geom.computeVertexNormals();
  const mat = clayMaterial({ color: 0x2b3036, scale: 0.12, bump: 0.7, roughness: 0.7 });
  mat.flatShading = true;
  const plane = new THREE.Mesh(geom, mat);
  plane.castShadow = true;
  const stand = new THREE.Group();
  const post = new THREE.Mesh(new THREE.CylinderGeometry(1.2, 1.2, 22, 8), clayMaterial({ color: 0x8a8f96, scale: 0.4 }));
  post.position.y = 11;
  const foot = new THREE.Mesh(new THREE.CylinderGeometry(12, 13, 3, 24), clayMaterial({ color: 0x1d2328, scale: 0.2 }));
  foot.position.y = 1.5;
  plane.position.y = 24; plane.rotation.set(0.05, 0.6, -0.12);
  stand.add(foot, post, plane);
  // Museum placard
  const c = document.createElement("canvas"); c.width = 512; c.height = 256;
  const x = c.getContext("2d");
  x.fillStyle = "#f1e9d6"; x.fillRect(0, 0, 512, 256);
  x.fillStyle = "#3b2a17"; x.font = "600 30px Fraunces, Georgia, serif"; x.fillText("Historical subject", 28, 56);
  x.font = "22px 'Plex Sans', sans-serif"; x.fillStyle = "#4a3a28";
  ["F-117A Nighthawk, 1981–2008.", "Here for its information displays.", "Not a Project 33 component.", "No data from its flight manual."].forEach((l, i) => x.fillText(l, 28, 100 + i * 34));
  x.strokeStyle = "#b8925a"; x.lineWidth = 6; x.strokeRect(6, 6, 500, 244);
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
  const placard = new THREE.Mesh(new THREE.PlaneGeometry(40, 20), new THREE.MeshStandardMaterial({ map: tex, roughness: 0.8 }));
  placard.position.set(0, 7, 26); placard.rotation.x = -0.6;
  stand.add(placard);
  stand.scale.setScalar(1.35);
  stand.position.set(-175, 0, -55);
  stand.rotation.y = 0.45;
  scene.add(stand);
  return stand;
}

export function buildLamps(scene) {
  const lamps = [];
  for (const [x, z] of [[-140, -20], [130, -20]]) {
    const g = new THREE.Group();
    const cord = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.6, 200, 6), new THREE.MeshStandardMaterial({ color: 0x111111 }));
    cord.position.y = 100;
    const shade = new THREE.Mesh(new THREE.ConeGeometry(26, 22, 24, 1, true), clayMaterial({ color: 0x0f6a70, scale: 0.2 }));
    shade.material.side = THREE.DoubleSide;
    const bulb = new THREE.Mesh(new THREE.SphereGeometry(5, 12, 10), new THREE.MeshBasicMaterial({ color: 0xffe2b0 }));
    bulb.position.y = -6;
    const light = new THREE.PointLight(0xffd9a8, 9000, 900, 2);
    light.position.y = -8;
    light.castShadow = false;
    g.add(cord, shade, bulb, light);
    g.position.set(x, 190, z);
    scene.add(g);
    lamps.push({ group: g, light, bulb });
  }
  return lamps;
}
