// A field of slowly drifting, twinkling points behind the home page's call to action.
// Canvas 2D only. It pauses off screen and in background tabs, and draws a single still
// frame when reduced motion is requested. Decorative: it carries no information.

const AREA = 800 * 800; // particles are specified per 800 x 800 px, as in common particle engines

export function sparkles(canvas, {
  density = 110, minSize = 0.6, maxSize = 1.4, speed = 0.8, color = "255, 255, 255", motionQuery,
} = {}) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  let width = 0, height = 0, particles = [], frame = 0, visible = false, last = 0;
  const still = () => Boolean(motionQuery?.matches);

  const spawn = () => {
    const heading = Math.random() * Math.PI * 2;
    const pace = (4 + Math.random() * 20) * speed; // px/s
    return {
      x: Math.random() * width,
      y: Math.random() * height,
      r: minSize + Math.random() * (maxSize - minSize),
      vx: Math.cos(heading) * pace,
      vy: Math.sin(heading) * pace,
      phase: Math.random() * Math.PI * 2,
      rate: (0.6 + Math.random() * 1.4) * speed, // rad/s of the twinkle
    };
  };

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = rect.width;
    height = rect.height;
    canvas.width = Math.max(1, Math.round(width * dpr));
    canvas.height = Math.max(1, Math.round(height * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = Math.min(260, Math.round((density * width * height) / AREA));
    particles = Array.from({ length: count }, spawn);
    draw(0);
  }

  function draw(dt) {
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = `rgb(${color})`;
    for (const p of particles) {
      if (dt) {
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.phase += p.rate * dt;
        if (p.x < -4) p.x = width + 4; else if (p.x > width + 4) p.x = -4;
        if (p.y < -4) p.y = height + 4; else if (p.y > height + 4) p.y = -4;
      }
      ctx.globalAlpha = 0.1 + 0.9 * (0.5 + 0.5 * Math.sin(p.phase));
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  function tick(now) {
    frame = 0;
    const dt = last ? Math.min((now - last) / 1000, 0.05) : 0;
    last = now;
    draw(dt);
    schedule();
  }

  function schedule() {
    if (!frame && visible && !document.hidden && !still()) frame = requestAnimationFrame(tick);
    else if (!frame) last = 0;
  }

  new ResizeObserver(resize).observe(canvas);
  new IntersectionObserver((entries) => {
    visible = entries[0].isIntersecting;
    last = 0;
    schedule();
  }).observe(canvas);
  document.addEventListener("visibilitychange", () => { last = 0; schedule(); });
  motionQuery?.addEventListener?.("change", () => { last = 0; draw(0); schedule(); });
  return { redraw: () => draw(0) };
}
