import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateMonitorReport } from '../../lab/js/instruments/usb-monitor.js';

const report = () => ({ schema: 'project33.monitor_report/1', elapsed_s: 1, origins: ['synthetic'], boots: [{
  role: 'rocket', boot: '0123456789abcdef', identity_comparison: 'UNKNOWN', system: null,
  sensors: { mpu6050: { status: 'REPORTED', valid: true, age_s: 0.5, values: { ax: 9.8 }, units: { ax: 'm/s^2' } } },
}] });
test('USB report preserves unknown identity and a declared synthetic origin', () => {
  const input = report(); assert.equal(validateMonitorReport(input), input);
  assert.equal(input.boots[0].identity_comparison, 'UNKNOWN');
});
test('USB report rejects nonfinite values, unknown shapes and false validity', () => {
  assert.throws(() => validateMonitorReport({}));
  const a = report(); a.boots[0].sensors.mpu6050.values.ax = Infinity;
  assert.throws(() => validateMonitorReport(a));
  const b = report(); b.boots[0].sensors.mpu6050.valid = false;
  assert.throws(() => validateMonitorReport(b));
  const c = report(); c.boots[0].sensors.mpu6050.age_s = -1;
  assert.throws(() => validateMonitorReport(c));
});
