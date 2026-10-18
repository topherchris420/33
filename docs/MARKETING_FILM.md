# From frequency to form

Project 33's project page and design film use the existing GitHub Pages / Jekyll deployment. The root `index.md` keeps its generated evidence fragments and now selects the `landing` layout; its complete engineering brief remains available under **Open the engineering brief**. The film lives at `film.html`.

## The film

The silent, 32-second film is available as an interactive Canvas animation and a 1920 × 1080, 24 fps H.264 MP4. Its three chapters are:

| Time | Chapter | Visual |
| --- | --- | --- |
| 0–9 s | The idea | Fourier epicycles draw a closed rocket silhouette while component contours appear. |
| 9–21 s | The assembly | The drawing finishes and the exploded nose, fins, canards, and base move into place. |
| 21–32 s | The perspective | The viewpoint rotates around the assembled three-dimensional wireframe. |

The illustration uses a cylindrical body, rounded nose, four aft fins, and four canards inspired by the repository's side-view silhouette. It is hand-authored in normalized scene coordinates. It is **not extracted from the Fusion archives, not to scale, and not an assembly procedure**. In particular, it does not depict a validated folding linkage. The animation supplies no engineering evidence and changes no claim status.

## Fourier construction

`assets/marketing/fourier.mjs` resamples closed polylines at equal arc-length intervals, computes their complex discrete Fourier coefficients, and sorts the terms by magnitude. Signed frequencies preserve traversal direction. At time `t`, each term contributes `c[k] * exp(i * 2π * k * t)`; their vector sum determines the pen position. The renderer draws the coefficient circles and vector chain while accumulating the curve.

The full silhouette uses 256 samples and 65 terms. Component contours use 128 samples and 45 terms. Each contour's local plane is mapped into three-dimensional scene coordinates before orthographic projection. The viewpoint rotates through the final chapter. This is a Canvas wireframe renderer; it does not require WebGL, a graphics framework, external fonts, a CDN, or a network service.

The player supports pause/play, timeline scrubbing, restart, blueprint/surface styling, and keyboard controls through native buttons and a range input. Reduced-motion preferences show a paused, assembled view; the visitor can choose to play. Rendering stops when the canvas is outside the viewport or the page is hidden. A poster and MP4 fallback cover disabled JavaScript.

## Edit and verify

- Page: `_layouts/landing.html` and `assets/marketing/site.css`.
- Geometry, camera, timing, and film titles: `assets/marketing/rocket.mjs`.
- Playback: `assets/marketing/player.mjs`.
- Film page: `film.html`.
- Coefficient reconstruction and sampling tests: `node --test tests/fourier.test.mjs` (Node 22+).

Preview through Jekyll, with the repository's `/33` base path. The **Project page and film** workflow runs the math tests and an actual GitHub Pages Jekyll build on every push and pull request. The existing engineering CI remains separate.

## Export the MP4

The exporter renders deterministic frames from the same browser artwork at exactly `frame / 24` seconds, then streams them into FFmpeg. It does not record wall-clock playback. Prerequisites: Node 22+, Playwright with Chromium, FFmpeg with libx264, and a running Jekyll preview or a deployed version containing this film.

Example setup and export in PowerShell, from the repository root:

```powershell
npm install --prefix build/film-tools playwright@1.62.1
$env:PLAYWRIGHT_MODULE = (Resolve-Path build/film-tools/node_modules/playwright).Path
node build/film-tools/node_modules/playwright/cli.js install chromium
node tools/export_marketing_film.mjs http://127.0.0.1:4000/33/film.html build/project33-blueprint.mp4
```

FFmpeg must be on `PATH`; alternatively set `FFMPEG_PATH` to its executable. Set `CHROME_PATH` to use an existing Chrome executable instead of Playwright's bundled Chromium. The same environment variables work on other operating systems with their shell's assignment syntax. Export requires no credentials or hardware. Copy the approved output into `assets/marketing/project33-blueprint.mp4` and update `assets/marketing/poster.jpg` after visual changes so the downloadable film and page stay consistent.

## Exact bytes on Windows

The evidence archive hashes exact committed bytes. `.gitattributes` keeps text files at LF line endings across platforms and treats media and CAD archives as binary. Existing Windows checkouts made before this rule may need a fresh clone to replace already-translated files. The evidence test fixture writes registered session data as explicit UTF-8 bytes for the same reason. Symbolic-link tampering tests run on Linux and on Windows accounts with the required privilege; otherwise those two tests explicitly skip.
