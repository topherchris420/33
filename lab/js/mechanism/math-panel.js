// The mathematics behind C1 at three depths: introduction, engineering, research.
import { h, depthTabs } from "../core/dom.js";
import { repoLink } from "../core/data.js";
import { eq } from "../core/tex.js";
import { diagonal, BASELINE } from "../core/math/fourbar.js";

function block(title, tex, note) {
  return h("div", { class: "mx-eq" }, h("h5", {}, title), eq(tex), note ? h("p", {}, note) : null);
}

export function buildMathPanel(root, { ev, sweep }) {
  const { ground: a, input: b, coupler: c, output: d } = BASELINE;
  const f0 = diagonal(a, b, 0), f92 = diagonal(a, b, 92);
  const cosMu0 = (c * c + d * d - f0 * f0) / (2 * c * d);
  const cosMu92 = (c * c + d * d - f92 * f92) / (2 * c * d);
  const claim = ev.claims.find((x) => x.id === "C1");
  const art = Object.fromEntries(ev.artifacts.map((x) => [x.id, x]));

  depthTabs(root, [
    {
      label: "Introduction",
      content: (p) => p.append(
        h("p", { class: "lede" }, "A four-bar linkage is a closed chain: a fixed ground link, an input link you drive, an output link that should swing the fin, and a coupler joining their free ends."),
        h("p", {}, "For the chain to exist at all, the coupler's free pin and the output link's free pin must be the same point. That point has to sit at exactly the coupler's length from one joint and exactly the output link's length from another. Draw a circle for each requirement: the linkage can only be assembled where the two circles cross."),
        h("p", {}, `With the recorded lengths, the coupler is so long (${c} mm) and the output so short (${d} mm) that the output's circle always lies entirely inside the coupler's circle. The circles never cross, at any drive angle. Pushing harder cannot help — clay or steel, the geometry has no solution.`),
        h("p", {}, "That is a valuable result. It tells a reviewer that either the dimensions were recorded wrongly or a different mechanism was intended — and it does so before anything is printed."),
      ),
    },
    {
      label: "Engineering",
      content: (p) => {
        p.append(
          h("div", { class: "mx-eq-grid" },
            h("div", {},
              block("1 · Vector loop closure", String.raw`\vec r_{AB} + \vec r_{BC} + \vec r_{CD} + \vec r_{DA} = \vec 0`, "A planar pin-jointed loop exists only if its link vectors sum to zero."),
              block("2 · Complex (Raven) form", String.raw`b\,e^{i\theta_2} + c\,e^{i\theta_3} - d\,e^{i\theta_4} - a = 0`, "Two real equations in the two unknown angles θ₃, θ₄ for a given drive angle θ₂."),
              block("3 · Loop diagonal", String.raw`f(\theta_2) = \lvert \vec r_{BD} \rvert = \sqrt{a^2 + b^2 - 2ab\cos\theta_2}`, `Baseline: f(0°) = ${f0.toFixed(2)} mm, f(92°) = ${f92.toFixed(2)} mm, f(180°) = a + b = ${a + b} mm.`),
              block("4 · Closure condition", String.raw`\lvert c - d \rvert \;\le\; f(\theta_2) \;\le\; c + d`, `Triangle inequality on B–C–D. Baseline needs ${Math.abs(c - d)} ≤ f ≤ ${c + d} mm; f never exceeds ${(a + b).toFixed(0)} mm.`)),
            h("div", {},
              block("5 · Closure residual", String.raw`\varepsilon(\theta_2) = \min_{\theta_3,\,\theta_4} \Bigl\lvert \textstyle\sum_i \vec r_i \Bigr\rvert = \max\bigl(0,\ \lvert c-d\rvert - f,\ f-(c+d)\bigr)`, `The gap between the two circles. Baseline: ε(0°) = ${(Math.abs(c - d) - f0).toFixed(2)} mm, ε(92°) = ${(Math.abs(c - d) - f92).toFixed(2)} mm.`),
              block("6 · Transmission angle", String.raw`\cos\mu = \frac{c^2 + d^2 - f^2}{2cd}`, `Baseline: cos μ = ${cosMu0.toFixed(3)} at 0° and ${cosMu92.toFixed(3)} at 92° — greater than 1, so no real μ exists. That is why R-C1-TRANSMISSION is NOT EVALUABLE rather than satisfied or failed.`),
              block("7 · Grashof criterion", String.raw`s + l \;\le\; p + q`, `s, l: shortest and longest links; p, q: the other two. Baseline: ${Math.min(a, b, c, d)} + ${Math.max(a, b, c, d)} = ${Math.min(a, b, c, d) + Math.max(a, b, c, d)} > ${a + b + c + d - Math.min(a, b, c, d) - Math.max(a, b, c, d)} → ${sweep.baseline.grashof} (no link can rotate fully). Grashof says nothing about whether the loop closes at a given angle.`))),
          h("h4", {}, "Variables"),
          h("dl", { class: "vars" },
            h("dt", {}, "a"), h("dd", {}, "ground link A–D, pin-centre distance (mm)"),
            h("dt", {}, "b"), h("dd", {}, "input link A–B (mm)"),
            h("dt", {}, "c"), h("dd", {}, "coupler B–C (mm)"),
            h("dt", {}, "d"), h("dd", {}, "output link D–C (mm)"),
            h("dt", {}, "θ₂"), h("dd", {}, "drive angle of the input link, measured from the folded position (deg)"),
            h("dt", {}, "θ₃, θ₄"), h("dd", {}, "absolute angles of the coupler and output link (deg)"),
            h("dt", {}, "f"), h("dd", {}, "loop diagonal |BD| (mm)"),
            h("dt", {}, "ε"), h("dd", {}, "closure residual: how far the loop is from closing (mm); 0 means it closes"),
            h("dt", {}, "μ"), h("dd", {}, "transmission angle between coupler and output link (deg), defined only for closed poses"),
            h("dt", {}, "s, l, p, q"), h("dd", {}, "shortest, longest, and remaining link lengths (mm)")),
          h("h4", {}, "Assumptions (claim C1)"),
          h("ul", {}, claim.assumptions.map((x) => h("li", {}, x))),
        );
      },
    },
    {
      label: "Research",
      content: (p) => {
        const files = ["four_bar_source", "four_bar_data", "four_bar_tests", "c1_closure_figure", "four_bar_step", "four_bar_cad_script"].map((id) => art[id]).filter(Boolean);
        p.append(
          h("p", {}, "Every value on this page traces to these committed files. Digests are the evidence record's SHA-256 (first 12 characters shown)."),
          h("div", { class: "mx-files" }, files.map((x) => h("a", { href: repoLink(x.path) },
            h("span", { class: "src" }, x.path), h("span", { class: "label" }, x.class_label),
            h("span", { class: "muted" }, x.description), h("span", { class: "hash" }, `sha256 ${x.sha256.slice(0, 12)}…`)))),
          h("h4", { style: { marginTop: "18px" } }, "Committed sweep metadata"),
          h("dl", { class: "kv" },
            h("dt", {}, "schema"), h("dd", { class: "mono" }, sweep.schema),
            h("dt", {}, "generator"), h("dd", { class: "mono" }, sweep.generator),
            h("dt", {}, "drive range"), h("dd", { class: "mono" }, `${sweep.drive_range_deg[0]}–${sweep.drive_range_deg[1]}° in ${sweep.drive_step_deg}° steps (${sweep.baseline.poses_evaluated} poses)`),
            h("dt", {}, "null means"), h("dd", {}, sweep.null_means),
            h("dt", {}, "not modeled"), h("dd", {}, h("ul", { class: "mb0" }, sweep.not_modeled.map((x) => h("li", {}, x)))),
            h("dt", {}, "reproduce"), h("dd", { class: "mono" }, "python mechanism/four_bar.py --emit docs/EVIDENCE/C1_four_bar_sweep.json"),
            h("dt", {}, "this page's port"), h("dd", {}, h("a", { href: repoLink("lab/js/core/math/fourbar.js") }, "lab/js/core/math/fourbar.js"), " — checked row-for-row against the committed sweep and against the Python model on closing configurations by ", h("a", { href: repoLink("tests/lab_math.test.mjs") }, "tests/lab_math.test.mjs"), ".")),
          h("h4", { style: { marginTop: "18px" } }, "Limitations (claim C1)"),
          h("ul", {}, claim.limitations.map((x) => h("li", {}, x))),
          h("h4", {}, "Measurement needed to close the next gate"),
          h("ul", {}, claim.measurement_needed.map((x) => h("li", {}, x))),
          h("p", { class: "muted" }, "Failure archive: model revision 1 returned 90° for poses that cannot close and its tests passed on those placeholders (D-003, resolved). Revision 2 reports null — no value exists."),
        );
      },
    },
  ], 1);
}
