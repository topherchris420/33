// Display pose for a four-bar configuration, built on lab/js/core/math/fourbar.js.
// If the loop closes, both links meet at C (open branch, as four_bar.py's tip_trajectory uses).
// If it cannot close, the links are drawn in their closest-approach configuration — the
// orientation that minimises |Σ r_i| — so the visible gap equals the closure residual ε.
// A non-closing configuration is never drawn closed.
import { pose as fbPose } from "../core/math/fourbar.js";

export function displayPose({ a, b, c, d }, thetaDeg) {
  const p = fbPose(a, b, c, d, thetaDeg);
  const { A, B, D, f } = p;
  if (p.C) {
    const C = p.C[0];
    return { ...p, closed: true, P: C, Q: C, gap: 0 };
  }
  // unit vector B -> D (f > 0 whenever b != a or theta != 0)
  const ux = f > 1e-9 ? (D[0] - B[0]) / f : 1, uy = f > 1e-9 ? (D[1] - B[1]) / f : 0;
  let P, Q;
  if (p.mode === "nested" && c >= d) {
    // output circle inside the coupler circle: both ends on the ray from B through D
    P = [B[0] + c * ux, B[1] + c * uy];
    Q = [D[0] + d * ux, D[1] + d * uy];
  } else if (p.mode === "nested") {
    // coupler circle inside the output circle: both ends on the ray from D through B
    P = [B[0] - c * ux, B[1] - c * uy];
    Q = [D[0] - d * ux, D[1] - d * uy];
  } else {
    // circles apart: ends face each other along B -> D
    P = [B[0] + c * ux, B[1] + c * uy];
    Q = [D[0] - d * ux, D[1] - d * uy];
  }
  return { ...p, closed: false, P, Q, gap: Math.hypot(P[0] - Q[0], P[1] - Q[1]), u: [ux, uy] };
}

export const MODE_TEXT = {
  nested: "nested — one circle lies entirely inside the other",
  apart: "apart — the circles never reach each other",
};
