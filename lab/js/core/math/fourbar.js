// Planar four-bar kinematics, a line-by-line port of mechanism/four_bar.py (revision 2).
// Convention (mm, degrees): ground pivot A at the origin, ground pivot D at (a, 0).
// Input link AB rotates by the drive angle θ; coupler BC and output DC close the loop.
// A pose that cannot close returns null — never a numeric placeholder (see D-003).
// tests/lab_math.test.mjs checks this port against the Python model and the committed sweep.

export const DRIVE_MIN_DEG = 0;
export const DRIVE_MAX_DEG = 92;
export const DRIVE_STEP_DEG = 2;
export const BASELINE = { ground: 25, coupler: 60, input: 15, output: 15 };

const rad = (d) => (d * Math.PI) / 180;
const deg = (r) => (r * 180) / Math.PI;

export function grashofCondition(a, b, c, d) {
  const [s, p, q, l] = [a, b, c, d].sort((x, y) => x - y);
  if (s + l < p + q) return "Grashof";
  if (s + l > p + q) return "non-Grashof";
  return "change-point";
}

/** Distance B–D for drive angle θ (the loop diagonal f). */
export function diagonal(a, b, thetaDeg) {
  const t = rad(thetaDeg);
  return Math.sqrt(Math.max(a * a + b * b - 2 * a * b * Math.cos(t), 0));
}

/** Both coupler–output joint positions C, or null when the circles do not intersect. */
export function closurePoints(a, b, c, d, theta2Rad) {
  const bx = b * Math.cos(theta2Rad), by = b * Math.sin(theta2Rad);
  const dx = a - bx, dy = -by;
  const f = Math.hypot(dx, dy);
  if (f === 0 || f > c + d || f < Math.abs(c - d)) return null;
  const along = (c * c - d * d + f * f) / (2 * f);
  const height = Math.sqrt(Math.max(c * c - along * along, 0));
  const ux = dx / f, uy = dy / f;
  const baseX = bx + along * ux, baseY = by + along * uy;
  return [[baseX - height * uy, baseY + height * ux], [baseX + height * uy, baseY - height * ux]];
}

/** Transmission angle μ between coupler and output link, degrees, or null. */
export function transmissionAngle(ground, coupler, input, output, thetaDeg) {
  const a = ground, b = input, c = coupler, d = output;
  const fSq = a * a + b * b - 2 * a * b * Math.cos(rad(thetaDeg));
  if (fSq <= 0) return null;
  const cosMu = (c * c + d * d - fSq) / (2 * c * d);
  if (cosMu > 1 || cosMu < -1) return null;
  return deg(Math.acos(cosMu));
}

/**
 * Loop-closure residual ε(θ) = min over θ3, θ4 of |r_AB + r_BC + r_CD + r_DA|, in mm.
 * For a pin-jointed loop it equals the gap between the coupler circle about B and the
 * output circle about D: max(0, |c−d| − f, f − (c + d)). Zero means the loop can close.
 */
export function closureResidual(a, b, c, d, thetaDeg) {
  const f = diagonal(a, b, thetaDeg);
  return Math.max(0, Math.abs(c - d) - f, f - (c + d));
}

/** Which inequality fails: "nested" (one circle inside the other), "apart", or null. */
export function closureFailureMode(a, b, c, d, thetaDeg) {
  const f = diagonal(a, b, thetaDeg);
  if (f < Math.abs(c - d)) return "nested";
  if (f > c + d) return "apart";
  return null;
}

export function tipTrajectory(ground, coupler, input, output, min, max, numSteps = 200) {
  const a = ground, b = input, c = coupler, d = output;
  const xs = [], ys = [];
  for (let i = 0; i < numSteps; i++) {
    const theta = min + ((max - min) * i) / Math.max(numSteps - 1, 1);
    const pts = closurePoints(a, b, c, d, rad(theta));
    if (pts === null) continue;
    xs.push(pts[0][0]); ys.push(pts[0][1]);
  }
  return [xs, ys];
}

export function sweptEnvelopeRadius(xs, ys) {
  if (!xs.length) return null;
  let m = 0;
  for (let i = 0; i < xs.length; i++) m = Math.max(m, xs[i] * xs[i] + ys[i] * ys[i]);
  return Math.sqrt(m);
}

/** Python's round(x, 2) — round half to even on the decimal representation. */
export function round2(value) {
  if (value === null) return null;
  const scaled = value * 100;
  const floor = Math.floor(scaled);
  const diff = scaled - floor;
  let r;
  if (Math.abs(diff - 0.5) < 1e-9) r = floor % 2 === 0 ? floor : floor + 1;
  else r = Math.round(scaled);
  return r / 100;
}

/** Mirror of evaluate_linkage(a, c, b, d): ground a, coupler c, input b, output d. */
export function evaluateLinkage(a, c, b, d) {
  const angles = [];
  for (let t = DRIVE_MIN_DEG; t <= DRIVE_MAX_DEG; t += DRIVE_STEP_DEG) angles.push(t);
  const mus = angles.map((t) => transmissionAngle(a, c, b, d, t));
  const closed = mus.filter((m) => m !== null);
  const [xs, ys] = tipTrajectory(a, c, b, d, DRIVE_MIN_DEG, DRIVE_MAX_DEG);
  return {
    ground: a, coupler: c, input: b, output: d,
    grashof: grashofCondition(a, b, c, d),
    poses_evaluated: angles.length,
    poses_closed: closed.length,
    assemblable_over_range: closed.length === angles.length,
    min_transmission_angle: closed.length ? round2(Math.min(...closed)) : null,
    max_transmission_angle: closed.length ? round2(Math.max(...closed)) : null,
    max_envelope_radius: round2(sweptEnvelopeRadius(xs, ys)),
  };
}

/**
 * Coupler lengths that close the loop at every drive angle in [min, max], holding the
 * other three links fixed: c must satisfy |c − d| ≤ f(θ) ≤ c + d for all θ.
 * Returns {low, high} or null. Arithmetic on the closure inequality — not a design choice.
 */
export function couplerClosureBand(a, b, d, min = DRIVE_MIN_DEG, max = DRIVE_MAX_DEG, step = 0.1) {
  let fMin = Infinity, fMax = -Infinity;
  for (let t = min; t <= max + 1e-9; t += step) {
    const f = diagonal(a, b, t);
    fMin = Math.min(fMin, f); fMax = Math.max(fMax, f);
  }
  // c + d ≥ fMax  →  c ≥ fMax − d ;  |c − d| ≤ fMin  →  d − fMin ≤ c ≤ d + fMin
  const low = Math.max(fMax - d, d - fMin, 0);
  const high = d + fMin;
  return low <= high ? { low, high, fMin, fMax } : null;
}

/** Joint positions for drawing: A, B, D always; C (both branches) when the pose closes. */
export function pose(a, b, c, d, thetaDeg) {
  const t = rad(thetaDeg);
  const A = [0, 0], D = [a, 0], B = [b * Math.cos(t), b * Math.sin(t)];
  const C = closurePoints(a, b, c, d, t);
  return { A, B, D, C, f: diagonal(a, b, thetaDeg), residual: closureResidual(a, b, c, d, thetaDeg), mode: closureFailureMode(a, b, c, d, thetaDeg) };
}
