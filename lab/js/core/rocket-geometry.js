// Geometry generated from the OpenRocket design file's own parameters (lab/data/openrocket.json,
// itself parsed from Simulation/Folding Stabilized Rocket.ork). Stations are millimetres from
// the nose tip along +X. Nothing here is invented: every dimension carries the XML path it came
// from, and things the file does not describe (the folding mechanism, joints) are reported as such.

const M = 1000; // metres -> millimetres

function f(c, key) { return c.fields[key]?.value; }
function src(c, key) { return c.fields[key]?.path; }

function finInstances(c) {
  const count = Math.round(f(c, "fincount") ?? f(c, "instancecount") ?? 1);
  const offset = f(c, "angleoffset") ?? 0;
  return Array.from({ length: count }, (_, i) => ({ index: i, angleDeg: offset + (360 * i) / count }));
}

/** Flatten the OpenRocket component list into displayable parts with provenance. */
export function rocketParts(or, { variant = "current" } = {}) {
  const model = or[variant];
  const comps = model.components;
  const byId = new Map(comps.map((c) => [c.id, c]));
  const parts = [];
  for (const c of comps) {
    if (c.kind === "stage") continue;
    const name = f(c, "name") || c.kind;
    const x0 = c.x_start_m * M, x1 = c.x_end_m * M;
    const parent = byId.get(c.parent);
    const base = {
      kind: c.kind, name, path: c.path, oid: c.id, x0, x1,
      material: f(c, "material") || null,
      overrideMass: f(c, "overridemass") ?? null,
      overrideMassSub: f(c, "overridesubcomponentsmass") ?? null,
      fields: c.fields, axialMethod: c.axial_method, parentName: parent ? f(parent, "name") : null,
      sourceFile: model.source.path,
    };
    if (c.kind === "nosecone") {
      parts.push({ ...base, id: `nose`, shape: f(c, "shape"), length: f(c, "length") * M, radius: f(c, "aftradius") * M, thickness: f(c, "thickness") * M });
    } else if (c.kind === "bodytube") {
      const idx = parts.filter((p) => p.kind === "bodytube").length + 1;
      parts.push({ ...base, id: `tube${idx}`, length: f(c, "length") * M, radius: f(c, "radius") * M, thickness: f(c, "thickness") * M });
      if (c.motor) {
        const mf = c.motor.fields;
        parts.push({
          kind: "motor", id: `motor${idx}`, name: `Motor envelope (${mf.designation?.value ?? "unnamed"})`, path: c.motor.path,
          x0: c.motor.x_start_m * M, x1: c.motor.x_end_m * M, length: mf.length.value * M, radius: (mf.diameter.value * M) / 2,
          fields: mf, designation: mf.designation?.value, manufacturer: mf.manufacturer?.value, overhang: c.motor.overhang_m * M,
          sourceFile: model.source.path, parentName: name,
        });
      }
    } else if (c.kind === "trapezoidfinset") {
      const host = parent;
      const idx = parts.filter((p) => p.kind === "trapezoidfinset").length + 1;
      parts.push({
        ...base, id: `fins${idx}`, rootChord: f(c, "rootchord") * M, tipChord: f(c, "tipchord") * M,
        sweep: f(c, "sweeplength") * M, span: f(c, "height") * M, thickness: f(c, "thickness") * M,
        crossSection: f(c, "crosssection"), cant: f(c, "cant") ?? 0, instances: finInstances(c),
        rootRadius: host ? f(host, "radius") * M : 0, axialOffset: c.axial_offset_m * M,
      });
    }
  }
  return parts;
}

