import { h } from '../core/dom.js';

export function validateMonitorReport(report) {
  if (report?.schema !== 'project33.monitor_report/1' || !Array.isArray(report.boots) || report.boots.length > 1024) throw new Error('Expected a Project 33 USB monitor report');
  if (!Number.isFinite(report.elapsed_s) || report.elapsed_s < 0) throw new Error('Invalid report time');
  if (!Array.isArray(report.origins) || report.origins.length > 3 || report.origins.some(o => !['synthetic', 'undeclared', 'other declaration'].includes(o))) throw new Error('Invalid origin declaration');
  for (const boot of report.boots) {
    if (!['rocket', 'launcher'].includes(boot.role) || !/^[a-f0-9]{16}$/.test(boot.boot)) throw new Error('Invalid boot identity');
    if (!['UNKNOWN', 'REPORTED MATCH', 'MISMATCH', 'CONFLICT'].includes(boot.identity_comparison)) throw new Error('Invalid identity comparison');
    if (boot.elf_sha256 != null && !/^[a-f0-9]{64}$/.test(boot.elf_sha256)) throw new Error('Invalid ELF identity');
    if (!boot.sensors || Object.keys(boot.sensors).length > 4) throw new Error('Invalid sensor collection');
    for (const [name, sensor] of Object.entries(boot.sensors)) {
      if (!['mpu6050', 'bmp180', 'qmc5883l', 'gps'].includes(name) || !['REPORTED', 'INVALID', 'STALE', 'NOT OBSERVED'].includes(sensor.status)) throw new Error('Invalid sensor status');
      if ((name === 'mpu6050') !== (boot.role === 'rocket')) throw new Error('Sensor does not belong to this board role');
      if (sensor.status === 'NOT OBSERVED') continue;
      if (!Number.isFinite(sensor.age_s) || sensor.age_s < 0 || !sensor.values || !Object.keys(sensor.values).length || Object.keys(sensor.values).length > 7) throw new Error('Invalid reading age or values');
      if (sensor.status === 'REPORTED' && sensor.valid !== true) throw new Error('Invalid reading labeled reported');
      for (const value of Object.values(sensor.values)) {
        if (value !== null && !Number.isFinite(value)) throw new Error('Nonfinite sensor reading');
        if (sensor.status === 'REPORTED' && value === null) throw new Error('Missing value labeled reported');
      }
    }
    if (boot.system && !['reset_code', 'free_heap', 'min_heap'].every(k => Number.isSafeInteger(boot.system[k]) && boot.system[k] >= 0)) throw new Error('Invalid system diagnostics');
  }
  return report;
}

export function mountUSBMonitor(root) {
  if (!root) return;
  const file = h('input', { type: 'file', accept: '.json,application/json', id: 'usb-report-file', style: { width: '100%', maxWidth: '100%', margin: '12px 0' } });
  const output = h('div', { id: 'usb-report-result', role: 'status' });
  file.addEventListener('change', async () => {
    output.replaceChildren();
    const selected = file.files[0];
    if (!selected) return;
    try {
      if (selected.size > 2 * 1024 * 1024) throw new Error('Report must be at most 2 MB');
      const report = validateMonitorReport(JSON.parse(await selected.text()));
      if (file.files[0] !== selected) return;
      const origin = report.origins?.length ? report.origins.join(', ') : 'undeclared';
      output.replaceChildren(h('p', {}, `RAW DIAGNOSTICS / declared origin: ${origin} / ${report.elapsed_s.toFixed(1)} s`),
        h('p', { class: 'small muted' }, 'This is a supplied derived report. Replay the original capture with the Python tool to check its raw-file digest. A report is not hardware attestation or accepted evidence.'),
        ...report.boots.map(boot => h('section', { class: 'panel', style: { padding: '16px', marginBottom: '16px', overflowWrap: 'anywhere' } },
          h('h3', {}, `${boot.role} / boot ${boot.boot}`), h('p', {}, `Firmware identity: ${boot.identity_comparison}`),
          h('p', {}, h('code', {}, boot.elf_sha256 || 'ELF identity NOT OBSERVED')),
          h('p', {}, boot.system ? `${boot.system.status || 'UNKNOWN AGE'}: reset code ${boot.system.reset_code}; free heap ${boot.system.free_heap} bytes; minimum heap ${boot.system.min_heap} bytes.` : 'System diagnostics: NOT OBSERVED'),
          ...Object.entries(boot.sensors).map(([name, sensor]) => h('div', { 'data-usb-status': sensor.status },
            h('h4', {}, `${name} / ${sensor.status}`),
            h('p', {}, sensor.age_s === undefined ? 'Age: unknown' : `Age at report end: ${sensor.age_s.toFixed(2)} s`),
            h('dl', { class: 'kv' }, ...Object.entries(sensor.values || {}).flatMap(([field, value]) => [h('dt', {}, field), h('dd', {}, value === null ? 'NOT REPORTED' : `${value} ${sensor.units?.[field] || ''}`)])))))));
    } catch (error) { if (file.files[0] === selected) output.replaceChildren(h('p', { role: 'alert' }, error.message)); }
  });
  root.replaceChildren(h('label', { for: file.id }, 'Open report.json from the USB capture or replay tool'), file, output);
}
