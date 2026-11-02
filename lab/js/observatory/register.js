// Tables and lists: the accessible claim table, the discrepancy register, and the record's
// own grounded questions. Nothing here is generated prose; answers come from the record.
import { h, clear } from "../core/dom.js";
import { statusChip } from "../core/taxonomy.js";
import { discrepancyCard, resultChip, linkIds, boundText } from "./passport.js";

export function claimTable(ev, onPick) {
  return h("table", { class: "data claim-table" },
    h("caption", { class: "sr-only" }, "All claims with status, support, gate, requirements, and open discrepancies"),
    h("thead", {}, h("tr", {}, ["Claim", "Subject", "Status", "Strongest accepted evidence", "Gate reached", "Requirements", "Open discrepancies"].map((t) => h("th", { scope: "col" }, t)))),
    h("tbody", {}, ev.claims.map((c) => h("tr", {},
      h("th", { scope: "row" }, h("button", { class: "linkish mono", type: "button", onclick: () => onPick(c.id) }, c.id)),
      h("td", {}, c.title),
      h("td", {}, statusChip(c.status, c.status_label)),
      h("td", { class: "mono small" }, c.support_label),
      h("td", { class: "mono small" }, c.gate_label),
      h("td", {}, h("div", { class: "req-list" }, c.requirement_results.map((r) => h("span", { title: r.id }, resultChip(r.label, r.result))))),
      h("td", { class: "mono small" }, c.discrepancies_open.join(", ") || "none")))));
}

export function discrepancyRegister(container, ev, onId) {
  const kinds = [...new Set(ev.discrepancies.map((d) => d.kind))].sort();
  let status = "open", kind = "all";
  const listEl = h("div", { class: "disc-list" });
  const count = h("span", { class: "readout", "aria-live": "polite" });
  const statusSeg = h("div", { class: "seg", role: "group", "aria-label": "Discrepancy status" },
    [["open", "Open"], ["resolved", "Resolved"], ["all", "All"]].map(([k, label]) => {
      const b = h("button", { class: "btn", type: "button", "aria-pressed": String(k === status), "data-status": k }, label);
      b.addEventListener("click", () => { status = k; [...statusSeg.children].forEach((x) => x.setAttribute("aria-pressed", String(x === b))); render(); });
      return b;
    }));
  const kindSel = h("select", { "aria-label": "Discrepancy kind" }, h("option", { value: "all" }, "All kinds"), kinds.map((k) => h("option", { value: k }, k.replace(/_/g, " "))));
  kindSel.addEventListener("change", () => { kind = kindSel.value; render(); });
  function render() {
    const items = ev.discrepancies.filter((d) => (status === "all" || (status === "open" ? d.status === "open" : d.status !== "open")) && (kind === "all" || d.kind === kind));
    count.textContent = `${items.length} of ${ev.discrepancies.length}`;
    clear(listEl, items.length ? items.map((d) => {
      const det = h("details", { class: `disc-item ${d.status === "open" ? "is-open" : ""}`, id: `reg-${d.id}` },
        h("summary", {},
          h("span", { class: `tri-mini ${d.status === "open" ? "open" : ""}`, "aria-hidden": "true" }),
          h("b", { class: "mono" }, d.id), h("span", { class: "disc-title" }, d.title),
          h("span", { class: "faint small mono" }, d.claims.join(" ") || "—")),
        discrepancyCard(d, ev, { onId }));
      return det;
    }) : h("p", { class: "faint" }, "No discrepancies match."));
  }
  container.append(h("div", { class: "cluster reg-controls" }, statusSeg, kindSel, count), listEl);
  render();
  return {
    open(id) {
      const d = ev.discrepancies.find((x) => x.id === id);
      if (!d) return;
      if (status !== "all" && (d.status === "open") !== (status === "open")) statusSeg.querySelector('[data-status="all"]').click();
      if (kind !== "all" && kind !== d.kind) { kindSel.value = "all"; kind = "all"; render(); }
      const det = listEl.querySelector(`#reg-${id}`);
      if (det) { det.open = true; det.scrollIntoView({ block: "center" }); }
    },
  };
}

