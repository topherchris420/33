// Deterministic educational data-validity model. No sensor or device interfaces.
export const VALIDITY_DEFAULTS = Object.freeze({
  airdata: Object.freeze({ validity: 0.5 }),
  inertial: Object.freeze({ validity: 0.1 }),
  gnss: Object.freeze({ validity: 2 }),
});
export const VALIDITY_STATES = Object.freeze(["nominal", "missing", "stale", "inconsistent", "unavailable"]);
const PRIORITY = { warning: 0, caution: 1, advisory: 2, status: 3 };
const copy = (value) => value === undefined ? null : structuredClone(value);
function finite(value, name, minimum = 0) {
  if (!Number.isFinite(value) || value < minimum) throw new RangeError(`${name} must be finite and >= ${minimum}`);
  return value;
}
function validValue(value) {
  if (typeof value === "number") return Number.isFinite(value);
  return value !== null && typeof value === "object" && !Array.isArray(value)
    && Object.keys(value).length > 0 && Object.values(value).every((v) => typeof v === "number" && Number.isFinite(v));
}

/** Inputs and elapsed time are explicit, so identical events produce identical snapshots.
 * Before the first sample, sources are unavailable. A missing sample preserves last-good
 * data only for its configured window; after that it is stale. Disagreement is explicit.
 */
export function createValidityModel(config = VALIDITY_DEFAULTS) {
  if (!config || typeof config !== "object" || !Object.keys(config).length) throw new TypeError("source configuration required");
  const sources = new Map(Object.entries(config).map(([id, entry]) => {
    const validity = finite(entry?.validity, `${id} validity`);
    return [id, { validity, short: entry.short || ({ airdata: 'ADC', inertial: 'IRS', gnss: 'GNSS' }[id] || id.toUpperCase()), state: "unavailable", lastGood: null, lastValidAt: null }];
  }));
  let time = 0;
  const alerts = new Map();
  function source(id) {
    if (!sources.has(id)) throw new RangeError(`unknown source: ${id}`);
    return sources.get(id);
  }
  function syncAlerts() {
    const active = new Set();
    for (const [id, s] of sources) {
      if (!["stale", "inconsistent", "unavailable"].includes(s.state)) continue;
      const key = `${id}:${s.state}`;
      active.add(key);
      if (!alerts.has(key)) alerts.set(key, {
        id: key, source: id, kind: s.state === "unavailable" ? "warning" : "caution",
        text: `${s.state === 'unavailable' ? 'WARNING' : 'CAUTION'} ${s.short} ${ { stale: "DATA AGED", inconsistent: "DISAGREE", unavailable: "FAIL" }[s.state] }`,
        raisedAt: time,
      });
    }
    for (const key of alerts.keys()) if (!active.has(key)) alerts.delete(key);
  }
  function snapshot() {
    return {
      time,
      sources: Object.fromEntries([...sources].map(([id, s]) => [id, {
        ...s, age: s.lastValidAt === null ? null : time - s.lastValidAt,
        lastGood: copy(s.lastGood), value: s.state === "unavailable" ? null : copy(s.lastGood),
      }])),
      messages: [...alerts.values()].map((a) => ({ ...a, age: time - a.raisedAt })),
    };
  }
  function sample(id, value) {
    const s = source(id);
    if (!validValue(value)) throw new TypeError("sample must be a finite number or nonempty record of finite numbers");
    s.lastGood = copy(value); s.lastValidAt = time; s.state = "nominal";
    syncAlerts(); return snapshot();
  }
  function setSource(id, state, value) {
    const s = source(id);
    if (!VALIDITY_STATES.includes(state)) throw new RangeError(`unknown validity state: ${state}`);
    if (value !== undefined && !validValue(value)) throw new TypeError("invalid source value");
    if (state === "nominal") {
      if (value === undefined && s.lastGood === null) throw new TypeError("nominal requires an initial sample");
      return sample(id, value === undefined ? s.lastGood : value);
    }
    if (value !== undefined) { s.lastGood = copy(value); s.lastValidAt = time; }
    // A scenario may explicitly demonstrate an aged observation without waiting.
    if (state === "stale" && s.lastValidAt !== null && time - s.lastValidAt <= s.validity) s.lastValidAt = time - s.validity - 0.6;
    s.state = s.lastGood === null ? "unavailable" : state;
    if (s.state === "missing" && time - s.lastValidAt > s.validity) s.state = "stale";
    syncAlerts(); return snapshot();
  }
  function tick(dt) {
    finite(dt, "elapsed time");
    finite(time + dt, "clock");
    time += dt;
    for (const s of sources.values()) {
      if (["nominal", "missing"].includes(s.state) && time - s.lastValidAt > s.validity) s.state = "stale";
    }
    syncAlerts(); return snapshot();
  }
  syncAlerts();
  return { sample, setSource, tick, snapshot };
}

/** Display selection counts BOTH declutter exclusions and rows beyond capacity. */
export function selectAlerts(messages, { level = 5, capacity = 9, now = 0 } = {}) {
  if (!Number.isInteger(level) || level < 1 || level > 5) throw new RangeError("level must be an integer from 1 to 5");
  if (!Number.isInteger(capacity) || capacity < 0) throw new RangeError("capacity must be a nonnegative integer");
  finite(now, "clock");
  for (const m of messages) {
    if (!Object.hasOwn(PRIORITY, m.kind)) throw new RangeError("unknown alert kind");
    finite(m.raisedAt, "alert time");
    if (m.raisedAt > now) throw new RangeError("alert cannot be raised in the future");
  }
  const visible = messages.filter((m) => PRIORITY[m.kind] < Math.min(level, 4))
    .sort((a, b) => PRIORITY[a.kind] - PRIORITY[b.kind] || b.raisedAt - a.raisedAt || String(a.id).localeCompare(String(b.id)))
    .slice(0, capacity).map((m) => ({ ...copy(m), age: now - m.raisedAt }));
  return { visible, hidden: messages.length - visible.length, total: messages.length };
}
