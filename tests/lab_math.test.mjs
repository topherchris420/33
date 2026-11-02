// Laboratory math: the JavaScript four-bar port must agree with mechanism/four_bar.py and
// with the committed C1 sweep; explode placement must be deterministic and reversible;
// signal utilities must be reproducible. Run: node --test tests/lab_math.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import * as FB from "../lab/js/core/math/fourbar.js";
import { explodePlan } from "../lab/js/core/math/explode.js";
import { rng, amplitudeSpectrum, ema, emaTimeConstant } from "../lab/js/core/math/signal.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const sweep = JSON.parse(readFileSync(join(ROOT, "docs/EVIDENCE/C1_four_bar_sweep.json"), "utf8"));

test("every committed C1 sweep row is reproduced exactly by the JS port", () => {
  assert.equal(sweep.rows.length, 81);
  for (const row of [sweep.baseline, ...sweep.rows]) {
    const js = FB.evaluateLinkage(row.ground, row.coupler, row.input, row.output);
    assert.deepEqual(js, row, `mismatch for ${row.ground}/${row.coupler}/${row.input}/${row.output}`);
  }
  assert.equal(sweep.summary.closing_at_any_pose, 0);
});

test("baseline residual is the nested-circle gap and never reaches zero over 0-92 deg", () => {
  const { ground: a, input: b, coupler: c, output: d } = FB.BASELINE;
  for (let t = 0; t <= 92; t += 0.5) {
    const r = FB.closureResidual(a, b, c, d, t);
    assert.ok(r > 15, `residual ${r} at ${t}`);
    assert.equal(FB.closureFailureMode(a, b, c, d, t), "nested");
    assert.ok(Math.abs(r - (Math.abs(c - d) - FB.diagonal(a, b, t))) < 1e-12);
  }
  // D-002 states the 0-92 deg B-D maximum precisely.
  assert.equal(FB.diagonal(a, b, 92).toFixed(1), "29.6");
});

test("closing configurations agree with the Python model, including rounding", (t) => {
  const configs = [[25, 25, 15, 15], [25, 20, 15, 15], [30, 28, 12, 18], [25, 18, 12, 15], [20, 15, 10, 12]];
  let python;
  try {
    const code = [
      "import json, sys",
      `sys.path.insert(0, ${JSON.stringify(join(ROOT, "mechanism"))})`,
      "import four_bar",
      `print(json.dumps([four_bar.evaluate_linkage(*c) for c in ${JSON.stringify(configs)}]))`,
    ].join("\n");
    python = JSON.parse(execFileSync(process.env.PYTHON || "python3", ["-c", code], { encoding: "utf8" }));
  } catch (err) {
    t.skip(`python unavailable: ${err.message}`);
    return;
  }
  configs.forEach((c, i) => assert.deepEqual(FB.evaluateLinkage(...c), python[i], `config ${c}`));
  assert.ok(python.some((r) => r.poses_closed > 0), "fixture must include configurations that close");
});

test("coupler closure band follows from the closure inequality", () => {
  const band = FB.couplerClosureBand(25, 15, 15);
  assert.ok(Math.abs(band.low - 14.6) < 0.05 && Math.abs(band.high - 25) < 1e-9, JSON.stringify(band));
  for (const c of [band.low + 0.01, 20, band.high - 1e-6]) {
    for (let t = 0; t <= 92; t += 1) assert.equal(FB.closureResidual(25, 15, c, 15, t), 0);
  }
  assert.ok(FB.closureResidual(25, 15, 60, 15, 0) > 0);
});

test("explode placement is deterministic, bounded, and exactly reversible", () => {
  const plan = [
    { id: "nose", center: [-200, 0, 0] }, { id: "fin", center: [250, 60, 0] },
    { id: "tube", center: [0, 0, 0], direction: [0, 1, 0], distance: 40 },
  ];
  const a = explodePlan(plan, { spread: 100 });
  const b = explodePlan(plan, { spread: 100 });
  for (const amount of [0, 0.25, 0.5, 1]) {
    for (const seq of [false, true]) {
      assert.deepEqual([...a.offsets(amount, { sequential: seq })], [...b.offsets(amount, { sequential: seq })]);
    }
  }
  for (const [, v] of a.offsets(0)) assert.deepEqual(v.map((x) => Math.abs(x)), [0, 0, 0]);
  assert.deepEqual(a.offsets(1).get("fin").map((x) => Math.round(x) + 0), [0, 100, 0]);
  assert.deepEqual(a.offsets(1).get("nose").map((x) => Math.round(x) + 0), [-100, 0, 0]);
  assert.deepEqual(a.offsets(1.7).get("tube"), a.offsets(1).get("tube"));
});

test("seeded generator and spectrum are reproducible", () => {
  const r1 = rng(7), r2 = rng(7);
  for (let i = 0; i < 100; i++) assert.equal(r1(), r2());
  const fs = 20, n = 256;
  const x = Array.from({ length: n }, (_, i) => Math.sin(2 * Math.PI * 2.5 * (i / fs)));
  const spec = amplitudeSpectrum(x, fs);
  const peak = spec.reduce((m, s) => (s.amplitude > m.amplitude ? s : m));
  assert.ok(Math.abs(peak.hz - 2.5) < fs / n + 1e-9, `peak at ${peak.hz}`);
  assert.deepEqual(ema([1, NaN, 3], 0.5).map(String), ["1", "NaN", "2"]);
  assert.ok(Math.abs(emaTimeConstant(0.5, 0.05) - 0.0721) < 1e-3);
});
