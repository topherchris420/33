import { test } from 'node:test';
import assert from 'node:assert/strict';
import { comparePlans } from '../../lab/js/instruments/configuration.js';
const plan = () => ({ schema: 'project33.bench_plan/1', scope: 'stationary_inert_demonstrator', hardware_revision: 'A', specimen: { id: 'one' }, source_snapshot: [{ path: 'one.py', sha256: 'a'.repeat(64) }], installed_firmware: [{ id: 'rocket', sha256: null }] });
test('source matches cannot turn unknown installed binary declarations into matches', () => {
  const r = comparePlans(plan(), plan());
  assert.equal(r.rows.find(x => x.group === 'sources').state, 'matched');
  assert.equal(r.rows.find(x => x.group === 'firmware').state, 'unknown');
});
test('changed, added, missing and different specimens remain distinct', () => {
  const a = plan(), b = plan();
  b.source_snapshot = [{ path: 'two.py', sha256: 'b'.repeat(64) }];
  b.specimen.id = 'two';
  const r = comparePlans(a,b);
  assert.equal(r.counts.added, 1); assert.equal(r.counts.missing, 1); assert.equal(r.counts.changed, 1);
  assert.equal(a.specimen.id, 'one');
});
test('invalid schema, duplicate identities and malformed digests are rejected', () => {
  const a = plan();
  assert.throws(() => comparePlans({}, a));
  const b = plan(); b.source_snapshot.push(b.source_snapshot[0]);
  assert.throws(() => comparePlans(a,b), /Duplicate/);
  const c = plan(); c.installed_firmware[0].sha256 = 'unknown';
  assert.throws(() => comparePlans(a,c), /SHA-256/);
});
