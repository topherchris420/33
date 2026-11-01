// Small DOM helpers shared by every laboratory page. No framework, no build step.

/** Create an element: h("div", {class: "x", onclick: fn}, child, "text"). */
export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") el.className = value;
    else if (key === "style" && typeof value === "object") {
      for (const [prop, v] of Object.entries(value)) {
        if (prop.startsWith("--")) el.style.setProperty(prop, String(v)); else el.style[prop] = v;
      }
    }
    else if (key === "dataset") Object.assign(el.dataset, value);
    else if (key.startsWith("on") && typeof value === "function") el.addEventListener(key.slice(2), value);
    else if (key === "html") el.innerHTML = value;
    else if (value === true) el.setAttribute(key, "");
    else el.setAttribute(key, String(value));
  }
  append(el, children);
  return el;
}

function append(el, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

export function clear(el, ...children) {
  el.replaceChildren();
  append(el, children);
  return el;
}

let live;
/** Announce a state change to assistive technology. */
export function announce(message) {
  if (!live) {
    live = h("div", { class: "sr-only", "aria-live": "polite", role: "status" });
    document.body.append(live);
  }
  live.textContent = "";
  requestAnimationFrame(() => { live.textContent = message; });
}

export const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Format a length given in metres or millimetres as millimetres with sensible precision. */
export function mm(value, { fromMetres = false, digits } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return "NOT SPECIFIED";
  const v = fromMetres ? value * 1000 : value;
  const d = digits ?? (Math.abs(v) >= 100 ? 1 : 2);
  return `${v.toFixed(d)} mm`;
}

export function fixed(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return Number(value).toFixed(digits);
}

/** Keep the filled part of a range input in sync with its value (used by the CSS track). */
export function syncRange(input) {
  const update = () => {
    const min = Number(input.min || 0), max = Number(input.max || 100);
    input.style.setProperty("--fill", `${((Number(input.value) - min) / (max - min)) * 100}%`);
  };
  input.addEventListener("input", update);
  update();
  return input;
}

/** Toggle-button helper: sets aria-pressed and returns the new state. */
export function press(button, state) {
  const next = state ?? button.getAttribute("aria-pressed") !== "true";
  button.setAttribute("aria-pressed", String(next));
  return next;
}

/** Tabs implementing the three explanation depths (Introduction / Engineering / Research). */
export function depthTabs(container, depths, initial = 0) {
  const tablist = h("div", { class: "depths", role: "tablist" });
  const panels = [];
  depths.forEach((depth, i) => {
    const id = `${container.id || "d"}-${i}-${Math.random().toString(36).slice(2, 7)}`;
    const tab = h("button", { role: "tab", id: `${id}-tab`, "aria-controls": id, "aria-selected": String(i === initial), tabindex: i === initial ? "0" : "-1" }, depth.label);
    const panel = h("div", { class: "depth-panel", role: "tabpanel", id, "aria-labelledby": `${id}-tab`, hidden: i !== initial });
    if (typeof depth.content === "function") depth.content(panel); else append(panel, [depth.content]);
    tab.addEventListener("click", () => select(i));
    tab.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
        const n = (i + (e.key === "ArrowRight" ? 1 : depths.length - 1)) % depths.length;
        select(n); tablist.children[n].focus();
      }
    });
    tablist.append(tab);
    panels.push(panel);
  });
  function select(n) {
    [...tablist.children].forEach((t, i) => { t.setAttribute("aria-selected", String(i === n)); t.tabIndex = i === n ? 0 : -1; });
    panels.forEach((p, i) => { p.hidden = i !== n; });
  }
  container.append(tablist, ...panels);
  return { select };
}

export function copyButton(text, label = "Copy") {
  const b = h("button", { class: "btn ghost", type: "button" }, label);
  b.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(text); b.textContent = "Copied"; } catch { b.textContent = "Select and copy"; }
    setTimeout(() => { b.textContent = label; }, 1400);
  });
  return b;
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = h("a", { href: url, download: filename });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export function webglAvailable() {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGL2RenderingContext && c.getContext("webgl2")) || !!c.getContext("webgl");
  } catch { return false; }
}
