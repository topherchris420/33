// Evidence passports and node detail panels. Every label is the record's own vocabulary.
import { h } from "../core/dom.js";
import { statusChip, notMeasured, EVIDENCE_CLASS_COLORS, categoryBadge } from "../core/taxonomy.js";
import { claimLink, discrepancyLink, repoLink, docLink } from "../core/data.js";

export function boundText(bound, unit) {
  if (!bound) return h("span", { class: "faint" }, "none stated");
  const u = unit && unit !== "boolean" ? ` ${unit}` : "";
  const parts = [];
  if ("equals" in bound) parts.push(`= ${bound.equals}`);
  if ("min" in bound) parts.push(`≥ ${bound.min}`);
  if ("max" in bound) parts.push(`≤ ${bound.max}`);
  return h("span", { class: "num" }, parts.join(" and ") + u);
}

export function observedText(r) {
  if (r.result === "not_measured") return notMeasured();
  if (r.observed === null || r.observed === undefined) {
    if (r.result === "requires_human_review") return h("span", { class: "faint" }, "needs engineering judgement");
    if (r.result === "not_evaluated") return h("span", { class: "faint" }, "not evaluated in this build");
    return h("span", { class: "faint", title: "Null means no value exists; it is never zero." }, "no value exists");
  }
  const vals = Array.isArray(r.observed) ? r.observed : [r.observed];
  return h("span", { class: "num" }, vals.map(String).join(" – ") + (r.unit && r.unit !== "boolean" ? ` ${r.unit}` : ""));
}

export function resultChip(label, result) {
  return h("span", { class: `result result-${result}` }, label);
}

function classChip(cls, label) {
  if (!cls) return h("span", { class: "faint" }, "—");
  return h("span", { class: "evc", style: `--c:${EVIDENCE_CLASS_COLORS[cls] || "#8fa2ad"}` }, label || cls.replace(/_/g, " ").toUpperCase());
}

function list(items, empty = "None recorded.") {
  if (!items || !items.length) return h("p", { class: "faint" }, empty);
  return h("ul", { class: "plist" }, items.map((x) => h("li", {}, x)));
}

function section(title, ...body) {
  return h("section", { class: "pp-sec" }, h("h4", {}, title), ...body);
}

