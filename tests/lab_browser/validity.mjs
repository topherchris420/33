import { test } from "node:test";
import assert from "node:assert/strict";
import { createValidityModel, selectAlerts } from "../../lab/js/instruments/validity.js";

test("last-good values survive missing/stale data and recover only on a sample", () => {
  const m = createValidityModel({ sensor: { validity: 1 } });
  assert.equal(m.snapshot().sources.sensor.value, null);
  m.sample("sensor", { reading: 42 });
  m.setSource("sensor", "missing");
  assert.equal(m.tick(1).sources.sensor.state, "missing");
  const stale = m.tick(0.001);
  assert.equal(stale.sources.sensor.state, "stale");
  assert.deepEqual(stale.sources.sensor.value, { reading: 42 });
  const raised = stale.messages[0].raisedAt;
  assert.equal(m.tick(4).messages[0].raisedAt, raised);
  assert.ok(Math.abs(m.snapshot().messages[0].age - 4) < 1e-9);
  assert.equal(m.sample("sensor", 43).sources.sensor.state, "nominal");
  assert.equal(m.snapshot().messages.length, 0);
});

test("disagreement and unavailable states are explicit and snapshots isolated", () => {
  const m = createValidityModel();
  const value = { reading: 12 };
  m.sample("inertial", value); value.reading = 90;
  m.setSource("inertial", "inconsistent");
  const snap = m.tick(2);
  assert.equal(snap.sources.inertial.state, "inconsistent");
  snap.sources.inertial.lastGood.reading = 999;
  assert.equal(m.snapshot().sources.inertial.lastGood.reading, 12);
  assert.equal(m.setSource("inertial", "unavailable").sources.inertial.value, null);
  assert.equal(m.snapshot().sources.inertial.lastGood.reading, 12);
});

test("invalid input cannot poison the clock or stored sample", () => {
  const m = createValidityModel(); m.sample("airdata", 3);
  for (const dt of [-1, NaN, Infinity, "1"]) assert.throws(() => m.tick(dt));
  for (const v of [NaN, Infinity, {}, { n: NaN }, null]) assert.throws(() => m.sample("airdata", v));
  assert.throws(() => m.sample("unknown", 1));
  assert.throws(() => m.setSource("airdata", "bogus"));
  assert.equal(m.snapshot().time, 0);
  assert.equal(m.snapshot().sources.airdata.value, 3);
});

test("alert priority, recency and both kinds of overflow are reflected", () => {
  const messages = [
    { id: "old", kind: "warning", raisedAt: 1 },
    { id: "new", kind: "warning", raisedAt: 2 },
    { id: "caution", kind: "caution", raisedAt: 3 },
    { id: "status", kind: "status", raisedAt: 4 },
  ];
  const result = selectAlerts(messages, { level: 2, capacity: 1, now: 5 });
  assert.deepEqual(result.visible.map((m) => m.id), ["new"]);
  assert.equal(result.visible[0].age, 3);
  assert.equal(result.hidden, 3);
  assert.equal(messages[0].id, "old");
  assert.throws(() => selectAlerts(messages, { now: 3 }));
  assert.throws(() => selectAlerts(messages, { level: 9, now: 5 }));
});

test("identical event streams reproduce the same state and alert identities", () => {
  const run = () => {
    const m = createValidityModel();
    m.sample("gnss", 7); m.tick(2); m.tick(0.01);
    m.setSource("gnss", "inconsistent"); m.tick(1);
    return m.snapshot();
  };
  assert.deepEqual(run(), run());
});
