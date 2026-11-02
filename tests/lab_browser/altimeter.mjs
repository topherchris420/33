import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { validateAltimeterReport } from '../../lab/js/instruments/altimeter.js';
const example = () => JSON.parse(readFileSync(new URL('../../lab/data/altimeter_example_review.json', import.meta.url)));

test('Python example validates with distinct simulated markers and observer declarations', () => {
  const r = example(); assert.equal(validateAltimeterReport(r), r);
  assert.equal(r.events[1].kind, 'SIMULATED_RELEASE_MARKER');
  assert.ok(r.events[1].time_s > r.events[1].sampled_peak_time_s);
});

test('ground source cannot be loaded with rocket release markers', () => {
  const r = example(); r.sensor.mount = 'launcher'; r.summary.rocket_altitude_available = false;
  assert.throws(() => validateAltimeterReport(r), /review marker/);
  r.events = []; assert.equal(validateAltimeterReport(r), r);
});

test('invalid values, clocks, identities and unearned validity fail report loading', () => {
  for (const change of [
    r => { r.samples[0].height_m = Infinity; },
    r => { r.samples[1].time_s = 0; },
    r => { r.samples[0].status = 'INVALID'; },
    r => { r.samples[0].status = 'ESTIMATED'; },
    r => { r.samples[0].origin = 'measured'; },
    r => { r.implementation_sha256 = ''; },
    r => { r.observations[0].operator = ''; },
  ]) { const r = example(); change(r); assert.throws(() => validateAltimeterReport(r)); }
});
