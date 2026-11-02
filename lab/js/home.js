// Project site home page (_layouts/lab-home.html): navigation, the hero spotlight, the live
// evidence record, scroll reveals, call-to-action sparkles, and the 3D rocket, which loads only
// after the page is interactive. Every number shown is read from the committed evidence record
// (lab/data/evidence.json). Like the rest of the laboratory, nothing here can transmit anything.
import { lab, claimLink } from "./core/data.js";
import { h, $, $$, clear, webglAvailable } from "./core/dom.js";
import { STATUS } from "./core/taxonomy.js";
import { sparkles } from "./home/sparkles.js";

const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");
const STATUS_CLASS = {
  contradicted: "status-contradicted",
  open: "status-open",
  supported_within_limits: "status-supported_within_limits",
};
// The record requires a named human from this gate onward (see docs/ROADMAP.md).
const HUMAN_GATE = "inert_bench_setup";

function initNav() {
  const nav = $("#site-nav");
  const toggle = nav && $(".nav-toggle", nav);
  const panel = $("#nav-panel");
  if (!nav || !toggle || !panel) return;
  const isOpen = () => nav.classList.contains("is-open");
  const setOpen = (open) => {
    nav.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
  };
  toggle.addEventListener("click", () => setOpen(!isOpen()));
  panel.addEventListener("click", (event) => { if (event.target.closest("a")) setOpen(false); });
  document.addEventListener("click", (event) => { if (isOpen() && !nav.contains(event.target)) setOpen(false); });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && isOpen()) { setOpen(false); toggle.focus(); }
  });
  const onScroll = () => nav.classList.toggle("is-scrolled", window.scrollY > 24);
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
}

// A soft glow that follows the pointer across the hero card (pointer devices only).
function initSpotlight() {
  const card = $("#hero-card");
  const glow = card && $(".spotlight-follow", card);
  if (!glow || !finePointer.matches) return;
  let tx = 0, ty = 0, x = 0, y = 0, frame = 0;
  const step = () => {
    const k = motionQuery.matches ? 1 : 0.16;
    x += (tx - x) * k;
    y += (ty - y) * k;
    const half = glow.offsetWidth / 2;
    glow.style.transform = `translate3d(${(x - half).toFixed(1)}px, ${(y - half).toFixed(1)}px, 0)`;
    frame = Math.abs(tx - x) + Math.abs(ty - y) > 0.4 ? requestAnimationFrame(step) : 0;
  };
  card.addEventListener("pointermove", (event) => {
    if (event.pointerType !== "mouse") return;
    const rect = card.getBoundingClientRect();
    tx = event.clientX - rect.left;
    ty = event.clientY - rect.top;
    if (!glow.classList.contains("on")) { x = tx; y = ty; glow.classList.add("on"); }
    if (!frame) frame = requestAnimationFrame(step);
  });
  card.addEventListener("pointerleave", () => glow.classList.remove("on"));
}

function initReveal() {
  const cta = $(".cta");
  if (!("IntersectionObserver" in window)) { cta?.classList.add("is-in"); return; }
  if (!motionQuery.matches) document.documentElement.classList.add("reveal-ready");
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add("is-in");
      observer.unobserve(entry.target);
    }
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.06 });
  $$("[data-reveal]").forEach((el) => observer.observe(el));
  if (cta) observer.observe(cta);
}

function initSparkles() {
  const canvas = $("#cta-sparkles");
  if (canvas) sparkles(canvas, { motionQuery });
}

// ---------------------------------------------------------------------------
// Live evidence record
// ---------------------------------------------------------------------------
function renderStats(counts) {
  const status = counts.claim_status;
  const values = [counts.claims, status.contradicted || 0, status.open || 0, counts.accepted_physical_measurements];
  $$("#stats .stat > b").forEach((b, i) => { b.textContent = String(values[i]); });
  const chip = (value, label) => h("span", {}, h("b", {}, String(value)), ` ${label}`);
  clear($("#stats-minor"),
    chip(status.supported_within_limits || 0, "supported within stated limits"),
    chip(`${counts.discrepancies_open}/${counts.discrepancies_total}`, "discrepancies open"),
    chip(`${counts.predictions_not_measured}/${counts.predictions_total}`, "predictions not yet measured"));
}