/** Dimension annotations with provenance. Values in mm. */
export function rocketDimensions(or, parts) {
  const model = or.current;
  const dims = [];
  const nose = parts.find((p) => p.kind === "nosecone");
  const tubes = parts.filter((p) => p.kind === "bodytube");
  const fins = parts.filter((p) => p.kind === "trapezoidfinset");
  const motor = parts.find((p) => p.kind === "motor");
  const total = model.overall_length_m * M;
  dims.push({ id: "overall", label: "Overall length", value: total, from: [0, 0], to: [total, 0], offset: -95, axis: "x",
    source: "sum of nosecone/length and bodytube/length (stacked in document order)", part: null });
  if (nose) dims.push({ id: "nose-l", label: "Nose", value: nose.length, from: [0, 0], to: [nose.length, 0], offset: 98, axis: "x", source: src(nose, "length"), part: "nose" });
  tubes.forEach((t, i) => dims.push({ id: `${t.id}-l`, label: `${tubes.length > 1 ? (i === 0 ? "Fwd" : i === tubes.length - 1 ? "Aft" : `#${i + 1}`) + " tube" : "Tube"} length`, value: t.length, from: [t.x0, 0], to: [t.x1, 0], offset: 62, axis: "x", source: src(t, "length"), part: t.id }));
  if (tubes[0]) dims.push({ id: "dia", label: "Body diameter", value: 2 * tubes[0].radius, from: [tubes[0].x0 + 30, -tubes[0].radius], to: [tubes[0].x0 + 30, tubes[0].radius], offset: 0, axis: "y", source: `2 × ${src(tubes[0], "radius")}`, part: tubes[0].id });
  for (const fn of fins) {
    dims.push({ id: `${fn.id}-root`, label: "Root chord", value: fn.rootChord, from: [fn.x0, fn.rootRadius], to: [fn.x0 + fn.rootChord, fn.rootRadius], offset: -14, axis: "x", source: src(fn, "rootchord"), part: fn.id, finPlane: true });
    dims.push({ id: `${fn.id}-span`, label: "Span (height)", value: fn.span, from: [fn.x0 + fn.rootChord + 6, fn.rootRadius], to: [fn.x0 + fn.rootChord + 6, fn.rootRadius + fn.span], offset: 0, axis: "y", source: src(fn, "height"), part: fn.id, finPlane: true });
    dims.push({ id: `${fn.id}-tip`, label: "Tip chord", value: fn.tipChord, from: [fn.x0 + fn.sweep, fn.rootRadius + fn.span], to: [fn.x0 + fn.sweep + fn.tipChord, fn.rootRadius + fn.span], offset: 12, axis: "x", source: src(fn, "tipchord"), part: fn.id, finPlane: true });
    dims.push({ id: `${fn.id}-station`, label: `LE station (${fn.axialMethod})`, value: fn.x0, from: [0, 0], to: [fn.x0, 0], offset: fn.rootChord > 60 ? -130 : -118, axis: "x",
      source: `${src(fn, "axialoffset") || src(fn, "position")} (method="${fn.axialMethod}")`, part: fn.id });
  }
  if (motor) dims.push({ id: "motor-l", label: "Motor length (sim. input)", value: motor.length, from: [motor.x0, -motor.radius], to: [motor.x1, -motor.radius], offset: -30, axis: "x", source: `${motor.path}/length`, part: motor.id, internal: true });
  return dims;
}

/** Things the file does not describe, shown explicitly instead of being drawn. */
export function rocketUnspecified(parts) {
  const fins = parts.filter((p) => p.kind === "trapezoidfinset");
  const aft = fins.reduce((m, p) => (p.span > (m?.span ?? 0) ? p : m), null);
  const out = [];
  if (aft) out.push({ id: "hinge", label: "Fold hinge / mechanism", text: "NOT IN SOURCE — the OpenRocket file models fixed fins; the folding mechanism exists only as the C1 planar model.", at: [aft.x0, aft.rootRadius + 4], part: aft.id });
  out.push({ id: "joints", label: "Tube joints & fasteners", text: "NOT SPECIFIED", at: [parts.find((p) => p.id === "tube2")?.x0 ?? 381, 40], part: "tube2" });
  out.push({ id: "electronics", label: "Electronics bay layout", text: "NOT IN SOURCE — see the architecture view", at: [200, 0], part: "tube1" });
  return out;
}

/** Side-elevation outline (mm) for 2D drawings: body silhouette plus fins in the 0°/180° plane. */
export function elevationPaths(or, variant = "current") {
  const parts = rocketParts(or, { variant });
  const paths = [];
  const nose = parts.find((p) => p.kind === "nosecone");
  const tubes = parts.filter((p) => p.kind === "bodytube");
  const body = [];
  if (nose) {
    for (let i = 0; i <= 40; i++) {
      const x = (i / 40) * nose.length;
      body.push([x, nose.radius * Math.sqrt(Math.max(0, 1 - ((nose.length - x) / nose.length) ** 2))]);
    }
  }
  for (const t of tubes) { body.push([t.x0, t.radius], [t.x1, t.radius]); }
  const upper = body;
  const lower = body.map(([x, y]) => [x, -y]).reverse();
  paths.push({ id: "body", points: [...upper, ...lower], closed: true });
  for (const t of tubes) paths.push({ id: `${t.id}-joint`, points: [[t.x0, -t.radius], [t.x0, t.radius]], closed: false, thin: true });
  for (const fn of parts.filter((p) => p.kind === "trapezoidfinset")) {
    for (const sign of [1, -1]) {
      const r = fn.rootRadius * sign, s = fn.span * sign;
      paths.push({ id: `${fn.id}-${sign}`, points: [[fn.x0, r], [fn.x0 + fn.sweep, r + s], [fn.x0 + fn.sweep + fn.tipChord, r + s], [fn.x0 + fn.rootChord, r]], closed: false, fin: fn.id });
    }
  }
  return { parts, paths, length: or[variant].overall_length_m * M };
}

/** Build THREE geometries for a part. Returns [{geometry, matrix}] per instance. */
export function buildPartGeometry(THREE, part) {
  const lathe = (pts) => {
    const g = new THREE.LatheGeometry(pts.map(([r, y]) => new THREE.Vector2(Math.max(r, 0), y)), 72);
    g.rotateZ(-Math.PI / 2); // lathe axis +Y -> +X (station axis)
    return g;
  };
  if (part.kind === "nosecone") {
    const L = part.length, R = part.radius, t = part.thickness;
    const outer = [], inner = [];
    for (let i = 0; i <= 48; i++) {
      const y = (i / 48) * L;
      const r = R * Math.sqrt(Math.max(0, 1 - ((L - y) / L) ** 2));
      outer.push([r, y]);
      inner.push([Math.max(r - t, 0), Math.min(y + t * 0.0, L)]);
    }
    const pts = [...outer, ...inner.reverse().filter(([r]) => r > 0.01)];
    pts.push([0.0001, t]);
    const g = lathe(pts);
    g.translate(part.x0, 0, 0);
    return [{ geometry: g, instance: null }];
  }
  if (part.kind === "bodytube") {
    const R = part.radius, t = part.thickness, L = part.length;
    const g = lathe([[R - t, 0], [R, 0], [R, L], [R - t, L], [R - t, 0]]);
    g.translate(part.x0, 0, 0);
    return [{ geometry: g, instance: null }];
  }
  if (part.kind === "motor") {
    const g = new THREE.CylinderGeometry(part.radius, part.radius, part.length, 48, 1, false);
    g.rotateZ(-Math.PI / 2);
    g.translate(part.x0 + part.length / 2, 0, 0);
    return [{ geometry: g, instance: null }];
  }
  if (part.kind === "trapezoidfinset") {
    const shape = new THREE.Shape();
    shape.moveTo(0, 0);
    shape.lineTo(part.sweep, part.span);
    shape.lineTo(part.sweep + part.tipChord, part.span);
    shape.lineTo(part.rootChord, 0);
    shape.lineTo(0, 0);
    const bevel = part.crossSection === "rounded" ? Math.min(part.thickness * 0.45, 1.6) : 0;
    const depth = Math.max(part.thickness - 2 * bevel, 0.2);
    return part.instances.map((inst) => {
      // bevelOffset = -bevelSize keeps the outer silhouette exactly on the recorded planform.
      const g = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: bevel > 0, bevelThickness: bevel, bevelSize: bevel, bevelOffset: -bevel, bevelSegments: 3, curveSegments: 1 });
      g.translate(0, 0, -depth / 2);
      // Fin plane contains the axis (+X) and the radial direction; root sits on the tube.
      g.translate(part.x0, part.rootRadius, 0);
      g.rotateX((inst.angleDeg * Math.PI) / 180);
      return { geometry: g, instance: inst };
    });
  }
  return [];
}

/**
 * Drawing feature lines for axisymmetric parts: generator lines at 0/90/180/270 degrees
 * (they read as silhouettes in the standard views), end circles, and inner-wall circles.
 * Returns a flat array of segment endpoints [x,y,z, x,y,z, ...] in station coordinates.
 */
export function latheFeatureLines(part, segments = 96) {
  const out = [];
  const circle = (x, r) => {
    for (let i = 0; i < segments; i++) {
      const a0 = (i / segments) * Math.PI * 2, a1 = ((i + 1) / segments) * Math.PI * 2;
      out.push(x, r * Math.cos(a0), r * Math.sin(a0), x, r * Math.cos(a1), r * Math.sin(a1));
    }
  };
  const gens = [0, Math.PI / 2, Math.PI, (3 * Math.PI) / 2];
  if (part.kind === "nosecone") {
    const L = part.length, R = part.radius, n = 40;
    for (const a of gens) {
      for (let i = 0; i < n; i++) {
        const y0 = (i / n) * L, y1 = ((i + 1) / n) * L;
        const r0 = R * Math.sqrt(Math.max(0, 1 - ((L - y0) / L) ** 2)), r1 = R * Math.sqrt(Math.max(0, 1 - ((L - y1) / L) ** 2));
        out.push(part.x0 + y0, r0 * Math.cos(a), r0 * Math.sin(a), part.x0 + y1, r1 * Math.cos(a), r1 * Math.sin(a));
      }
    }
    circle(part.x0 + L, R);
  } else if (part.kind === "bodytube" || part.kind === "motor") {
    const R = part.radius;
    for (const a of gens) out.push(part.x0, R * Math.cos(a), R * Math.sin(a), part.x1, R * Math.cos(a), R * Math.sin(a));
    circle(part.x0, R); circle(part.x1, R);
    if (part.thickness) { circle(part.x0, R - part.thickness); circle(part.x1, R - part.thickness); }
  }
  return out;
}
