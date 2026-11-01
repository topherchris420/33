/* V3D-TO-33-1 tutorial player: playback, captions, chapters, copy panel,
 * and the page-by-page manual view. The picture is always P33T.renderFrame
 * at a time quantized to 12 drawings per second, the same function the
 * exporter calls frame by frame. */
(function () {
  "use strict";
  var P = window.P33T, TL = window.P33T_TIMELINE, CT = window.P33T_CONTENT;
  var qs = new URLSearchParams(location.search);
  var cutName = qs.get("cut") === "preflight60" ? "preflight60" : "main";
  var cut = TL[cutName];
  var $ = function (id) { return document.getElementById(id); };
  var canvas = $("film"), ctx = canvas.getContext("2d"), audio = $("audio");
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (qs.get("embed") === "1") document.body.classList.add("embed");
  if (cutName === "preflight60") {
    $("stage").classList.add("vertical");
    $("cut-link").textContent = "THE FULL MANUAL"; $("cut-link").href = "tutorial.html";
    $("download").href = "assets/tutorial/project33-preflight60.mp4";
    canvas.width = 1080; canvas.height = 1920;
    $("manual-toggle").hidden = true;
  }
  audio.src = cutName === "main" ? "assets/tutorial/tutorial-mix.m4a" : "assets/tutorial/preflight60-mix.m4a";

  var state = { t: 0, playing: false, sound: true, captions: true, drawn: -1, clock0: 0, t0: 0, manual: false, page: 0, pageAudioEnd: null };
  var tl = $("timeline");
  tl.max = cut.duration.toFixed(2);

  function fmt(t) { t = Math.max(0, t); return Math.floor(t / 60) + ":" + ("0" + Math.floor(t % 60)).slice(-2); }

  /* ---------- canvas sizing and drawing ---------- */
  function resize() {
    var rect = canvas.getBoundingClientRect(), dpr = Math.min(window.devicePixelRatio || 1, 2);
    var w = Math.max(320, Math.min(cut.width, Math.round(rect.width * dpr)));
    var h = Math.round(w * cut.height / cut.width);
    if (canvas.width !== w) { canvas.width = w; canvas.height = h; state.drawn = -1; }
    draw(true);
  }
  var posterT = cutName === "main" ? cut.events["s10.cut"] + 0.5 : 1.5;
  function draw(force) {
    var t = state.started ? state.t : posterT;
    var d = Math.floor(t * 12 + 1e-6);
    if (!force && d === state.drawn) return;
    state.drawn = d;
    var s = canvas.width / cut.width;
    ctx.setTransform(s, 0, 0, s, 0, 0);
    try { P.renderFrame(ctx, cut, t, cut.width, cut.height); } catch (e) { console.error(e); }
  }

  /* ---------- clock ---------- */
  function now() {
    if (state.playing && state.sound && !audio.paused && audio.readyState >= 2) return audio.currentTime;
    if (state.playing) return state.t0 + (performance.now() - state.clock0) / 1000;
    return state.t;
  }
  function play(withSound) {
    if (state.t >= cut.duration - 0.05) seek(0);
    state.sound = withSound; state.started = true;
    $("start").hidden = true;
    state.playing = true; state.clock0 = performance.now(); state.t0 = state.t;
    audio.muted = !withSound;
    audio.currentTime = state.t;
    var pr = audio.play();
    if (pr && pr.catch) pr.catch(function () { state.sound = false; syncButtons(); });
    syncButtons();
  }
  function pause() {
    state.t = now(); state.playing = false; audio.pause(); syncButtons();
  }
  function seek(t) {
    state.started = true;
    state.t = Math.max(0, Math.min(cut.duration, t));
    state.t0 = state.t; state.clock0 = performance.now();
    try { audio.currentTime = state.t; } catch (e) {}
    draw(true); ui();
  }
  function syncButtons() {
    $("toggle").textContent = state.playing ? "❚❚" : "▶";
    $("toggle").setAttribute("aria-label", state.playing ? "Pause" : "Play");
    $("mute").textContent = state.sound ? "Sound on" : "Sound off";
    $("mute").setAttribute("aria-pressed", String(!state.sound));
    $("cc").setAttribute("aria-pressed", String(state.captions));
  }

  /* ---------- chapters, captions, copy panel ---------- */
  function sceneAt(t) {
    for (var i = 0; i < cut.scenes.length; i++) if (t < cut.scenes[i].end) return cut.scenes[i];
    return cut.scenes[cut.scenes.length - 1];
  }
  function chapterAt(t) {
    var c = 0;
    cut.chapters.forEach(function (ch, i) { if (t >= ch.start - 0.01) c = i; });
    return c;
  }
  function tabLabel(title) {
    var m = title.match(/^Sections? (\S+(?: and \S+)?) ·/);
    if (m) return m[1].replace(" and ", "–");
    return { "Cover and scope": "Cover", "Table of contents": "Contents", "Change data summary": "Gates", "Run the review": "End", "Glossary, index and disclaimer": "Credits", "Preflight in 60 seconds": "Cover", "Inert bench preflight": "II-B" }[title] || title;
  }
  var tabs = [];
  cut.chapters.forEach(function (ch, i) {
    var b = document.createElement("button");
    b.type = "button"; b.setAttribute("role", "tab");
    b.textContent = tabLabel(ch.title); b.title = ch.title + " · " + fmt(ch.start);
    if (/III|Abnormal/.test(ch.title)) b.classList.add("mustard");
    if (/Section V ·|Limitations/.test(ch.title)) b.classList.add("sage");
    b.addEventListener("click", function () { seek(ch.start + 0.01); if (state.manual) showPage(pageForChapter(i)); });
    $("tabs").appendChild(b); tabs.push(b);
  });
  var lastChapter = -1, lastCmdKey = null, lastCaption = null;
  function ui() {
    tl.value = state.t.toFixed(2);
    $("time").textContent = fmt(state.t) + " / " + fmt(cut.duration);
    var c = chapterAt(state.t);
    if (c !== lastChapter) {
      tabs.forEach(function (b, i) { b.setAttribute("aria-current", String(i === c)); b.setAttribute("aria-selected", String(i === c)); });
      lastChapter = c;
    }
    var cue = null;
    for (var i = 0; i < cut.cues.length; i++) { var q = cut.cues[i]; if (state.t >= q.start && state.t < q.end + 0.25) { cue = q; break; } }
    var txt = state.captions && cue ? cue.text : "";
    if (txt !== lastCaption) { $("caption").textContent = txt; lastCaption = txt; }
    var key = sceneAt(state.t).commands;
    if (key !== lastCmdKey) { renderCommands(key); lastCmdKey = key; }
  }
  function renderCommands(key) {
    var list = CT.commands[key] || [], box = $("copy-panel");
    box.textContent = "";
    $("copy-chapter").textContent = (cut.chapters[chapterAt(state.t)] || {}).title + ". Exactly as in the repository; select or copy.";
    list.forEach(function (c) {
      var wrap = document.createElement("div"); wrap.className = "cmd";
      var lab = document.createElement("div"); lab.className = "label"; lab.textContent = c.label + " — " + c.src;
      var row = document.createElement("div"); row.className = "row";
      var pre = document.createElement("pre"); var code = document.createElement("code"); code.textContent = c.cmd; pre.appendChild(code);
      var btn = document.createElement("button"); btn.type = "button"; btn.textContent = "Copy";
      btn.setAttribute("aria-label", "Copy: " + c.label);
      btn.addEventListener("click", function () {
        var done = function () { btn.textContent = "Copied"; setTimeout(function () { btn.textContent = "Copy"; }, 1400); };
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(c.cmd).then(done, function () { selectText(pre); });
        else selectText(pre);
      });
      row.appendChild(pre); row.appendChild(btn); wrap.appendChild(lab); wrap.appendChild(row); box.appendChild(wrap);
    });
  }
  function selectText(el) { var r = document.createRange(); r.selectNodeContents(el); var s = getSelection(); s.removeAllRanges(); s.addRange(r); }

  /* ---------- the main loop: a new drawing twelve times a second ---------- */
  var visible = true;
  function loop() {
    if (state.playing) {
      state.t = now();
      if (state.pageAudioEnd !== null && state.t >= state.pageAudioEnd) { pause(); state.pageAudioEnd = null; $("page-audio").setAttribute("aria-pressed", "false"); }
      if (state.t >= cut.duration) { state.t = cut.duration; pause(); }
      if (visible && !state.manual) draw(false);
      ui();
    }
    requestAnimationFrame(loop);
  }
  if ("IntersectionObserver" in window) new IntersectionObserver(function (es) { visible = es[0].isIntersecting; }).observe(canvas);
  document.addEventListener("visibilitychange", function () { if (document.hidden && state.playing && !state.sound) pause(); });

  /* ---------- controls ---------- */
  $("play-sound").addEventListener("click", function () { play(true); });
  $("play-quiet").addEventListener("click", function () { play(false); });
  $("toggle").addEventListener("click", function () { if (state.playing) pause(); else play(state.sound); });
  $("mute").addEventListener("click", function () {
    state.sound = !state.sound; audio.muted = !state.sound;
    if (state.playing) { state.t0 = state.t; state.clock0 = performance.now(); audio.currentTime = state.t; if (state.sound) audio.play().catch(function () {}); }
    syncButtons();
  });
  $("cc").addEventListener("click", function () { state.captions = !state.captions; lastCaption = null; ui(); syncButtons(); });
  tl.addEventListener("input", function () { $("start").hidden = true; seek(parseFloat(tl.value)); });
  document.addEventListener("keydown", function (e) {
    if (e.target && /INPUT|TEXTAREA/.test(e.target.tagName) && e.target.type !== "range") return;
    if (e.code === "Space" && e.target.tagName !== "BUTTON") { e.preventDefault(); if (state.playing) pause(); else play(state.sound); }
    else if (e.key === "ArrowRight" && e.target !== tl) seek(state.t + 5);
    else if (e.key === "ArrowLeft" && e.target !== tl) seek(state.t - 5);
    else if (e.key === "c" || e.key === "C") $("cc").click();
    else if (e.key === "m" || e.key === "M") $("mute").click();
  });

  /* ---------- page-by-page manual view (no camera motion, optional audio) ---------- */
  var PAGES = [
    { ids: ["cover", "scope"], ch: 0 }, { ids: ["toc"], ch: 1 }, { ids: ["div1", "fig11", "fo1"], ch: 2 },
    { ids: ["div2", "p21"], ch: 3 }, { ids: ["p23"], ch: 4 }, { ids: ["p26"], ch: 5 }, { ids: ["p28"], ch: 6 },
    { ids: ["div3", "p31", "fig31"], ch: 7 }, { ids: ["div5", "p51"], ch: 8 }, { ids: ["cds"], ch: 9 },
    { ids: ["endcard"], ch: 10 }, { ids: ["glossary"], ch: 11 },
  ];
  function pageForChapter(c) { for (var i = 0; i < PAGES.length; i++) if (PAGES[i].ch === c) return i; return 0; }
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; }
  function renderBlocks(article, blocks) {
    (blocks || []).forEach(function (b) {
      if (b.t === "h") article.appendChild(el("h3", null, b.text));
      else if (b.t === "h2") article.appendChild(el("h4", null, b.text));
      else if (b.t === "text") article.appendChild(el("p", null, b.text));
      else if (b.t === "small") article.appendChild(el("p", "small", b.text));
      else if (b.t === "toc") {
        var r = el("div", "toc"); r.appendChild(el("span", null, (b.label ? b.label + "  " : "") + b.title)); r.appendChild(el("span", "lead")); r.appendChild(el("span", "pg", b.page)); article.appendChild(r);
      } else if (b.t === "step") {
        var p = el("p", "step"); p.appendChild(document.createTextNode((b.n || "") + " "));
        if (b.cmd) p.appendChild(el("code", null, b.cmd)); else p.appendChild(el("b", null, b.item));
        p.appendChild(document.createTextNode(" – " + b.state)); article.appendChild(p);
      } else if (b.t === "sub") article.appendChild(el("p", "sub", b.text));
      else if (b.t === "cond") article.appendChild(el("p", "cond", b.text));
      else if (b.t === "note" || b.t === "caution" || b.t === "warning") {
        var box = el("aside", "box " + b.t); box.appendChild(el("span", "kind", b.t.toUpperCase())); box.appendChild(document.createTextNode(b.text)); article.appendChild(box);
      } else if (b.t === "table") {
        if (b.caption) article.appendChild(el("p", "small", b.caption));
        var tb = el("table"), tr = el("tr"); b.cols.forEach(function (c) { tr.appendChild(el("th", null, c)); }); tb.appendChild(tr);
        b.rows.forEach(function (row) { var r2 = el("tr"); row.forEach(function (c) { r2.appendChild(el("td", null, c)); }); tb.appendChild(r2); });
        article.appendChild(tb);
      }
    });
  }
  function renderPageContent(article, id) {
    var pg = CT.pages[id];
    if (id === "glossary") {
      article.appendChild(el("h3", null, "Glossary"));
      CT.glossary.forEach(function (g) { var p = el("p"); p.appendChild(el("b", null, g[0] + " — ")); p.appendChild(document.createTextNode(g[1])); article.appendChild(p); });
      article.appendChild(el("h4", null, "Index"));
      cut.chapters.forEach(function (c) { var r = el("div", "toc"); r.appendChild(el("span", null, c.title)); r.appendChild(el("span", "lead")); r.appendChild(el("span", "pg", fmt(c.start))); article.appendChild(r); });
      article.appendChild(el("h4", null, "Standing disclaimer"));
      article.appendChild(el("p", null, CT.disclaimer));
      return;
    }
    if (!pg) return;
    if (pg.lines) {
      if (pg.figure) article.appendChild(el("h4", null, pg.figure));
      var pre = el("p"); pre.style.whiteSpace = "pre-wrap"; pre.textContent = pg.lines.join("\n"); article.appendChild(pre);
      return;
    }
    if (pg.tab) { article.appendChild(el("h4", null, pg.section)); article.appendChild(el("h3", null, pg.title)); renderBlocks(article, pg.blocks); article.appendChild(el("h4", null, "INTRODUCTION")); article.appendChild(el("p", null, pg.intro)); return; }
    if (pg.callouts) { article.appendChild(el("h4", null, pg.figure)); var ol = el("ol"); pg.callouts.forEach(function (c) { ol.appendChild(el("li", null, c)); }); article.appendChild(ol); return; }
    if (pg.rows && pg.root) { article.appendChild(el("h4", null, pg.figure)); article.appendChild(el("p", null, pg.root)); pg.rows.forEach(function (r) { var d = el("div", "toc"); d.appendChild(el("span", null, r[0])); d.appendChild(el("span", "lead")); d.appendChild(el("span", "pg", r[1])); article.appendChild(d); }); article.appendChild(el("p", "small", pg.source)); return; }
    if (pg.gates) {
      article.appendChild(el("h3", null, pg.title));
      var ul = el("ol"); pg.gates.forEach(function (g, i) {
        var who = Object.keys(pg.claims).filter(function (k) { return pg.claims[k] === i; });
        ul.appendChild(el("li", null, g + (who.length ? "  ← " + who.join(", ") : "") + (i >= pg.humanFrom ? "  (needs a named human)" : "")));
      });
      article.appendChild(ul); article.appendChild(el("p", null, pg.note)); return;
    }
    renderBlocks(article, pg.blocks);
  }
  function stillTime(c) {
    var ch = cut.chapters[c];
    var ends = { 0: 16.9, 1: 31.0, 2: 59.0, 3: 87.0, 4: 126.0, 5: 147.0, 6: 160.5, 7: 188.0, 8: 206.5, 9: 222.0, 10: 236.0, 11: 241.0 };
    return ends[c] !== undefined && cutName === "main" ? ends[c] : ch.start + (ch.end - ch.start) * 0.7;
  }
  function showPage(i) {
    state.page = Math.max(0, Math.min(PAGES.length - 1, i));
    var pg = PAGES[state.page], ch = cut.chapters[pg.ch], art = $("sheet");
    art.textContent = "";
    var fur = el("div", "furniture"); fur.appendChild(el("span", null, CT.pub)); fur.appendChild(el("span", null, ch.title)); art.appendChild(fur);
    // a still from the film for this chapter: no camera motion
    var still = el("canvas", "still"); still.width = 960; still.height = 540; still.setAttribute("role", "img"); still.setAttribute("aria-label", "Still from the film: " + ch.title);
    art.appendChild(still);
    var sc = still.getContext("2d"); sc.setTransform(0.5, 0, 0, 0.5, 0, 0);
    try { P.renderFrame(sc, cut, stillTime(pg.ch), cut.width, cut.height); } catch (e) {}
    pg.ids.forEach(function (id) { renderPageContent(art, id); });
    var said = cut.cues.filter(function (q) { return q.start >= ch.start && q.start < ch.end; });
    if (said.length) { var n = el("div", "narration"); n.appendChild(el("b", null, "Narration: ")); n.appendChild(document.createTextNode(said.map(function (q) { return q.text; }).join(" "))); art.appendChild(n); }
    $("page-of").textContent = "Page " + (state.page + 1) + " of " + PAGES.length;
    $("prev").disabled = state.page === 0; $("next").disabled = state.page === PAGES.length - 1;
    seek(ch.start + 0.01);
  }
  function setManual(on) {
    state.manual = on;
    if (on) pause();
    $("manual").hidden = !on; $("film-view").hidden = on;
    $("manual-toggle").setAttribute("aria-pressed", String(on));
    if (on) { showPage(pageForChapter(chapterAt(state.t))); $("sheet").focus(); } else { draw(true); }
  }
  $("manual-toggle").addEventListener("click", function () { setManual(!state.manual); });
  $("back-to-film").addEventListener("click", function () { setManual(false); });
  $("prev").addEventListener("click", function () { if (state.playing) pause(); showPage(state.page - 1); });
  $("next").addEventListener("click", function () { if (state.playing) pause(); showPage(state.page + 1); });
  $("page-audio").addEventListener("click", function () {
    var ch = cut.chapters[PAGES[state.page].ch];
    if (state.playing) { pause(); state.pageAudioEnd = null; $("page-audio").setAttribute("aria-pressed", "false"); return; }
    seek(ch.start + 0.01); state.pageAudioEnd = ch.end; play(true); $("page-audio").setAttribute("aria-pressed", "true");
  });

  /* ---------- start ---------- */
  P.init().then(function () {
    window.addEventListener("resize", resize);
    // poster: the binder standing beside the rocket, before anything plays
    resize();
    ui(); syncButtons();
    if (reduce && cutName === "main") setManual(true);
    requestAnimationFrame(loop);
  });

  /* Hooks for the deterministic exporter (tools/export_tutorial_film.mjs). */
  window.project33Tutorial = {
    cut: cut,
    ready: function () { return P.init(); },
    renderAt: function (t, target) {
      var c = target || canvas, x = c.getContext("2d"), s = c.width / cut.width;
      x.setTransform(s, 0, 0, s, 0, 0); P.renderFrame(x, cut, t, cut.width, cut.height);
    },
  };
})();
