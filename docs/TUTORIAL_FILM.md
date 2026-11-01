# The Bench Manual (tutorial film)

*V3D-TO-33-1, a claymation tutorial for Project 33.* The film teaches the two procedures the repository supports today, offline review of the evidence record and inert bench validation, in the documentary grammar of a flight manual: numbered **ITEM – STATE** steps, WARNING, CAUTION and NOTE placards set down before the steps they guard, tab dividers, a foldout, a degraded-modes diagram, and an operating-limitations section that lists the record's contradictions as plainly as its procedures. It borrows the manual's page structure and nothing else: no text, figures, aircraft, markings or mission content from any government publication.

**Claymation tutorial. Not a flight test, physical assembly record, or evidence of deployment. Procedures are summarized from the Project 33 repository, which is authoritative. This film supplies no engineering evidence and changes no claim status.**

## Watch it

- Interactive page: [`tutorial.html`](https://topherchris420.github.io/33/tutorial.html), with **Play with sound** (browsers block autoplay with sound), captions, chapter tabs styled as manual dividers, a copy panel that shows the current step's commands as selectable text, and a page-by-page manual view.
- The 9:16 social cut, *Preflight in 60 Seconds*: `tutorial.html?cut=preflight60`.
- Embed without the surrounding page: add `?embed=1`.
- Files: `assets/tutorial/project33-bench-manual.mp4` (compressed copy for the repository), `assets/tutorial/project33-preflight60.mp4`, `assets/tutorial/poster.jpg`, captions `tutorial.en.vtt` / `tutorial.en.srt` (and `preflight60.en.*`), chapters `tutorial.chapters.vtt`, and a timestamp list for a video description, `tutorial.chapters.txt`.

## Chapters

| Time | Chapter | What it teaches |
| --- | --- | --- |
| 0:00 | Cover and scope | The manual authorizes no ignition, propulsion or flight. Safety gates G-01 to G-14, each NOT MEASURED on hardware. |
| 0:19 | Table of contents | Flight characteristics and performance data: NOT MEASURED. Adverse weather: outside the validation boundary. |
| 0:32 | Section I · Description | Exploded system (FIGURE 1-1), the data path (FO-1: dashboard, Wi-Fi UDP 4444, launcher, UART2 115200, rocket), roll-only control (VIEW A-A). |
| 1:05 | Section II-A · Offline review | `python -m evidence status`, `check`, `build --output build/review`, `verify build/review`, open `build/review/index.html`. |
| 1:29 | Section II-B · Inert bench preflight | The ten-step preflight from `docs/SAFETY.md`, ending with `CMD_REJECT:dashboard_launch_disabled`. |
| 2:09 | Section II-C · Canards and gain windows | Canard centres and the ±12° limit from firmware; the four gain windows from `docs/PID_TUNING.md`. |
| 2:29 | Section II-D · Session passport | Close cleanly, declare, build a passport, verify; only a named human accepts. |
| 2:44 | Sections III and IV · Abnormal operations | Loss of rocket telemetry, the read-only status board, DUMP LOG isolation, FIGURE 3-1 degraded modes. |
| 3:10 | Section V · Operating limitations | C1 linkage does not close; C6 margin 19% vs 20%; C5 models disagree; C8 modulus; zero accepted physical measurements. |
| 3:38 | Change data summary | The validation gates, each claim's bead at the gate its passport reports, and the line from which every gate needs a person. |
| 3:46 | Run the review | End card: `python -m evidence status`. |
| 3:59 | Glossary, index and disclaimer | |

The film runs 4:08 including credits.

## What was re-verified, and against what

Every on-screen command, number and status was checked at commit `217696a` (2026-11-01), and the offline-review commands were run as shown: `status` and `check` exit 0, `build --output build/review` writes the packet, a second build into the same folder is refused, and `verify build/review` reports `"bundle_integrity": "verified"`.

| On screen | Source |
| --- | --- |
| Record state (8 claims · 3 contradicted · 4 unresolved · 1 supported within stated limits · 0 accepted physical measurements) and the claim lines | live `python -m evidence status`; [claim passports](claims/README.md) |
| Gate each claim has reached (C1 analytical model; C2 synthetic test; the rest software reproduction) | `Gate reached` in each passport |
| Preflight steps, bench rules, safety gates | [Safety](SAFETY.md) |
| Canard GPIO, centres, ±12° | `Firmware/Rocket/src/main.cpp`, [Wiring](WIRING.md) (the calibration sketch's swapped LEFT/RIGHT labels are not used) |
| Gain-window matrix and the saturation caution | [PID Tuning](PID_TUNING.md) |
| Session folder files, declare/passport/verify, "never run session accept" | [Bench Sessions](BENCH_SESSIONS.md) |
| Dashboard labels (`RAW SESSION (not evidence)`, `no fix`, `not reported`, button names), `ABORT:Arming switch flipped OFF.` | `Firmware/dashboard.py`, `Firmware/Launcher/src/main.cpp` |
| DUMP LOG isolation, advisory `C-ROCKET-TELEMETRY-LOST` | [Ground Status](GROUND_STATUS.md) |
| Degraded modes (12, 4, 1, 7, 6, 9, 11 of 12) | [Degraded Modes](DEGRADED_MODES.md) |
| Validation gates | [Roadmap](ROADMAP.md), [Evidence Observatory](EVIDENCE_OBSERVATORY.md) |

The film says what it does not show: no ignition, motor, propellant, flame, launch or countdown; no way to enable dashboard launch or bench-only ignition; no steering, guidance or targeting (roll stabilization is the only loop). The one picture of the rocket in flight is a pencil doodle on a sticky note, stamped NOT MEASURED. If the record changes, re-run the checks above and rebuild; the on-screen text and narration both come from `assets/tutorial/content.js` and `tools/tutorial/narration.json`.

## How it is made

**Picture.** Canvas 2D only, no libraries, no WebGL, no network. Every object is hand-shaped from paths and shaded as plasticine in code: lamp gradient, occlusion and rim light from inner shadows, a procedurally generated thumb-worked texture, a matte sheen. Sprites are cached in three boil variants and drawn with a sub-pixel jitter that changes on every drawing; wires are rolled clay snakes; pages are typeset by a small monospace typesetter with typewriter irregularity, punched holes and change bars. The film animates on twos: the picture is a pure function of time quantized to 12 drawings per second inside a 24 fps timeline, so the page and the export can never disagree. Rostrum (top-down) shots carry the manual pages; the opening, the Section V exhibit and the closing are shot from the front of the bench.

| File | Role |
| --- | --- |
| `tutorial.html`, `assets/tutorial/tutorial.css`, `player.js` | The page and player |
| `assets/tutorial/core.js` | Clock, clay shading, sprites, textures, typesetter, hands |
| `assets/tutorial/props.js` | Rocket, boards, servos, launcher, laptop, placards, stamps, Section V exhibits |
| `assets/tutorial/stage.js` | Binder, pages, dividers, camera, page turns |
| `assets/tutorial/scenes-a.js` … `scenes-v.js` | The scenes of the film and of the 9:16 cut |
| `assets/tutorial/content.js` | Every word of manual text, the glossary and the copy-panel commands |
| `assets/tutorial/timeline.js` | Generated: scenes, cues, events, chapters |
| `assets/tutorial/fonts.js`, `fonts/` | Courier Prime and Barlow Condensed subsets, SIL Open Font License |

**Sound.** The narration is a local neural voice, Kokoro-82M (Apache-2.0) through `kokoro-onnx`; no API key, no network service, and no credentials are involved. The score and every sound effect are synthesized in `tools/tutorial/build_audio.py` from scratch (Karplus–Strong pizzicato and bass, modal marimba, vibraphone and music box, a felt piano for Section V, analog pads, brush and typewriter percussion; binder rings, page turns, stamps, clay squish, pencil ticks, toggles, a soft brief buzzer, servo whirs). Music ducks under the voice, and drops out for "It refuses. Good."

**Timing.** `tools/tutorial/timeline.py` is the single source for picture, sound and captions. It places each narration line, lands beats on specific words using word timings from a local speech-recognition pass (`align_words.py`, which also prints what the voice actually said next to each caption), snaps every event to a drawing, and writes the timeline, captions and chapter files.

## Rebuild

From the repository root, with Python 3.11+, Node 22+, FFmpeg with libx264, and Playwright with Chromium:

```bash
python -m pip install kokoro-onnx soundfile scipy faster-whisper fonttools brotli
# Kokoro model files (Apache-2.0), downloaded once, not committed:
#   https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
#   kokoro-v1.0.onnx and voices-v1.0.bin into build/tts/ (or set KOKORO_MODEL_DIR)
python tools/tutorial/build_narration.py      # narration, one WAV per line
python tools/tutorial/align_words.py          # optional: listen check and word timings
python tools/tutorial/timeline.py             # timeline.js, captions, chapters
python tools/tutorial/build_audio.py          # score, sound design, mix → *.m4a
python tools/tutorial/build_fonts.py          # only if the on-screen character set changes
python tools/tutorial/frames.py main 123.7    # optional: stills for review
node tools/export_tutorial_film.mjs main       # → build/tutorial/project33-bench-manual.mp4
node tools/export_tutorial_film.mjs preflight60
```

Set `CHROME_PATH` to use an installed Chrome, `FFMPEG_PATH` for FFmpeg, and `PLAYWRIGHT_MODULE` as for the [marketing film](MARKETING_FILM.md). The exporter opens `tutorial.html` from disk, renders each frame at exactly `frame / 24` seconds, encodes one file per scene (an interrupted export resumes), joins them without re-encoding, then adds the soundtrack without touching the picture. Frames that share a drawing are identical by construction, so each drawing is rendered once.

The repository keeps a compressed 1280 × 720 copy of the main film. The full-quality 1920 × 1080 master is kept out of git history and attached to a GitHub release.

## Accessibility

Captions are on by default and available as WebVTT and SRT. The page view is a page-by-page manual with Previous and Next, a still for each chapter, the manual text as real, selectable HTML, the chapter's narration as text, and optional narration audio; it opens automatically when the visitor prefers reduced motion. All controls are native buttons and a range input with keyboard shortcuts. A poster and an MP4 with a captions track cover disabled JavaScript.
