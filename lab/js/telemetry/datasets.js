// Two read-only datasets for the Telemetry Theater, both SYNTHETIC.
// A — the repository's own intentionally flawed fixture (python -m evidence demo), parsed
//     row by row so the audit's line numbers point at real rows.
// B — a declared, seeded generator. Every equation and parameter is shown on screen; the
//     "truth" it exposes exists only because the data are fabricated.
import { rng, gaussian } from "../core/math/signal.js";

export const NOMINAL_PERIOD_MS = 50; // firmware telemetry period (docs/ARCHITECTURE.md)
export const SERVO_LIMIT_DEG = 12;   // max deflection, protocol/ground_status_model.json firmware_limits

/** Minimal RFC-4180 CSV parser (handles quoted fields with commas). */
export function parseQuotedCSV(text) {
  const rows = [];
  let row = [], cell = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (ch === '"') quoted = false;
      else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(cell); rows.push(row); row = []; cell = "";
    } else cell += ch;
  }
  if (cell.length || row.length) { row.push(cell); rows.push(row); }
  return rows.filter((r) => r.length > 1 || r[0] !== "");
}

const num = (s) => {
  if (s === undefined || s === "") return null;
  const v = Number(s);
  return Number.isFinite(v) ? v : NaN; // "NaN" stays NaN: an invalid sample, never zero
};

/** Dataset A: the fixture CSV, keeping file line numbers (header = line 1). */
export function fixtureDataset(fixture) {
  const table = parseQuotedCSV(fixture.csv);
  const head = table[0];
  const t0 = Date.parse(table[1][0]);
  const rows = table.slice(1).map((cells, i) => {
    const r = Object.fromEntries(head.map((k, j) => [k, cells[j]]));
    return {
      line: i + 2,
      received_s: (Date.parse(r.received_at_iso) - t0) / 1000,
      type: r.message_type,
      time_ms: num(r.time_ms),
      roll_deg: num(r.roll_deg),
      rate_deg_s: num(r.rate_deg_s),
      servo_output: num(r.servo_output),
      raw: r.raw,
    };
  });
  const streams = {
    T: rows.filter((r) => r.type === "T"),
    LOG: rows.filter((r) => r.type === "LOG"),
  };
  const events = rows.filter((r) => r.type === "RAW").map((r) => ({ line: r.line, t: r.received_s, label: r.raw }));
  const byLine = new Map(rows.map((r) => [r.line, r]));
  const annotations = fixture.audit.details.map((d) => {
    const row = byLine.get(d.line);
    return { line: d.line, code: d.code, severity: d.severity, row, text: AUDIT_TEXT[d.code] || d.code };
  });
  return {
    id: "A",
    title: "Repository fixture — intentionally flawed",
    origin: fixture.origin,
    generator: fixture.generator,
    rows, streams, events, annotations,
    audit: fixture.audit,
    inputs: fixture.inputs,
    periodMs: NOMINAL_PERIOD_MS,
  };
}

export const AUDIT_TEXT = {
  duplicate_sample: "Duplicate sample: same device time and values as the row before.",
  invalid_numeric_sample: "Invalid numeric sample (NaN): counted and excluded — drawn as a gap, never as zero.",
  device_time_gap: "Device-time gap above the 500 ms threshold (100 → 900 ms).",
  device_clock_regression: "Device clock regression (900 → 10 ms). Reset, reorder, or rollover: no cause inferred.",
  log_dump_unterminated: "Log dump announced 3 rows, delivered 2, and never sent LOG_END.",
  interval_differs_from_expected: "Median interval differs from the 50 ms firmware period.",
};

export const GENERATOR_DEFAULTS = {
  seed: 33,
  samples: 240,          // 12 s at the 50 ms period
  stepTime: 2.0,         // s, disturbance onset
  amplitude: 15,         // deg, initial roll disturbance
  tau: 0.9,              // s, decay time constant
  dampedHz: 1.1,         // Hz, oscillation of the decaying response
  driftAmp: 2.0,         // deg, slow disturbance amplitude
  driftHz: 0.25,         // Hz
  sigmaRoll: 0.45,       // deg, additive Gaussian noise
  sigmaRate: 3.0,        // deg/s
  quantum: 0.05,         // deg, reporting resolution of roll
  jitterMs: 8,           // ms, uniform relay jitter 0..J
  dropProb: 0.02,        // per-sample probability the packet never arrives
  nanProb: 0.006,        // per-sample probability of an invalid numeric value
  kp: 0.55, kd: 0.06,    // illustrative gains for the servo channel (not firmware values)
};

