// Dimension annotations drawn like a technical drawing: extension lines, a dimension line
// with arrowheads, and a label carrying the value and the exact source field it came from.
import { THREE, label3D } from "../core/three-kit.js";

const LINE = new THREE.LineBasicMaterial({ color: 0x9fe8df, transparent: true, opacity: 0.9, depthTest: false });
const EXT = new THREE.LineBasicMaterial({ color: 0x67d8cf, transparent: true, opacity: 0.45, depthTest: false });
const ARROW = new THREE.MeshBasicMaterial({ color: 0x9fe8df, depthTest: false });

/**
 * from/to: THREE.Vector3 in specimen space; offsetDir: unit vector for the dimension line offset;
 * offset: distance (mm). Returns a Group with userData {id, part}.
 */
export function dimension({ id, from, to, offsetDir, offset = 0, text, source, unspecified = false, part = null, scale = 1 }) {
  const group = new THREE.Group();
  group.userData = { id, part, kind: "dimension" };
  group.renderOrder = 10;
  const a = from.clone().addScaledVector(offsetDir, offset);
  const b = to.clone().addScaledVector(offsetDir, offset);
  const ext = new THREE.BufferGeometry().setFromPoints([
    from.clone().addScaledVector(offsetDir, Math.sign(offset) * 2 * scale), a.clone().addScaledVector(offsetDir, Math.sign(offset || 1) * 3 * scale),
    to.clone().addScaledVector(offsetDir, Math.sign(offset) * 2 * scale), b.clone().addScaledVector(offsetDir, Math.sign(offset || 1) * 3 * scale),
  ]);
  const extLines = new THREE.LineSegments(ext, EXT);
  extLines.renderOrder = 10;
  if (offset !== 0) group.add(extLines);
  const dir = b.clone().sub(a);
  const len = dir.length();
  dir.normalize();
  const head = Math.min(4.2 * scale, len / 4);
  const main = new THREE.Line(new THREE.BufferGeometry().setFromPoints([a.clone().addScaledVector(dir, head * 0.9), b.clone().addScaledVector(dir, -head * 0.9)]), LINE);
  main.renderOrder = 10;
  group.add(main);
  for (const [p, d] of [[a, dir], [b, dir.clone().negate()]]) {
    const cone = new THREE.Mesh(new THREE.ConeGeometry(head * 0.32, head, 10), ARROW);
    cone.position.copy(p).addScaledVector(d, head / 2);
    cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), d);
    cone.renderOrder = 10;
    group.add(cone);
  }
  const shortSource = source ? source.replace(/openrocket\/rocket\/subcomponents\/stage\[\d+\]\/subcomponents\//g, "").replace(/\/subcomponents\//g, "/") : source;
  const lbl = label3D(text, { className: `css2d-label dim${unspecified ? " unspecified" : ""}`, sub: shortSource });
  lbl.position.copy(a).lerp(b, 0.5);
  lbl.element.title = source ? `Source: ${source}` : "";
  group.add(lbl);
  group.userData.label = lbl;
  return group;
}

/** A callout for something the source does not specify: a leader line and a dashed label. */
export function unspecifiedCallout({ id, at, text, label, part = null, lift = new THREE.Vector3(0, 40, 0) }) {
  const group = new THREE.Group();
  group.userData = { id, part, kind: "unspecified" };
  const end = at.clone().add(lift);
  const leader = new THREE.Line(new THREE.BufferGeometry().setFromPoints([at, end]), new THREE.LineDashedMaterial({ color: 0x8fa2ad, dashSize: 2, gapSize: 2, depthTest: false }));
  leader.computeLineDistances();
  leader.renderOrder = 10;
  const dot = new THREE.Mesh(new THREE.SphereGeometry(1.4, 10, 8), new THREE.MeshBasicMaterial({ color: 0x8fa2ad, depthTest: false }));
  dot.position.copy(at);
  dot.renderOrder = 10;
  const short = text.split(" — ")[0];
  const lbl = label3D(`${label}: ${short}`, { className: "css2d-label unspecified", sub: text.includes(" — ") ? text.split(" — ")[1] : null });
  lbl.element.title = text;
  lbl.position.copy(end);
  group.add(leader, dot, lbl);
  return group;
}

/** A ring marking an axial station on an axisymmetric body. */
export function stationRing({ x, radius, color = 0xe3c27a, text, sub, dashed = false, width = 1.2 }) {
  const group = new THREE.Group();
  const ring = new THREE.Mesh(new THREE.TorusGeometry(radius, width, 8, 96), new THREE.MeshBasicMaterial({ color, transparent: true, opacity: dashed ? 0.55 : 0.95, depthTest: false }));
  ring.rotation.y = Math.PI / 2;
  ring.position.x = x;
  ring.renderOrder = 11;
  group.add(ring);
  if (dashed) {
    const ticks = new THREE.Group();
    for (let i = 0; i < 24; i++) {
      const t = new THREE.Mesh(new THREE.BoxGeometry(0.6, 2.4, 2.4), new THREE.MeshBasicMaterial({ color, depthTest: false }));
      const a = (i / 24) * Math.PI * 2;
      t.position.set(x, Math.cos(a) * (radius + 3), Math.sin(a) * (radius + 3));
      t.renderOrder = 11;
      ticks.add(t);
    }
    group.add(ticks);
  }
  const lbl = label3D(text, { className: "css2d-label always-sub", sub });
  lbl.element.style.borderColor = `#${new THREE.Color(color).getHexString()}`;
  lbl.position.set(x, radius + 14, 0);
  group.add(lbl);
  return group;
}

/** Axial band (e.g. a required window) as a translucent sleeve. */
export function stationBand({ x0, x1, radius, color = 0x4cc9bb, text, sub }) {
  const group = new THREE.Group();
  const len = Math.max(x1 - x0, 0.1);
  const g = new THREE.CylinderGeometry(radius, radius, len, 64, 1, true);
  g.rotateZ(-Math.PI / 2);
  const sleeve = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.14, side: THREE.DoubleSide, depthWrite: false }));
  sleeve.position.x = x0 + len / 2;
  sleeve.renderOrder = 9;
  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(g, 30), new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.5 }));
  edges.position.copy(sleeve.position);
  group.add(sleeve, edges);
  const lbl = label3D(text, { className: "css2d-label always-sub", sub });
  lbl.element.style.borderColor = `#${new THREE.Color(color).getHexString()}`;
  lbl.position.set(x0 + len / 2, -radius - 16, 0);
  group.add(lbl);
  return group;
}