function renderClaims(claims) {
  const grid = $("#claim-grid");
  if (!grid || !claims?.length) return;
  clear(grid, claims.map((claim) => {
    const open = claim.discrepancies_open.length;
    const label = STATUS[claim.status]?.label || claim.status_label;
    return h("a", { class: "claim-card", href: claimLink(claim.id), "aria-label": `${claim.id}, ${claim.title}: ${label}. Open the claim passport.` },
      h("span", { class: `status ${STATUS_CLASS[claim.status] || "status-other"}` }, label),
      h("p", { class: "claim-q" }, claim.question),
      h("span", { class: "claim-foot" },
        h("strong", {}, h("span", {}, claim.id), claim.title),
        h("small", {}, `${claim.support_label} · ${open ? `${open} open discrepanc${open === 1 ? "y" : "ies"}` : "no open discrepancies"}`)));
  }));
}

// Rebuilt from the record's own gate vocabulary, so the track cannot disagree with it.
function renderGates(record) {
  const list = $("#gate-list");
  const gates = record.vocabulary?.gates;
  if (!list || !Array.isArray(gates) || !gates.length) return;
  const index = new Map(gates.map(([key], i) => [key, i]));
  const reached = Math.max(-1, ...record.claims.map((c) => index.get(c.gate) ?? -1));
  const human = index.get(HUMAN_GATE) ?? gates.length;
  clear(list, gates.map(([key, label], i) => {
    const here = record.claims.filter((c) => c.gate === key);
    const classes = ["gate", i <= reached && "is-reached", i === reached && "is-frontier", i >= human && "is-human"];
    return h("li", { class: classes.filter(Boolean).join(" "), "data-gate": key },
      h("span", { class: "gate-dot", "aria-hidden": "true" }),
      h("span", { class: "gate-num" }, `Gate ${i + 1}`),
      h("span", { class: "gate-label" }, label.charAt(0) + label.slice(1).toLowerCase()),
      h("span", { class: "sr-only" }, i <= reached ? "Reached by at least one claim." : "Not reached by any claim."),
      h("span", { class: "gate-claims" }, here.map((c) => h("a", {
        class: `gate-chip ${c.status}`, href: claimLink(c.id), title: `${c.id} · ${c.title} · ${c.status_label}`,
      }, c.id))));
  }));
}

function initRecord() {
  const line = $("#hub-record");
  lab.evidence().then((record) => {
    const c = record.counts;
    const status = c.claim_status;
    if (line) line.textContent = `${c.claims} claims · ${status.contradicted || 0} contradicted · ${status.open || 0} unresolved · ${c.accepted_physical_measurements} accepted physical measurements`;
    renderStats(c);
    renderClaims(record.claims);
    renderGates(record);
  }).catch(() => {
    if (line) line.textContent = "Evidence record unavailable: open the engineering brief below";
  });
}

// ---------------------------------------------------------------------------
// 3D hero: loaded after first paint; the poster image stands in without WebGL.
// ---------------------------------------------------------------------------
function initHero() {
  const stage = $("#hero-stage");
  if (!stage) return;
  const fallback = () => { stage.dataset.state = "fallback"; };
  if (!webglAvailable()) { fallback(); return; }
  stage.dataset.state = "loading";
  const start = () => import("./home/hero-rocket.js")
    .then((module) => module.mountHeroRocket(stage, { card: $("#hero-card"), motionQuery, finePointer }))
    .catch(fallback);
  if ("requestIdleCallback" in window) window.requestIdleCallback(start, { timeout: 1200 });
  else setTimeout(start, 120);
}

initNav();
initSpotlight();
initReveal();
initSparkles();
initRecord();
initHero();
