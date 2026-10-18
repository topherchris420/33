import { RocketFilm, DURATION, CHAPTERS } from "./rocket.mjs";
const canvas = document.querySelector("#rocket");
if (canvas && canvas.getContext("2d")) {
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const film = new RocketFilm(canvas, {
    cinematic: document.body.dataset.cinematic === "true",
  });
  const toggle = document.querySelector("#toggle"),
    timeline = document.querySelector("#timeline");
  const output = document.querySelector("#time"),
    chapter = document.querySelector("#chapter");
  let time = reduced.matches ? 24 : 0,
    playing = !reduced.matches,
    previous = null,
    visible = true;
  let frameId = null;
  const update = () => {
    film.render(time);
    timeline.value = time;
    output.value = `${String(Math.floor(time)).padStart(2, "0")} / 32`;
    const index = CHAPTERS.findLastIndex((ch) => time >= ch.start);
    chapter.textContent = `0${index + 1} / ${CHAPTERS[index].name.toUpperCase()}`;
    toggle.textContent = playing ? "Ⅱ" : "▶";
    toggle.setAttribute(
      "aria-label",
      playing ? "Pause animation" : "Play animation",
    );
  };
  function schedule() {
    if (frameId === null && playing && visible && !document.hidden)
      frameId = requestAnimationFrame(tick);
  }
  function tick(now) {
    frameId = null;
    if (previous !== null)
      time = (time + Math.min((now - previous) / 1000, 0.1)) % DURATION;
    previous = now;
    update();
    schedule();
  }
  toggle.addEventListener("click", () => {
    playing = !playing;
    previous = null;
    update();
    schedule();
  });
  timeline.addEventListener("input", () => {
    time = Number(timeline.value);
    previous = null;
    update();
  });
  document.querySelector("#restart").addEventListener("click", () => {
    time = 0;
    previous = null;
    update();
  });
  for (const mode of ["blueprint", "surface"])
    document.querySelector(`#${mode}-mode`).addEventListener("click", () => {
      film.mode = mode;
      for (const name of ["blueprint", "surface"])
        document
          .querySelector(`#${name}-mode`)
          .setAttribute("aria-pressed", String(name === mode));
      update();
    });
  new ResizeObserver(() => {
    film.resize();
    update();
  }).observe(canvas);
  new IntersectionObserver((entries) => {
    visible = entries[0].isIntersecting;
    previous = null;
    schedule();
  }).observe(canvas);
  document.addEventListener("visibilitychange", () => {
    previous = null;
    schedule();
  });
  reduced.addEventListener("change", () => {
    if (reduced.matches) {
      playing = false;
      time = 24;
      previous = null;
      update();
    }
  });
  // Deterministic render interface for exporting the exact browser artwork.
  globalThis.project33Film = {
    film,
    seek(value) {
      playing = false;
      time = Number(value);
      update();
    },
    get time() {
      return time;
    },
    get playing() {
      return playing;
    },
  };
  update();
  schedule();
} else if (canvas) {
  canvas.style.display = "none";
  document.querySelector(".canvas-fallback")?.removeAttribute("hidden");
  document.querySelector(".player")?.setAttribute("hidden", "");
}