/** Noise-free generator signal (only knowable because the data are synthetic). */
export function generatorTruth(p, t) {
  const drift = p.driftAmp * Math.sin(2 * Math.PI * p.driftHz * t);
  const dDrift = p.driftAmp * 2 * Math.PI * p.driftHz * Math.cos(2 * Math.PI * p.driftHz * t);
  let roll = drift, rate = dDrift;
  if (t >= p.stepTime) {
    const s = t - p.stepTime, w = 2 * Math.PI * p.dampedHz, e = Math.exp(-s / p.tau);
    roll += p.amplitude * e * Math.cos(w * s);
    rate += p.amplitude * e * (-Math.cos(w * s) / p.tau - w * Math.sin(w * s));
  }
  const servo = Math.max(-SERVO_LIMIT_DEG, Math.min(SERVO_LIMIT_DEG, -(p.kp * roll + p.kd * rate)));
  return { roll, rate, servo };
}

/** Dataset B: deterministic synthetic roll telemetry at the firmware period. */
export function generatorDataset(params = {}) {
  const p = { ...GENERATOR_DEFAULTS, ...params };
  const random = rng(p.seed);
  const rows = [];
  const truth = [];
  let dropped = 0, invalid = 0;
  for (let k = 0; k < p.samples; k++) {
    const t = (k * NOMINAL_PERIOD_MS) / 1000;
    const tr = generatorTruth(p, t);
    truth.push({ t, ...tr });
    // Draw every random number for every sample so changing one probability does not
    // reshuffle the rest of the sequence.
    const nRoll = gaussian(random), nRate = gaussian(random), jitter = random() * p.jitterMs;
    const uDrop = random(), uNan = random();
    if (uDrop < p.dropProb) { dropped++; continue; }
    let roll = Math.round((tr.roll + p.sigmaRoll * nRoll) / p.quantum) * p.quantum;
    roll = Number(roll.toFixed(4));
    const rate = Number((tr.rate + p.sigmaRate * nRate).toFixed(2));
    const servo = Math.round(Math.max(-SERVO_LIMIT_DEG, Math.min(SERVO_LIMIT_DEG, -(p.kp * roll + p.kd * rate))));
    const bad = uNan < p.nanProb;
    if (bad) invalid++;
    const relayMs = k * NOMINAL_PERIOD_MS + jitter;
    rows.push({
      line: rows.length + 2, k, type: "T",
      received_s: relayMs / 1000 + 0.004,
      time_ms: Math.round(relayMs),
      roll_deg: bad ? NaN : roll,
      rate_deg_s: rate,
      servo_output: servo,
      raw: `T,${Math.round(relayMs)},${bad ? "NaN" : roll},${rate},${servo}`,
    });
  }
  return {
    id: "B",
    title: "Declared generator — seeded synthetic roll response",
    origin: "SOFTWARE-GENERATED TEST DATA — MODELS NO HARDWARE",
    generator: "lab/js/telemetry/datasets.js generatorDataset()",
    params: p,
    rows, truth,
    streams: { T: rows },
    events: [{ t: p.stepTime, label: `disturbance onset t₀ = ${p.stepTime} s (generator parameter)` }],
    annotations: [],
    stats: { dropped, invalid, delivered: rows.length },
    periodMs: NOMINAL_PERIOD_MS,
  };
}

/** Intervals between successive rows of a stream, in device milliseconds. */
export function intervals(stream) {
  const out = [];
  for (let i = 1; i < stream.length; i++) {
    const a = stream[i - 1].time_ms, b = stream[i].time_ms;
    out.push({ at: stream[i], dt: a === null || b === null ? null : b - a });
  }
  return out;
}

/** Uniform resample of a stream for spectral analysis: index k at the nominal period, gaps bridged linearly. */
export function uniformSeries(dataset, key) {
  const n = dataset.params.samples;
  const series = new Array(n).fill(NaN);
  for (const r of dataset.rows) if (Number.isFinite(r[key])) series[r.k] = r[key];
  let last = -1;
  for (let i = 0; i < n; i++) {
    if (Number.isFinite(series[i])) {
      if (last >= 0 && i - last > 1) for (let j = last + 1; j < i; j++) series[j] = series[last] + ((series[i] - series[last]) * (j - last)) / (i - last);
      last = i;
    }
  }
  const first = series.findIndex(Number.isFinite);
  for (let i = 0; i < first; i++) series[i] = series[first];
  for (let i = last + 1; i < n; i++) series[i] = series[last];
  return series;
}
