import test from "node:test";
import assert from "node:assert/strict";
import {
  TAU,
  resample,
  transform,
  evaluate,
} from "../assets/marketing/fourier.mjs";

test("DFT reconstructs a translated circle, including phase and DC offset", () => {
  const samples = Array.from({ length: 64 }, (_, j) => [
    2 + 3 * Math.cos((TAU * j) / 64 + 0.4),
    -1 + 3 * Math.sin((TAU * j) / 64 + 0.4),
  ]);
  const terms = transform(samples);
  for (let j = 0; j < samples.length; j++) {
    const p = evaluate(terms, j / samples.length);
    assert.ok(Math.hypot(p[0] - samples[j][0], p[1] - samples[j][1]) < 1e-10);
  }
  const fundamental = terms.find((t) => t.frequency === 1);
  assert.ok(Math.abs(fundamental.amplitude - 3) < 1e-12);
  assert.ok(Math.abs(fundamental.phase - 0.4) < 1e-12);
});

test("negative-frequency terms preserve clockwise traversal and close the loop", () => {
  const samples = Array.from({ length: 32 }, (_, j) => [
    Math.cos((TAU * j) / 32),
    -Math.sin((TAU * j) / 32),
  ]);
  const terms = transform(samples);
  assert.equal(terms[0].frequency, -1);
  const start = evaluate(terms, 0),
    end = evaluate(terms, 1);
  assert.ok(Math.hypot(start[0] - end[0], start[1] - end[1]) < 1e-12);
  assert.ok(evaluate(terms, 0.25)[1] < -0.99);
});

test("arc-length resampling includes the closing edge and handles duplicate vertices", () => {
  assert.deepEqual(
    resample(
      [
        [0, 0],
        [2, 0],
        [2, 0],
        [2, 2],
        [0, 2],
      ],
      8,
    ),
    [
      [0, 0],
      [1, 0],
      [2, 0],
      [2, 1],
      [2, 2],
      [1, 2],
      [0, 2],
      [0, 1],
    ],
  );
  assert.throws(
    () =>
      resample([
        [0, 0],
        [0, 0],
      ]),
    RangeError,
  );
  assert.throws(() => transform([]), RangeError);
});
