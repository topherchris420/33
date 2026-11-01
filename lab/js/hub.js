// Laboratory hub: category legend and live record counts from the evaluated evidence record.
import { mountShell } from "./core/shell.js";
import { h, $, clear } from "./core/dom.js";
import { lab } from "./core/data.js";
import { CATEGORIES, categoryBadge } from "./core/taxonomy.js";

mountShell();

clear($("#cats"), ["historical", "research", "conceptual"].map((k) =>
  h("div", { class: "panel ticked" }, categoryBadge(k), h("p", { class: "muted" }, CATEGORIES[k].text))));

lab.evidence().then((ev) => {
  const c = ev.counts;
  $("#hub-record").textContent = `${c.claims} claims · ${c.claim_status.contradicted || 0} contradicted · ${c.claim_status.open || 0} unresolved · ${c.accepted_physical_measurements} accepted physical measurements`;
  const items = [
    [c.claims, "claims in the ledger"],
    [c.claim_status.contradicted || 0, "contradicted by their own models"],
    [c.claim_status.open || 0, "unresolved"],
    [c.claim_status.supported_within_limits || 0, "supported within stated limits"],
    [c.accepted_physical_measurements, "accepted physical measurements", true],
    [`${c.discrepancies_open}/${c.discrepancies_total}`, "discrepancies open"],
    [`${c.predictions_not_measured}/${c.predictions_total}`, "predictions not yet measured"],
  ];
  clear($("#counts"), items.map(([v, label, zero]) => h("div", { class: zero ? "zero" : "" }, h("b", {}, String(v)), h("span", { class: "label" }, label))));
}).catch(() => { $("#hub-record").textContent = "evidence record unavailable"; });
