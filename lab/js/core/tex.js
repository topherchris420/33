// KaTeX rendering for engineering notation. Falls back to the raw TeX source in a <code>
// element if the library fails to load, so the content is never lost.
let katexPromise;

function loadKatex() {
  if (!katexPromise) {
    if (!document.querySelector("link[data-katex]")) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = new URL("../../lib/katex/katex.min.css", import.meta.url).href;
      link.dataset.katex = "";
      document.head.append(link);
    }
    katexPromise = import("../../lib/katex/katex.mjs").then((m) => m.default || m).catch(() => null);
  }
  return katexPromise;
}

/** Render TeX into an element. display=true for block equations. */
export async function tex(el, source, { display = true } = {}) {
  el.classList.add("math");
  el.setAttribute("aria-label", source);
  const katex = await loadKatex();
  if (!katex) { el.replaceChildren(Object.assign(document.createElement("code"), { textContent: source })); return; }
  katex.render(source, el, { displayMode: display, throwOnError: false, strict: "ignore", output: "htmlAndMathml" });
}

/** Render every [data-tex] element under root. */
export async function renderAll(root = document) {
  await Promise.all([...root.querySelectorAll("[data-tex]")].map((el) => tex(el, el.dataset.tex, { display: el.dataset.display !== "inline" })));
}

/** Convenience: create a block equation element. */
export function eq(source, { display = true } = {}) {
  const el = document.createElement(display ? "div" : "span");
  tex(el, source, { display });
  return el;
}
