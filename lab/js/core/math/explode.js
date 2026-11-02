// Deterministic exploded-view placement. Each part gets a fixed direction and order from
// its geometry (or from an explicit plan), so the same amount always yields the same
// pose, assembly and disassembly are exact inverses, and paths never depend on frame rate.

/**
 * plan: [{ id, center: [x,y,z], direction?: [x,y,z], distance?: number, order?: number }]
 * options.axis: unit vector of the specimen axis (stack direction for axial parts)
 * options.origin: assembly reference point
 * options.spread: base separation in scene units at amount = 1
 * Returns { offsets(amount) -> Map(id -> [dx,dy,dz]), sequence: ids in disassembly order }.
 */
export function explodePlan(plan, { axis = [1, 0, 0], origin = [0, 0, 0], spread = 100, stagger = 0.55 } = {}) {
  const norm = (v) => { const l = Math.hypot(...v) || 1; return v.map((x) => x / l); };
  const ax = norm(axis);
  const parts = plan.map((p, index) => {
    let dir = p.direction;
    if (!dir) {
      const rel = p.center.map((c, i) => c - origin[i]);
      const along = rel[0] * ax[0] + rel[1] * ax[1] + rel[2] * ax[2];
      const radial = rel.map((r, i) => r - along * ax[i]);
      const rlen = Math.hypot(...radial);
      dir = rlen > 1e-6 ? radial : ax.map((a) => a * Math.sign(along || 1));
    }
    return { id: p.id, dir: norm(dir), distance: p.distance ?? spread, order: p.order ?? index };
  });
  const sequence = [...parts].sort((a, b) => a.order - b.order || (a.id < b.id ? -1 : 1)).map((p) => p.id);
  const count = sequence.length;
  const slot = new Map(sequence.map((id, i) => [id, i]));
  /** amount in [0, 1]; sequential = staged disassembly in plan order. */
  function offsets(amount, { sequential = false } = {}) {
    const a = Math.min(Math.max(amount, 0), 1);
    const out = new Map();
    for (const p of parts) {
      let k = a;
      if (sequential && count > 1) {
        const window = 1 - stagger;
        const start = (slot.get(p.id) / (count - 1)) * stagger;
        k = Math.min(Math.max((a - start) / window, 0), 1);
      }
      const e = k * k * (3 - 2 * k);
      out.set(p.id, p.dir.map((d) => d * p.distance * e));
    }
    return out;
  }
  return { offsets, sequence, parts };
}
