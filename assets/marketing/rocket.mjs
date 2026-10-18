import {
  TAU,
  transform,
  resample,
  evaluate,
  chain,
  clamp,
  smooth,
} from "./fourier.mjs";

export const DURATION = 32;
export const CHAPTERS = [
  {
    start: 0,
    name: "The idea",
    title: "Every possibility\nbegins with a line.",
    detail: "01 / FOURIER CONSTRUCTION",
  },
  {
    start: 9,
    name: "The assembly",
    title: "A system.\nTaking shape.",
    detail: "02 / EXPLODED ASSEMBLY",
  },
  {
    start: 21,
    name: "The perspective",
    title: "Built to question.\nDesigned to learn.",
    detail: "03 / PROJECT 33",
  },
];

const circle = (r) =>
  Array.from({ length: 96 }, (_, i) => [
    Math.cos((i * TAU) / 96) * r,
    Math.sin((i * TAU) / 96) * r,
  ]);
const contours = [];
function add(points, map, group, kind = "line") {
  const coefficients = transform(resample(points, 128)).slice(0, 45);
  contours.push({
    coefficients,
    map,
    group,
    kind,
    path: Array.from({ length: 161 }, (_, i) =>
      map(evaluate(coefficients, i / 160)),
    ),
  });
}

// Deliberately illustrative geometry in normalized scene units. No CAD dimensions.
for (const y of [-2.9, -2.5, -1.95, -1.2, -0.45, 0.3, 1.05, 1.8, 2.55]) {
  add(circle(0.34), ([x, z]) => [x, y, z], y > 1.8 ? 1 : 0, "ring");
}
for (let i = 0; i < 12; i++) {
  const a = (i * TAU) / 12;
  add(
    [
      [-2.9, 0.34],
      [2.55, 0.34],
      [2.55, 0.33],
      [-2.9, 0.33],
    ],
    ([y, r]) => [Math.cos(a) * r, y, Math.sin(a) * r],
    0,
  );
}
const nose = [
  [0.34, 2.55],
  [0.33, 2.85],
  [0.28, 3.12],
  [0.18, 3.38],
  [0, 3.55],
  [-0.18, 3.38],
  [-0.28, 3.12],
  [-0.33, 2.85],
  [-0.34, 2.55],
];
for (let i = 0; i < 4; i++) {
  const a = (i * Math.PI) / 4;
  add(nose, ([r, y]) => [Math.cos(a) * r, y, Math.sin(a) * r], 1, "nose");
}
for (const [y, r] of [
  [2.85, 0.33],
  [3.12, 0.28],
  [3.38, 0.18],
])
  add(circle(r), ([x, z]) => [x, y, z], 1, "ring");
for (let i = 0; i < 4; i++) {
  const a = (i * TAU) / 4;
  const map = ([r, y]) => [Math.cos(a) * r, y, Math.sin(a) * r];
  add(
    [
      [0.34, -1.75],
      [1.23, -3.04],
      [1.06, -3.2],
      [0.34, -2.85],
    ],
    map,
    2 + i,
    "fin",
  );
  add(
    [
      [0.34, 1.34],
      [0.72, 1.23],
      [0.72, 0.64],
      [0.34, 0.73],
    ],
    map,
    6 + i,
    "canard",
  );
}
add(circle(0.25), ([x, z]) => [x, -3.12, z], 10, "ring");
add(circle(0.18), ([x, z]) => [x, -3.3, z], 10, "ring");
const silhouette = transform(
  resample(
    [
      [0, 3.55],
      [0.28, 3.12],
      [0.34, 2.55],
      [0.34, 1.34],
      [0.72, 1.23],
      [0.72, 0.64],
      [0.34, 0.73],
      [0.34, -1.75],
      [1.23, -3.04],
      [1.06, -3.2],
      [0.34, -2.85],
      [-0.34, -2.85],
      [-1.06, -3.2],
      [-1.23, -3.04],
      [-0.34, -1.75],
      [-0.34, 0.73],
      [-0.72, 0.64],
      [-0.72, 1.23],
      [-0.34, 1.34],
      [-0.34, 2.55],
      [-0.28, 3.12],
    ],
    256,
  ),
).slice(0, 65);

