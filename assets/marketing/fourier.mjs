/** Closed-contour Fourier drawing, independent of the browser and renderer. */
export const TAU = Math.PI * 2;
export const clamp = (v, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, v));
export const smooth = (v) => {
  const t = clamp(v);
  return t * t * (3 - 2 * t);
};

export function resample(points, count = 128) {
  if (points.length < 2 || count < 2)
    throw new RangeError("A contour needs at least two points and samples.");
  const lengths = points.map((p, i) =>
    Math.hypot(
      p[0] - points[(i + 1) % points.length][0],
      p[1] - points[(i + 1) % points.length][1],
    ),
  );
  const total = lengths.reduce((a, b) => a + b, 0);
  if (!total) throw new RangeError("A contour must have nonzero length.");
  let edge = 0,
    offset = 0;
  return Array.from({ length: count }, (_, i) => {
    const distance = (i * total) / count;
    while (edge < lengths.length - 1 && offset + lengths[edge] < distance)
      offset += lengths[edge++];
    const a = points[edge],
      b = points[(edge + 1) % points.length];
    const t = lengths[edge] ? (distance - offset) / lengths[edge] : 0;
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
  });
}

export function transform(samples) {
  const n = samples.length;
  if (!n) throw new RangeError("Samples cannot be empty.");
  return samples
    .map((_, k) => {
      let re = 0,
        im = 0;
      samples.forEach(([x, y], j) => {
        const a = (TAU * k * j) / n;
        re += x * Math.cos(a) + y * Math.sin(a);
        im += y * Math.cos(a) - x * Math.sin(a);
      });
      re /= n;
      im /= n;
      return {
        frequency: k <= n / 2 ? k : k - n,
        re,
        im,
        amplitude: Math.hypot(re, im),
        phase: Math.atan2(im, re),
      };
    })
    .sort((a, b) => b.amplitude - a.amplitude);
}

export function chain(coefficients, t) {
  const points = [[0, 0]];
  for (const term of coefficients) {
    const a = TAU * term.frequency * t + term.phase;
    const p = points[points.length - 1];
    points.push([
      p[0] + term.amplitude * Math.cos(a),
      p[1] + term.amplitude * Math.sin(a),
    ]);
  }
  return points;
}

export const evaluate = (coefficients, t) => chain(coefficients, t).at(-1);