/** Linkify record IDs (D-002, R-C1-CLOSURE, C3, P-001) inside prose. */
export function linkIds(text, onId) {
  const out = [];
  // "C6-5" is a motor designation, not claim C6: claim IDs must not continue with "-" or a word character.
  const re = /\b(D-\d{3}|R-C\d-[A-Z-]+[A-Z]|PRED-C\d-[A-Z-]+[A-Z]|P-\d{3}|C\d(?![\w-]))(?![\w])/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const id = m[1];
    out.push(h("a", { href: `#${id}`, class: "idlink", onclick: (e) => { if (onId) { e.preventDefault(); onId(id); } } }, id));
    last = m.index + id.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function passport(c, ev, { onId } = {}) {
  const art = new Map(ev.artifacts.map((a) => [a.id, a]));
  const req = new Map(ev.requirements.map((r) => [r.id, r]));
  const pred = new Map(ev.predictions.map((p) => [p.id, p]));
  const pre = new Map(ev.preregistrations.map((p) => [p.id, p]));
  const disc = new Map(ev.discrepancies.map((d) => [d.id, d]));
  const review = ev.reviews[c.id]?.current;
  const human = review?.kind === "human";

  const head = h("header", { class: "pp-head" },
    h("div", { class: "pp-id" },
      h("span", { class: "pp-num" }, c.id),
      h("div", {}, h("p", { class: "eyebrow" }, "Evidence passport"), h("h3", { id: `pp-title-${c.id}` }, c.title))),
    h("div", { class: "cluster" }, statusChip(c.status, c.status_label), categoryBadge("research")));

  const summary = h("dl", { class: "kv pp-kv" },
    h("dt", {}, "Status"), h("dd", {}, statusChip(c.status, c.status_label), h("div", { class: "muted small" }, c.status_meaning)),
    h("dt", {}, "Strongest accepted evidence"), h("dd", {}, h("b", { class: "support" }, c.support_label),
      c.has_accepted_physical_evidence ? null : h("div", { class: "muted small" }, "No accepted physical evidence. Software and models are not physical performance.")),
    h("dt", {}, "Evidence classes cited"), h("dd", { class: "cluster" }, c.evidence_classes.map((k) => classChip(k, ev.vocabulary.evidence_classes[k]?.label))),
    h("dt", {}, "Gate reached"), h("dd", {}, h("span", { class: "mono" }, c.gate_label), nextGate(c, ev)),
    h("dt", {}, "Last review"), h("dd", {},
      h("span", { class: `review-chip ${human ? "review-human" : "review-snapshot"}` }, c.freshness_label),
      " ", h("span", { class: human ? "" : "warnish" }, human ? `human review by ${review.recorded_by}` : "NO HUMAN REVIEW — tooling snapshot only"),
      review ? h("div", { class: "muted small" }, `${review.recorded} · ${review.recorded_by}${review.note ? ` — ${review.note}` : ""}`) : null));

  const reqTable = h("div", { class: "pp-reqs" }, c.requirements.map((rid) => {
    const r = req.get(rid);
    return h("div", { class: `pp-req pp-req-${r.result}`, id: `pp-${rid}` },
      h("div", { class: "field-row" }, h("b", { class: "mono" }, rid), h("span", {}, resultChip(r.label, r.result), r.evidence_class ? h("span", { class: "faint small" }, ` (${r.evidence_class})`) : null)),
      h("p", { class: "small" }, r.text),
      h("dl", { class: "pp-req-vals" },
        h("dt", {}, "bound"), h("dd", {}, boundText(r.bound, r.unit)),
        h("dt", {}, "observed"), h("dd", {}, observedText(r)),
        h("dt", {}, "check"), h("dd", { class: "faint" }, r.check.replace(/_/g, " "))));
  }));

  const predictions = c.predictions.length ? h("div", { class: "stack" }, c.predictions.map((pid) => {
    const p = pred.get(pid);
    return h("div", { class: "pp-card" },
      h("div", { class: "field-row" }, h("b", { class: "mono" }, pid), resultChip(p.result_label, p.result)),
      h("p", { class: "small" }, `${p.quantity} — `, h("span", { class: "num" }, `predicted ${p.predicted} ${p.unit}`), p.model_uncertainty === null ? h("span", { class: "faint" }, " (no model uncertainty stated)") : ` ± ${p.model_uncertainty}`),
      h("p", { class: "faint small" }, `Measured: `, notMeasured(), ` · Basis: ${p.basis}`));
  })) : h("p", { class: "faint" }, "No registered predictions for this claim.");

  const prereg = c.preregistrations.length ? h("div", { class: "stack" }, c.preregistrations.map((pid) => {
    const p = pre.get(pid);
    return h("div", { class: "pp-card" },
      h("div", { class: "field-row" }, h("b", { class: "mono" }, `${pid} · ${p.title}`), h("span", { class: "prereg-chip" }, p.status.toUpperCase())),
      h("p", { class: "small" }, p.question),
      h("p", { class: "faint small" }, `Proposed by ${p.proposed_by}. Registered by: ${p.registered_by || "nobody yet — only a human can register"}.`));
  })) : h("p", { class: "faint" }, "None.");

  const discs = [...c.discrepancies_open, ...c.discrepancies_resolved].map((id) => disc.get(id));
  const discList = discs.length ? h("div", { class: "stack" }, discs.map((d) => discrepancyCard(d, ev, { compact: true, onId }))) : h("p", { class: "faint" }, "None recorded.");

  const artTable = h("table", { class: "data pp-table pp-art" },
    h("thead", {}, h("tr", {}, h("th", {}, "Artifact"), h("th", {}, "Class"), h("th", {}, "SHA-256"), h("th", {}, "Status"))),
    h("tbody", {}, [...c.evidence.map((id) => [id, false]), ...c.historical.map((id) => [id, true])].map(([id, hist]) => {
      const a = art.get(id);
      return h("tr", { class: hist ? "hist" : "" },
        h("td", {}, h("a", { href: repoLink(a.path), class: "mono small", target: "_blank", rel: "noopener" }, a.path), h("div", { class: "faint small" }, a.description)),
        h("td", {}, classChip(a.class, a.class_label)),
        h("td", {}, h("span", { class: "hash" }, a.sha256.slice(0, 12))),
        h("td", {}, h("span", { class: a.status === "superseded" ? "warnish small mono" : "small mono" }, a.status.toUpperCase()), hist ? h("div", { class: "faint small" }, "failure archive") : null));
    })));

  return h("article", { class: "passport", "aria-labelledby": `pp-title-${c.id}` },
    head,
    h("p", { class: "pp-q" }, h("span", { class: "label" }, "Question "), c.question),
    h("blockquote", { class: "pp-statement" }, h("span", { class: "label" }, "Current statement and scope"), h("p", {}, linkIds(c.statement, onId))),
    summary,
    section("Requirements", reqTable),
    section("Predictions", predictions),
    section("Discrepancies", discList),
    section("Pre-registered experiments", prereg),
    h("div", { class: "grid-2 pp-two" },
      section("Assumptions", list(c.assumptions)),
      section("Limitations", list(c.limitations))),
    section("Open questions", list(c.concerns.map((x) => h("span", {}, linkIds(x, onId))))),
    section("Missing validation",
      h("p", { class: "label" }, "Measurement needed to close the next gate"), list(c.measurement_needed),
      h("p", { class: "label" }, "What this claim does not establish"), list(c.not_established)),
    section("Provenance", artTable,
      h("p", { class: "faint small" }, "A digest detects change against a trusted reference; it is not a signature. A change to any cited file makes the last review insufficient without making the claim false.")),
    h("footer", { class: "pp-foot cluster" },
      h("a", { class: "btn", href: claimLink(c.id) }, "Generated passport ↗"),
      h("a", { class: "btn ghost", href: docLink("docs/TRACEABILITY.md") }, "Traceability ↗")));
}

function nextGate(c, ev) {
  const gates = ev.vocabulary.gates;
  const i = gates.findIndex(([k]) => k === c.gate);
  const next = gates[i + 1];
  return next ? h("div", { class: "muted small" }, `next: ${next[1]}`) : null;
}

export function discrepancyCard(d, ev, { compact = false, onId } = {}) {
  const kinds = ev.discrepancy_vocabulary.kinds;
  const open = d.status === "open";
  return h("div", { class: `pp-card disc ${open ? "disc-open" : "disc-resolved"}`, id: compact ? null : `disc-${d.id}` },
    h("div", { class: "field-row" },
      h("b", { class: "mono" }, h("a", { href: discrepancyLink(d.id) }, d.id), ` · ${d.title}`),
      h("span", { class: `disc-chip ${open ? "open" : ""}` }, ev.discrepancy_vocabulary.statuses[d.status] || d.status)),
    h("p", { class: "faint small" }, `${d.kind.replace(/_/g, " ")} — ${kinds[d.kind] || ""}`, d.claims.length ? h("span", {}, " · claims ", d.claims.map((c, i) => [i ? ", " : "", h("a", { href: `#${c}`, class: "idlink", onclick: (e) => { if (onId) { e.preventDefault(); onId(c); } } }, c)])) : " · no claim attributed"),
    compact ? null : h("div", { class: "sides" }, d.sides.map((side) => h("div", { class: "side" },
      h("span", { class: "label" }, side.artifact ? `artifact: ${side.artifact}` : side.path || "side"),
      h("p", { class: "small" }, `“${side.says}”`)))),
    h("p", { class: "small" }, h("span", { class: "label" }, open ? "Next action " : "Resolution "), open ? d.next_action : (d.resolution || "—")),
    !compact && d.found_by ? h("p", { class: "faint small" }, `Found by: ${d.found_by}`) : null);
}

/** Detail panel for a non-claim node. */
export function nodeDetail(n, ev, { onId } = {}) {
  const d = n.data || {};
  const wrap = (title, ...body) => h("article", { class: "passport node-detail" },
    h("header", { class: "pp-head" }, h("div", {}, h("p", { class: "eyebrow" }, title), h("h3", { class: n.type === "core" ? "" : "mono" }, n.type === "artifact" ? d.id : n.type === "core" ? "The empty centre" : n.id)), categoryBadge("research")), ...body);
  const claimsLine = n.claims?.size ? h("p", { class: "small" }, "Linked claims: ", [...n.claims].map((c, i) => [i ? ", " : "", h("a", { href: `#${c}`, class: "idlink", onclick: (e) => { e.preventDefault(); onId?.(c); } }, c)])) : null;
  switch (n.type) {
    case "requirement":
      return wrap("Requirement", h("p", {}, d.text), h("dl", { class: "kv" },
        h("dt", {}, "Bound"), h("dd", {}, boundText(d.bound, d.unit)), h("dt", {}, "Observed"), h("dd", {}, observedText(d)),
        h("dt", {}, "Result"), h("dd", {}, resultChip(d.label, d.result), d.evidence_class ? ` (${d.evidence_class})` : ""),
        h("dt", {}, "Check"), h("dd", {}, d.check_label), h("dt", {}, "Source"), h("dd", {}, d.source),
        d.reason ? [h("dt", {}, "Reason"), h("dd", {}, d.reason)] : null), claimsLine);
    case "prediction":
      return wrap("Registered prediction", h("p", {}, d.quantity), h("dl", { class: "kv" },
        h("dt", {}, "Predicted"), h("dd", { class: "num" }, `${d.predicted} ${d.unit}`), h("dt", {}, "Measured"), h("dd", {}, notMeasured()),
        h("dt", {}, "Result"), h("dd", {}, resultChip(d.result_label, d.result)), h("dt", {}, "Condition"), h("dd", {}, d.condition),
        h("dt", {}, "Method"), h("dd", {}, d.measurement_method), h("dt", {}, "Registered"), h("dd", {}, d.registered)),
        h("p", { class: "faint small" }, "A prediction's value is frozen at registration. Unknown is not zero."), claimsLine);
    case "preregistration":
      return wrap("Pre-registration (drafted)", h("p", {}, h("b", {}, d.title)), h("p", {}, d.question), h("p", { class: "small" }, d.prediction),
        h("dl", { class: "kv" }, h("dt", {}, "Status"), h("dd", {}, d.status.toUpperCase()), h("dt", {}, "Proposed by"), h("dd", {}, d.proposed_by),
          h("dt", {}, "Registered by"), h("dd", {}, d.registered_by || "nobody — only a human can register"), h("dt", {}, "Interpretation"), h("dd", {}, d.interpretation_rule),
          h("dt", {}, "Safety"), h("dd", {}, d.safety)), claimsLine);
    case "discrepancy":
      return wrap("Discrepancy", discrepancyCard(d, ev, { onId }));
    case "artifact":
      return wrap(`Artifact · ${d.class_label}`, h("p", {}, h("a", { href: repoLink(d.path), target: "_blank", rel: "noopener", class: "mono" }, d.path)),
        h("p", { class: "small" }, d.description),
        h("dl", { class: "kv" }, h("dt", {}, "Evidence class"), h("dd", {}, classChip(d.class, d.class_label), h("div", { class: "faint small" }, ev.vocabulary.evidence_classes[d.class]?.meaning)),
          h("dt", {}, "Status"), h("dd", {}, d.status.toUpperCase()), h("dt", {}, "SHA-256"), h("dd", {}, h("span", { class: "hash" }, d.sha256)),
          h("dt", {}, "Bytes"), h("dd", { class: "num" }, String(d.bytes ?? "—")),
          d.derived_from?.length ? [h("dt", {}, "Derived from"), h("dd", { class: "mono small" }, d.derived_from.join(", "))] : null), claimsLine);
    case "review": {
      const human = d.kind === "human";
      return wrap(`Review of ${d.claim}`, h("dl", { class: "kv" },
        h("dt", {}, "Freshness"), h("dd", {}, d.freshness_label), h("dt", {}, "Kind"), h("dd", { class: human ? "" : "warnish" }, human ? "Human engineering review" : "Tooling snapshot — not an engineering review"),
        h("dt", {}, "Recorded"), h("dd", {}, `${d.recorded || "—"} by ${d.recorded_by || "—"}`), d.note ? [h("dt", {}, "Note"), h("dd", {}, d.note)] : null), claimsLine);
    }
    case "core":
      return wrap("Accepted inert physical measurements", h("p", { class: "core-detail-num" }, String(d.count)),
        h("p", {}, "No inert physical measurement has been accepted into the record. Each dashed line in the constellation is a requirement or a registered prediction that can only be closed here — by a measurement with a named instrument, method, and uncertainty, accepted by a named human."),
        h("p", { class: "faint small" }, "Automated tools, including this page, cannot create, accept, or relabel a measurement."));
    default:
      return wrap(n.type, h("pre", {}, JSON.stringify(d, null, 1)));
  }
}
