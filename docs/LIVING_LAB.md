# The Living Engineering Laboratory

The project site's interactive laboratory lives in [`lab/`](../lab/index.html). It is a static,
read-only site served by GitHub Pages with no build step and no CDN. This page documents what it
is built from, how its provenance is enforced, what it deliberately does not do, and how to work on it.

> **Make the rigor entertaining, not the other way round.** Every number the laboratory shows comes
> from a committed file. Where a source is silent, the laboratory says NOT SPECIFIED or NOT MEASURED.

## Information categories

Every page, panel, and 3D asset carries a category tag, distinguished by shape as well as colour:

| Category | Meaning |
|---|---|
| Historical aerospace engineering | General aviation human-machine-interface practice, shown with original, non-operational illustrations. Nothing is reproduced from the F-117A supplement (see [source rights](#source-rights-audit)). |
| Project 33 research | Read from the repository: geometry, models, firmware architecture, claims, contradictions, validation records. |
| Conceptual exploration | Original educational models that explain a principle. Not verified hardware and not a Project 33 design. |
| Synthetic data | Fabricated to exercise software. Never supports a physical or performance claim. |

3D assets carry one of four asset classes: **source CAD** (tessellated from a committed STEP file),
**source model** (generated from a committed model's parameters), **reconstructed concept**
(arranged by the lab where no source records it, such as explosion paths), and
**educational illustration**. The Fusion 360 archives are shown as **not translated**.

## Rooms

| Page | What it does | Built from |
|---|---|---|
| [Workbench](../lab/workbench.html) | Rotate, explode (deterministic, reversible, sequential), five renderings (clay, solid, wireframe, blueprint with hidden lines, x-ray), section planes with hatching, orthographic and standard views, measurement, part inspector, stamped screenshots, fullscreen, keyboard shortcuts, deep links. | OpenRocket design file, STEP export, NACA generator, Fusion archive inventory |
| [Mechanism Lab](../lab/mechanism.html) | The four-bar closure failure as a 3D clay scene with the coupler/output circle gap, a gap chart, all 81 recorded variants, three-depth mathematics, a conceptual sandbox, and a model comparison studio (C5, C6, D-009, D-010). | `docs/EVIDENCE/C1_four_bar_sweep.json`, `mechanism/four_bar.py`, C5/C6 outputs, discrepancy register |
| [Evidence Observatory](../lab/observatory.html) | Claim constellation, evidence ladder, passports, discrepancy register, grounded questions. | `python -m evidence` assessment |
| [Telemetry Theater](../lab/telemetry.html) | Clock domains, gaps, duplicates, filtering, spectra, replay, and a 3D systems architecture with no transmit path. | `python -m evidence demo` fixture, a declared seeded generator, architecture docs, `protocol/ground_status_model.json` |
| [Instrumentation](../lab/instruments.html) | A conceptual clay cockpit with original generic symbology, an information-architecture chain with stale, missing, and inconsistent sources, and failure dependencies compared with Project 33's own source-pinned model. | Original content plus `protocol/ground_status_model.json` |
| [Opening film](../lab/cinematic.html) | An 80-second procedural clay film with captions, synthesized sound, optional browser-voice narration, chapters, skip, and replay. The whole film is a pure function of time. | The same OpenRocket geometry and evidence record |
| [Guided Lab](../lab/guided.html) | Six lessons with clay vignettes and challenges checked against committed data. | All of the above |
| [Research Archive](../lab/archive.html) | Capability matrix, candidate observations, provenance digests, the source-rights audit, documents, and commands. | Derived-view manifests |

## Provenance

The laboratory reads canonical records directly (`evidence/*.json`, `protocol/*.json`,
`docs/EVIDENCE/*`). Where a record needs translating for the browser, a derived view in `lab/data/`
is written by a tool and pins the SHA-256 of every input it used:

| View | Generator | Source |
|---|---|---|
| `lab/data/evidence.json` | [`tools/export_lab_data.py`](../tools/export_lab_data.py) | The `evidence/assess.py` assessment of the committed record, minus build provenance |
| `lab/data/openrocket.json` | `tools/export_lab_data.py` | `Simulation/Folding Stabilized Rocket.ork` and the archived pre-retune model, with OpenRocket axial-method stations |
| `lab/data/naca0012.json` | `tools/export_lab_data.py` | `naca_4digit_coordinates()` from the tested generator |
| `lab/data/telemetry_fixture.json` | `tools/export_lab_data.py` | `python -m evidence demo` |
| `lab/data/cad/four_bar.json` | [`tools/cad_to_web.py`](../tools/cad_to_web.py) | `CAD Files/Four Bar Linkage.step`, tessellated with OCP; pin spacing measured from cylindrical faces |
| `lab/data/cad/archives.json` and previews | `tools/cad_to_web.py` | The three `.f3z` archives, inventoried with [`tools/sab_inventory.py`](../tools/sab_inventory.py) |

`python tools/export_lab_data.py --check` (run by `make check`) regenerates the standard-library views
in memory, compares them byte for byte, and verifies the CAD manifest by digest. Change any input and
the check fails until the view is regenerated. The JavaScript four-bar port is verified against the
committed sweep and against `mechanism/four_bar.py` on configurations that do close
(`tests/lab_math.test.mjs`).

### Why the Fusion archives are not converted

Fusion stores bodies as Autodesk ShapeManager B-rep (`ASM BinaryFile4`) inside zstd-compressed
members, and occurrence placements in proprietary design streams. The repository has no reviewed
translator for that format; a partial or unplaced conversion would draw an assembly the record cannot
support. The archives are therefore inventoried (component names, versions, B-rep statistics,
Autodesk's embedded preview images). To unlock true assembly geometry, export STEP from Fusion 360
into `CAD Files/exports/` and run `python tools/cad_to_web.py`; the workbench translates it the same
way as the four-bar file.

## Candidate observations

Building the laboratory surfaced two items for human review. They are **not** in the discrepancy
register; the [archive](../lab/archive.html#observations) recomputes both live.

1. **LAB-OBS-1 (C5).** `Simulation/static_margin.py` reads `<position type="bottom">0.0</position>`
   as an offset from the top of the parent tube and records `X_f = 0.381 m`. Under OpenRocket's
   axial-method rules the aft fins' root leading edge is at `0.471 m`. Its effect on either CP
   formulation is not computed; that would be a third model.
2. **LAB-OBS-2 (C1).** With the recorded ground (25 mm) and input (15 mm) links, no integer
   coupler/output pair from 1 to 200 mm both closes over 0–92° and keeps the transmission angle within
   40–140°. D-002 asks which dimensions were intended; this suggests the ground and input need review
   too.

## Source rights audit

The supplied *OCIP Supplement to the Utility Flight Manual, F-117A* (TO 1F-117A-1A, Issue B,
3 February 1992) carries a distribution statement limiting it to U.S. Government agencies, states
that reproduction of its information or illustrations for non-military use is not permitted, and
carries handling, destruction, and disclosure notices. It also describes operational procedures and
weapon-system equipment. Therefore:

- the scan is not committed, published, linked, or redistributed;
- no text, figure, symbol, display format, procedure, value, or diagram from it appears in the site;
- the instrumentation exhibits use general, widely published human-factors principles with original
  synthetic examples, labelled as not an F-117A format;
- the workshop's aircraft miniature is an original low-poly prop of a retired, publicly displayed shape,
  with a placard stating it is not a Project 33 component and carries no data from the manual;
- no technical compatibility between the aircraft and Project 33 is implied.

Keep the PDF out of the repository and its history; obtain written redistribution permission before
any future use.

## Safety and isolation

The laboratory has no WebSocket, WebSerial, WebUSB, WebBluetooth, WebHID, WebRTC, beacon, or
cross-origin request code. [`tests/test_lab_isolation.py`](../tests/test_lab_isolation.py) scans every
laboratory script and fails if one appears. Firmware, interlocks, the safety-gate registry, and the
evidence record are unchanged by the laboratory. See [Safety](SAFETY.md).

## Working on the laboratory

```bash
python tools/serve_lab.py                 # http://localhost:8000/lab/ (no-store caching)
python tools/export_lab_data.py           # regenerate derived views after a record change
python tools/export_lab_data.py --check   # verify (also part of make check)
python tools/cad_to_web.py                # CAD views; needs cadquery and zstandard
node --test tests/lab_math.test.mjs       # math ports against the Python models
python -m pytest tests/test_lab_data.py tests/test_lab_isolation.py -q
node tests/lab_browser/workbench.mjs      # browser interaction tests (Playwright; server on :8100)
```

Browser tests exist for every page in `tests/lab_browser/`. Each exercises every control, fails on any
console error, checks mobile overflow, and saves screenshots. Under software WebGL (SwiftShader) they
take several minutes per page.

Design tokens and shared components live in `lab/css/lab.css` and `lab/js/core/`. Vendored libraries
and their digests are listed in [`lab/lib/README.md`](../lab/lib/README.md). The renderer drops shadows
and pixel ratio on software rasterisers; scenes render on demand.