function cell(value, onId, key, row, ev) {
  if (value === null || value === undefined) return h("span", { class: "faint" }, "—");
  if (key === "bound") return boundText(value, row?.unit);
  if (key === "result" && ev) {
    const k = Object.entries(ev.vocabulary.requirement_results).find(([, label]) => label === value)?.[0];
    return k ? resultChip(value, k) : String(value);
  }
  if (key === "status" && ev) {
    const k = Object.entries(ev.vocabulary.claim_statuses).find(([, v]) => v[0] === value)?.[0];
    return k ? statusChip(k, value) : String(value);
  }
  if (Array.isArray(value)) return value.map((v, i) => [i ? h("span", { class: "sep" }, " · ") : "", typeof v === "string" ? linkIds(v, onId) : JSON.stringify(v)]);
  if (typeof value === "object") return JSON.stringify(value);
  return typeof value === "string" ? linkIds(value, onId) : String(value);
}

export function groundedQuestions(container, ev, onId) {
  for (const q of ev.questions) {
    let body;
    const a = q.answer;
    if (Array.isArray(a) && a.every((x) => typeof x === "string")) {
      body = a.length ? (a.every((x) => /^C\d$/.test(x)) ? h("div", { class: "cluster" }, a.map((x) => h("a", { href: `#${x}`, class: "idchip", onclick: (e) => { e.preventDefault(); onId(x); } }, x)))
        : h("ul", { class: "plist" }, a.map((x) => h("li", {}, linkIds(x, onId))))) : h("p", { class: "faint" }, "None.");
    } else if (Array.isArray(a) && new Set(a.map((x) => Object.keys(x).join("|"))).size > 1) {
      // Heterogeneous rows (requirements mixed with discrepancies or predictions): one line per record.
      const ID_KEYS = ["requirement", "prediction", "discrepancy", "preregistration", "claim"];
      body = h("ul", { class: "qa-rows" }, a.map((row) => {
        const key = ID_KEYS.find((k) => k in row);
        const rest = Object.entries(row).filter(([k]) => k !== key);
        return h("li", {},
          h("span", { class: "qa-key" }, h("span", { class: "qa-kind" }, key), h("a", { href: `#${row[key]}`, class: "idlink", onclick: (e) => { e.preventDefault(); onId(row[key]); } }, row[key])),
          h("span", {}, rest.map(([, v], i) => [i ? " · " : "", cell(v, onId)])));
      }));
    } else if (Array.isArray(a)) {
      const keys = [...new Set(a.flatMap((x) => Object.keys(x)))];
      body = a.length ? h("div", { class: "table-scroll" }, h("table", { class: "data" }, h("thead", {}, h("tr", {}, keys.map((k) => h("th", {}, k.replace(/_/g, " "))))),
        h("tbody", {}, a.map((row) => h("tr", {}, keys.map((k) => h("td", { class: k === "requirement" || k === "claim" || k === "prediction" || k === "preregistration" ? "mono" : "" }, cell(row[k], onId, k, row, ev)))))))) : h("p", { class: "faint" }, "None.");
    } else if (a && typeof a === "object") {
      const entries = Object.entries(a);
      body = h("details", { class: "qa-details" }, h("summary", {}, `${entries.length} files — expand`),
        h("div", { class: "table-scroll" }, h("table", { class: "data" }, h("thead", {}, h("tr", {}, h("th", {}, "file"), h("th", {}, "claims whose review it would make insufficient"))),
          h("tbody", {}, entries.map(([path, claims]) => h("tr", {}, h("td", { class: "mono small" }, path), h("td", {}, cell(claims, onId))))))));
    } else body = h("p", {}, String(a));
    container.append(h("article", { class: "panel qa" }, h("div", { class: "panel-head" }, h("h4", {}, q.question), h("span", { class: "faint small mono" }, q.id)), h("div", { class: "panel-body" }, body)));
  }
}
