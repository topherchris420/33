// Shared page chrome: header with the four user modes, the lab sections, a live record
// chip, the category bar that names what kind of information is on screen, and a footer
// restating the safety boundary. Pages declare themselves with data attributes on <body>.
import { h, $ } from "./dom.js";
import { CATEGORIES, categoryBadge } from "./taxonomy.js";
import { lab, siteURL } from "./data.js";

const MODES = [
  { id: "cinematic", label: "Cinematic", href: "cinematic.html" },
  { id: "guided", label: "Guided Lab", href: "guided.html" },
  { id: "workbench", label: "Workbench", href: "workbench.html" },
  { id: "archive", label: "Research Archive", href: "archive.html" },
];

const SECTIONS = [
  { id: "workbench", label: "Workbench", href: "workbench.html", title: "3D Engineering Workbench" },
  { id: "mechanism", label: "Mechanism", href: "mechanism.html", title: "Mechanism Lab: folding-fin investigation and model comparison" },
  { id: "observatory", label: "Observatory", href: "observatory.html", title: "Evidence Observatory" },
  { id: "telemetry", label: "Telemetry", href: "telemetry.html", title: "Telemetry & Signal Analysis Theater" },
  { id: "instruments", label: "Instruments", href: "instruments.html", title: "Historical Aerospace Instrumentation Lab" },
];

export function mountShell() {
  const body = document.body;
  const page = body.dataset.page;
  const mode = body.dataset.mode || page;
  const cats = (body.dataset.categories || "").split(",").map((s) => s.trim()).filter(Boolean);
  // Pages outside /lab/ (the Jekyll home page) set data-lab-base="lab/" so links resolve.
  const base = body.dataset.labBase || "";
  const L = (href) => (/^(https?:|#|\.\.\/)/.test(href) ? href : base + href);

  const chip = h("a", { class: "record-chip", href: L("observatory.html"), title: "Live state of the evidence record" }, "record loading…");
  const nav = h("nav", { class: "lab-nav", "aria-label": "Laboratory sections" },
    SECTIONS.map((s) => h("a", { href: L(s.href), title: s.title, "aria-current": s.id === page ? "page" : null }, s.label)),
    chip);
  const toggle = h("button", { class: "menu-toggle", type: "button", "aria-expanded": "false" }, "Menu");
  toggle.addEventListener("click", () => {
    const open = nav.classList.toggle("open");
    toggle.setAttribute("aria-expanded", String(open));
  });
  const header = h("header", { class: "lab-header" },
    h("a", { class: "skip", href: "#main" }, "Skip to content"),
    h("a", { class: "brand", href: L("index.html"), "aria-label": "Project 33 Living Laboratory home" },
      h("span", { class: "brand-mark", "aria-hidden": "true" }, "33"),
      h("span", {}, h("b", {}, "PROJECT 33"), h("small", {}, "VERS3DYNAMICS · LIVING LAB"))),
    h("nav", { class: "modes", "aria-label": "Experience mode" },
      MODES.map((m) => h("a", { href: L(m.href), "aria-current": m.id === mode ? "page" : null }, m.label))),
    nav, toggle);

  const slot = $("#shell-header");
  if (slot) slot.replaceWith(header); else body.prepend(header);

  if (cats.length) {
    const bar = h("div", { class: "category-bar", role: "note", "aria-label": "Information categories on this page" },
      h("span", { class: "label" }, "On this page"),
      cats.map((c) => categoryBadge(c)),
      h("span", { class: "muted" }, cats.length === 1 ? CATEGORIES[cats[0]].text : "Every panel, label, and 3D asset carries its own category tag."));
    header.after(bar);
  }

  const footer = h("footer", { class: "lab-footer" },
    h("span", {}, "PROJECT 33 · VERS3DYNAMICS · BENCH-VALIDATION PROTOTYPE — NOT FLIGHT-TESTED"),
    h("span", {}, "Read-only laboratory: no interaction here can send a hardware command."),
    h("span", { class: "cluster" },
      h("a", { href: siteURL("docs/SAFETY.html") }, "Safety boundary"),
      h("a", { href: L("archive.html#rights") }, "Source rights audit"),
      h("a", { href: "https://github.com/topherchris420/33" }, "Repository ↗")));
  const old = $("#shell-footer");
  if (old) old.replaceWith(footer); else body.append(footer);

  lab.evidence().then((ev) => {
    const c = ev.counts;
    chip.replaceChildren(
      `${c.claims} claims · `, h("b", {}, `${c.claim_status.contradicted || 0} contradicted`),
      ` · ${c.accepted_physical_measurements} measured`);
    chip.title = `${c.claims} claims, ${c.claim_status.contradicted || 0} contradicted, ${c.accepted_physical_measurements} accepted physical measurements, ${c.discrepancies_open} of ${c.discrepancies_total} discrepancies open`;
  }).catch(() => { chip.textContent = "record unavailable"; });
  return { header };
}
