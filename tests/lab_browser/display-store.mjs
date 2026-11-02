import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createDisplayStore } from '../../lab/js/instruments/store.js';

test('stale data stops moving while other sources continue and recovery takes a fresh sample', () => {
  const s = createDisplayStore(); s.tick(1);
  s.setSource('inertial', 'stale');
  const held = s.get(); s.tick(2);
  assert.equal(s.get().displayState.roll, held.displayState.roll);
  assert.notEqual(s.get().displayState.speed, held.displayState.speed);
  assert.ok(s.get().sources.inertial.age > held.sources.inertial.age);
  s.setSource('inertial','nominal');
  assert.notEqual(s.get().displayState.roll, held.displayState.roll);
  assert.equal(s.get().sources.inertial.state,'nominal');
});
test('missing data expires, getters cannot change state, invalid controls are rejected', () => {
  const s = createDisplayStore(); s.setSource('gnss','missing'); s.tick(2.1);
  assert.equal(s.get().sources.gnss.state,'stale');
  s.get().sources.gnss.lastGood.routeProgress = 999;
  assert.notEqual(s.get().displayState.routeProgress,999);
  for (const v of [0,6,NaN,3.5]) assert.throws(() => s.setDeclutter(v));
  assert.throws(() => s.tick(-1)); assert.throws(() => s.setSource('x','nominal'));
});