export class RocketFilm {
  constructor(canvas, { cinematic = false } = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.cinematic = cinematic;
    this.mode = "blueprint";
    this.time = 0;
    this.resize();
  }
  resize() {
    const box = this.canvas.getBoundingClientRect();
    this.width = box.width || 960;
    this.height = box.height || 540;
    const dpr = Math.min(globalThis.devicePixelRatio || 1, 2);
    this.canvas.width = Math.round(this.width * dpr);
    this.canvas.height = Math.round(this.height * dpr);
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.render(this.time);
  }
  render(seconds) {
    this.time = clamp(seconds, 0, DURATION);
    const { ctx: c, width: w, height: h } = this;
    const t = this.time,
      u = w / 1440;
    c.clearRect(0, 0, w, h);
    c.fillStyle = "#101b23";
    c.fillRect(0, 0, w, h);
    const glow = c.createRadialGradient(
      w * 0.57,
      h * 0.45,
      0,
      w * 0.57,
      h * 0.45,
      w * 0.7,
    );
    glow.addColorStop(0, "#153945");
    glow.addColorStop(1, "#10191f");
    c.fillStyle = glow;
    c.fillRect(0, 0, w, h);
    const grid = Math.max(23, w / 26);
    c.lineWidth = 0.65;
    for (let x = 0; x < w; x += grid) {
      c.strokeStyle = Math.round(x / grid) % 5 === 0 ? "#27424b" : "#1c3039";
      c.beginPath();
      c.moveTo(x, 0);
      c.lineTo(x, h);
      c.stroke();
    }
    for (let y = 0; y < h; y += grid) {
      c.strokeStyle = Math.round(y / grid) % 5 === 0 ? "#27424b" : "#1c3039";
      c.beginPath();
      c.moveTo(0, y);
      c.lineTo(w, y);
      c.stroke();
    }
    const cinematic = this.cinematic;
    const center = [w * (cinematic ? 0.68 : 0.52), h * 0.49];
    const scale = Math.min(h / 10.2, w / (cinematic ? 10.8 : 5.9));
    const yaw = -0.65 + smooth((t - 20) / 12) * 2.7;
    const tilt = cinematic ? -0.19 : -0.25;
    const project = ([x, y, z]) => {
      const rx = x * Math.cos(yaw) + z * Math.sin(yaw);
      const rz = -x * Math.sin(yaw) + z * Math.cos(yaw);
      const px = rx,
        py = y * 0.97 - rz * 0.25;
      return [
        center[0] + (px * Math.cos(tilt) - py * Math.sin(tilt)) * scale,
        center[1] - (px * Math.sin(tilt) + py * Math.cos(tilt)) * scale,
      ];
    };
    const explode = 1 - smooth((t - 12) / 9);
    const shift = (p, g) => {
      if (g === 1) return [p[0], p[1] + explode * 0.64, p[2]];
      if (g >= 2 && g <= 9) {
        const a = ((g - (g < 6 ? 2 : 6)) * TAU) / 4;
        return [
          p[0] + Math.cos(a) * explode * 0.65,
          p[1],
          p[2] + Math.sin(a) * explode * 0.65,
        ];
      }
      return [p[0], p[1] - (g === 10 ? explode * 0.5 : 0), p[2]];
    };
    const stroke = (points, color, width = 1, close = false) => {
      if (points.length < 2) return;
      c.strokeStyle = color;
      c.lineWidth = width;
      c.beginPath();
      points.forEach((p, i) => (i ? c.lineTo(...p) : c.moveTo(...p)));
      if (close) c.closePath();
      c.stroke();
    };
    // Construction axes and orbital reference ellipse.
    c.setLineDash([3, 7]);
    stroke([project([0, -4.5, 0]), project([0, 4.65, 0])], "#4a6b75");
    const orbit = Array.from({ length: 101 }, (_, i) =>
      project([
        Math.cos((i * TAU) / 100) * 2.6,
        -3.65,
        Math.sin((i * TAU) / 100) * 2.6,
      ]),
    );
    stroke(orbit, "#45626b");
    c.setLineDash([]);
    const reveal = clamp(t / 10) * contours.length;
    contours.forEach((part, i) => {
      const progress = clamp(reveal - i);
      const points = part.path
        .slice(0, Math.max(1, Math.ceil(progress * part.path.length)))
        .map((p) => project(shift(p, part.group)));
      // A quiet ghost drawing provides context while the Fourier tip draws.
      stroke(
        part.path.map((p) => project(shift(p, part.group))),
        "#30515e",
        0.65,
      );
      if (this.mode === "surface" && progress >= 1 && part.kind !== "line") {
        c.beginPath();
        points.forEach((p, j) => (j ? c.lineTo(...p) : c.moveTo(...p)));
        c.closePath();
        c.fillStyle = part.kind === "fin" ? "#315e68aa" : "#28475388";
        c.fill();
      }
      stroke(
        points,
        part.kind === "ring" ? "#73b2c2" : "#a7e8ed",
        part.kind === "fin" ? 1.6 : 1,
      );
    });
    // Actual coefficient vectors and epicycles, mapped from the contour plane to 3D.
    const part = {
      coefficients: silhouette,
      map: ([x, y]) => [x, y, 0],
      group: 0,
    };
    if (t < 10) {
      const progress = t / 10;
      const links = chain(part.coefficients, progress);
      const traceCount = Math.max(2, Math.ceil(progress * 300));
      const traced = Array.from({ length: traceCount }, (_, i) =>
        project(
          part.map(evaluate(silhouette, (progress * i) / (traceCount - 1))),
        ),
      );
      stroke(traced, "#def5ac", 1.8);
      part.coefficients.slice(0, 16).forEach((term, i) => {
        if (term.frequency === 0 || term.amplitude < 0.006) return;
        const origin = links[i];
        const ring = Array.from({ length: 49 }, (_, j) => {
          const a = (j * TAU) / 48;
          return project(
            shift(
              part.map([
                origin[0] + term.amplitude * Math.cos(a),
                origin[1] + term.amplitude * Math.sin(a),
              ]),
              part.group,
            ),
          );
        });
        stroke(ring, "#d8ef9a88", 0.8);
      });
      stroke(
        links.map((p) => project(shift(part.map(p), part.group))),
        "#e2f1a5",
        1.1,
      );
      const tip = project(
        shift(part.map(evaluate(part.coefficients, progress)), part.group),
      );
      c.fillStyle = "#e5f5ad";
      c.shadowColor = "#d7ff7c";
      c.shadowBlur = 14;
      c.beginPath();
      c.arc(...tip, 3, 0, TAU);
      c.fill();
      c.shadowBlur = 0;
    }
    const label = (text, x, y, color = "#7a9eaa", size = 10) => {
      c.fillStyle = color;
      c.font = `${size}px 'Courier New', monospace`;
      c.fillText(text, x, y);
    };
    const annotation = (text, world, dx, dy) => {
      const p = project(world);
      stroke(
        [
          p,
          [p[0] + dx * scale, p[1] + dy * scale],
          [p[0] + (dx + 0.65) * scale, p[1] + dy * scale],
        ],
        "#6a8d98",
        0.75,
      );
      c.fillStyle = "#b9d6da";
      c.beginPath();
      c.arc(...p, 2, 0, TAU);
      c.fill();
      label(
        text,
        p[0] + dx * scale,
        p[1] + dy * scale - 7,
        "#9cbcc5",
        Math.max(8, Math.min(11, w / 68)),
      );
    };
    if (t > 10) {
      annotation("PROFILE / 01", [0, 3.1 + explode * 0.64, 0], 0.9, -0.2);
      annotation("AIRFRAME / 02", [0.34, 0.15, 0], 1.1, -0.1);
      annotation("FIN ARRAY / 03", [0.8, -2.6, 0], 1.2, 0.4);
    }
    const pad = Math.max(22, w * 0.035);
    label(
      "V3D / DESIGN STUDY 033",
      pad,
      pad + 4,
      "#a5bec6",
      Math.max(9, w / 110),
    );
    label(
      "ILLUSTRATIVE GEOMETRY · NOT TO SCALE",
      pad,
      h - pad,
      "#7896a0",
      Math.max(8, w / 135),
    );
    label(
      `${String(Math.floor(t)).padStart(2, "0")}:${String(Math.floor((t % 1) * 24)).padStart(2, "0")} / 00:32`,
      w - pad - Math.max(115, w * 0.105),
      h - pad,
      "#b7ced2",
      Math.max(9, w / 120),
    );
    if (cinematic) {
      const chapter = [...CHAPTERS].reverse().find((ch) => t >= ch.start);
      const fade = smooth((t - chapter.start) / 0.8);
      c.save();
      c.globalAlpha = fade;
      label(chapter.detail, pad, h * 0.32, "#d0ed9b", Math.max(10, 14 * u));
      c.fillStyle = "#edf0e7";
      c.font = `500 ${Math.max(25, 59 * u)}px Arial, sans-serif`;
      chapter.title
        .split("\n")
        .forEach((line, i) =>
          c.fillText(line, pad, h * 0.42 + i * Math.max(32, 68 * u)),
        );
      label("VERS3DYNAMICS", pad, h * 0.72, "#9ab2ba", Math.max(9, 13 * u));
      label(
        "APPLIED AEROSPACE RESEARCH",
        pad,
        h * 0.72 + 22 * u,
        "#9ab2ba",
        Math.max(8, 11 * u),
      );
      label(
        "BENCH-VALIDATION PROTOTYPE",
        pad,
        h * 0.83,
        "#d0ed9b",
        Math.max(9, 12 * u),
      );
      c.restore();
    }
  }
}
