// Signal utilities for the Telemetry Theater: a seeded generator (so synthetic data is
// reproducible and declared), FFT, and the filters demonstrated on screen.

/** Mulberry32: tiny deterministic PRNG. Same seed, same sequence, every browser. */
export function rng(seed = 33) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Standard normal samples from a uniform source (Box–Muller). */
export function gaussian(random) {
  let u = 0, v = 0;
  while (u === 0) u = random();
  while (v === 0) v = random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

/** In-place iterative radix-2 FFT. re/im lengths must be a power of two. */
export function fft(re, im) {
  const n = re.length;
  if (n & (n - 1)) throw new Error("FFT length must be a power of two");
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = (-2 * Math.PI) / len;
    const wr = Math.cos(ang), wi = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let cr = 1, ci = 0;
      for (let k = 0; k < len / 2; k++) {
        const ar = re[i + k], ai = im[i + k];
        const br = re[i + k + len / 2] * cr - im[i + k + len / 2] * ci;
        const bi = re[i + k + len / 2] * ci + im[i + k + len / 2] * cr;
        re[i + k] = ar + br; im[i + k] = ai + bi;
        re[i + k + len / 2] = ar - br; im[i + k + len / 2] = ai - bi;
        const ncr = cr * wr - ci * wi;
        ci = cr * wi + ci * wr; cr = ncr;
      }
    }
  }
}

/** One-sided amplitude spectrum of a uniformly sampled real signal with a Hann window. */
export function amplitudeSpectrum(samples, sampleRateHz) {
  let n = 1;
  while (n < samples.length) n <<= 1;
  const re = new Float64Array(n), im = new Float64Array(n);
  const mean = samples.reduce((s, v) => s + v, 0) / samples.length;
  let wsum = 0;
  for (let i = 0; i < samples.length; i++) {
    const w = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (samples.length - 1));
    re[i] = (samples[i] - mean) * w;
    wsum += w;
  }
  fft(re, im);
  const out = [];
  for (let k = 0; k <= n / 2; k++) {
    out.push({ hz: (k * sampleRateHz) / n, amplitude: (2 * Math.hypot(re[k], im[k])) / wsum });
  }
  return out;
}

/** Exponential moving average: y[k] = α x[k] + (1 − α) y[k−1]. NaN samples pass through as gaps. */
export function ema(values, alpha) {
  const out = new Array(values.length);
  let y = null;
  for (let i = 0; i < values.length; i++) {
    const x = values[i];
    if (!Number.isFinite(x)) { out[i] = NaN; continue; }
    y = y === null ? x : alpha * x + (1 - alpha) * y;
    out[i] = y;
  }
  return out;
}

/** Centred moving average over a window of odd length, ignoring non-finite samples. */
export function movingAverage(values, window) {
  const half = Math.floor(window / 2);
  return values.map((_, i) => {
    let s = 0, n = 0;
    for (let j = i - half; j <= i + half; j++) {
      if (j >= 0 && j < values.length && Number.isFinite(values[j])) { s += values[j]; n++; }
    }
    return n ? s / n : NaN;
  });
}

/** Time constant of an EMA at a fixed sample period, in seconds: τ = −T / ln(1 − α). */
export function emaTimeConstant(alpha, periodS) {
  return -periodS / Math.log(1 - alpha);
}
