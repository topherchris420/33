# Project 33

[![Project 33 — The record is the experiment. Conceptual cover with layered archival sheets.](docs/assets/readme/project33-cover.png)](https://topherchris420.github.io/33/lab/observatory.html)

**An open engineering laboratory and evidence record by Vers3Dynamics.**

[![Project checks](https://github.com/topherchris420/33/actions/workflows/ci.yml/badge.svg)](https://github.com/topherchris420/33/actions/workflows/ci.yml)
[![Laboratory and site checks](https://github.com/topherchris420/33/actions/workflows/marketing.yml/badge.svg)](https://github.com/topherchris420/33/actions/workflows/marketing.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Project 33 pairs an interactive browser laboratory with an inspectable engineering record. A folding-fin rocket concept is the case study; the record connects each claim to its sources, assumptions, discrepancies, and missing measurements. You can explore the visual laboratory, read the claim passports, or verify a portable review packet offline.

> **The rocket is the specimen. The record is the experiment.**

**[Explore the evidence](https://topherchris420.github.io/33/lab/observatory.html)** · **[Enter the laboratory](https://topherchris420.github.io/33/lab/)** · **[Start here](docs/START_HERE.md)**

[Current status](#current-status) · [First visit](#choose-your-first-visit) · [Offline review](#reproduce-the-review) · [Claim status](#claim-status) · [Development](#develop-and-verify) · [Contribute](#contribute)

*Cover: conceptual artwork, not a photograph, technical drawing, or test result. [Image sources and provenance](docs/assets/readme/README.md).*

## Current status

Project 33 began as an **inert bench-validation prototype**. The repository now also contains a guided-munition design study, alongside its browser laboratory and evidence-review software. That design material is modeled or implemented work; it does not establish a physically validated or deployable system.

**No physical measurement has been accepted into the evidence record. The project is not flight-tested.** Software checks, simulated outputs, and rendered assemblies each have a defined scope. None substitutes for an accepted physical measurement.

<!-- evidence:counts -->
**Record state:** 8 claims · 1 contradicted · 2 unresolved · 5 supported within stated limits · 0 accepted physical measurements · 7 open discrepancies of 27 · 8 of 8 predictions not measured.
<!-- /evidence:counts -->

The summary and claim table below are generated from the committed record. **Supported within stated limits** means support for the statement at its recorded evidence class; it does not mean hardware validation. Contradictions and unresolved questions remain visible.

| What is available | What it establishes |
|---|---|
| Browser laboratory | Read-only exploration of committed models and records |
| Claim passports and discrepancy register | The current statements, their sources, and recorded disagreements |
| Portable review packets | A reviewable snapshot with copied sources and integrity verification |
| Synthetic examples and illustrations | Tooling demonstrations and visual orientation, clearly labeled |
| Physical performance | **Not established** by the current evidence record |

## Choose your first visit

| You want to… | Start with | What you get |
|---|---|---|
| **See the idea** | [3D workbench](https://topherchris420.github.io/33/lab/workbench.html) | Rotate, explode, section, and inspect source-derived geometry |
| **Learn through exploration** | [Guided laboratory](https://topherchris420.github.io/33/lab/guided.html) | Six lessons and challenges grounded in committed data |
| **Watch the workshop** | [Utility Bench Manual film](https://topherchris420.github.io/33/lab/bench-manual.html) | A 4:09 claymation engineering companion with sound |
| **Review the research** | [Claim passports](docs/claims/README.md) and [discrepancies](docs/DISCREPANCIES.md) | Statements, assumptions, source files, and unresolved questions |
| **Reproduce the record** | [Offline review below](#reproduce-the-review) | A portable, locally verifiable review packet |
| **Contribute** | [First contribution routes](docs/START_HERE.md#make-a-useful-contribution) | Specific review questions and the checks for each kind of change |

The browser laboratory is read-only. Its values come from committed sources; synthetic data and conceptual illustrations are labeled, and unknown measurements stay **NOT MEASURED**. [How the laboratory is built](docs/LIVING_LAB.md).

## The evidence, made visible

[![The live Evidence Observatory interface: eight claims, one contradicted, two unresolved, five supported within stated limits, and zero accepted physical measurements.](docs/assets/readme/evidence-observatory.jpg)](https://topherchris420.github.io/33/lab/observatory.html)

*Actual screenshot of the published Evidence Observatory, captured 2026-11-15 UTC. This is a dated interface snapshot; the generated summary and [claim table](#claim-status) describe the committed record. [Capture provenance](docs/assets/readme/README.md).*

The Observatory lets you follow a claim into its requirements, cited artifacts, review history, and missing evidence. Its constellation, evidence ladder, and table show the same record in different forms. The offline review below makes that record available without the website.

<details>
<summary><b>Existing design illustrations</b> · modeled material</summary>

## Guided munition configuration

<a href="docs/MILITARY/README.md"><img src="docs/assets/munition_overview.svg" alt="Project 33 guided munition Phase 6 configuration card: side view with warhead bay, canards, folding fins, MIL-33 motor, CG and CP stations, and modeled performance summary."></a>

The configuration card is generated from committed sources by `tools/render_munition_card.py` — every dimension, station, and number comes from `design_point.json` and the evidence records, and the card carries its own MODELED label. Warhead loadouts are interchangeable at constant bay mass; the S&A fuze arms only on launch acceleration **and** canard-deployment confirmation **and** burn-time gate. [Militarization evidence tree](docs/MILITARY/README.md) · [Operator card](docs/MILITARY/OPERATOR_CARD.md).

<details>
<summary><b>Exploded assembly blueprint</b> (generated from the design point and the verified linkage kinematics)</summary>

<a href="docs/assets/munition_blueprint.svg"><img src="docs/assets/munition_blueprint.svg" alt="Project 33 guided munition exploded assembly blueprint: nose cone and S&A fuze, constant-mass warhead bay, avionics with GPS-aided IMU, canard ring, G-10 aft body with folding-fin section and MIL-33 motor, plus a verified four-bar linkage detail drawing with stations and the CG/CP ruler."></a>

Rendered by `tools/render_munition_blueprint.py`; the four-bar detail is drawn from the actual kinematic trace at the deployed-stop pose. All values MODELED. The interactive [3D workbench](https://topherchris420.github.io/33/lab/workbench.html) explodes the same geometry from the committed OpenRocket file.

</details>

</details>

<details>
<summary><b>Illustrated overview</b> · Issue B flier and PDF</summary>

## Project 33 · Issue B flier

<a href="docs/media/project33-issue-b-flier.pdf"><img src="assets/marketing/project33-flier-page-1.png" alt="Project 33 Issue B flier, page 1: numbered exploded assembly of the folding-fin concept. Open the complete two-page PDF." width="460"></a>

**[Open the complete flier · PDF · 2 pages](docs/media/project33-issue-b-flier.pdf)** · **[Download original PDF](docs/media/project33-issue-b-flier.pdf?raw=1)**

An illustrated overview of the concept and its proposed technology integrations. Issue B items are proposals; dimensions, stability, and cost shown in the artwork are design or estimated values. The [claim ledger](#claim-status) records the current evidence state. [File provenance](docs/media/README.md).

<details>
<summary>Preview sheet 2: technology integration and configurations</summary>

<a href="docs/media/project33-issue-b-flier.pdf"><img src="assets/marketing/project33-flier-page-2.png" alt="Project 33 Issue B flier, page 2: proposed technology integration, evidence-assistant authority order, and stowed, deployed, and launcher illustrations." width="640"></a>

</details>

</details>

## Reproduce the review

Python 3.11+ and Git are enough for this first workflow. After cloning, all commands below run offline with the Python standard library and require no hardware.

```bash
git clone https://github.com/topherchris420/33.git
cd 33
python -m evidence status
python -m evidence check
python -m evidence build --output build/review
python -m evidence verify build/review
```

Open `build/review/index.html` in your browser. It contains the claim assessment, copied sources, record files, provenance, and verification instructions. Choose a fresh output directory for every packet; existing reports are never overwritten. Verification checks file integrity. Scientific validity and physical performance require their own evidence.

After a revision, compare two snapshots:

```bash
python -m evidence build --output build/review-02
python -m evidence compare build/review build/review-02 --format markdown
```

The comparison identifies changed artifact bytes, record files, claim statuses, and evaluated requirement fields—even when an edited requirement still passes. Use `python -m evidence impact PATH` before an edit and `python -m evidence drift build/review` afterward to inspect affected claims. [Full review workflow and boundaries](docs/EVIDENCE_OBSERVATORY.md).

## The Living Engineering Laboratory

The laboratory gives the record a spatial form. Explore source-derived geometry, inspect model histories, follow claim relationships, and replay explicitly synthetic telemetry. Current results and historical discrepancies have separate records; use the claim passports for the present assessment.

| Room | Explore |
|---|---|
| [Workbench](https://topherchris420.github.io/33/lab/workbench.html) | Exploded assemblies, section planes, orthographic views, and source categories |
| [Mechanism Lab](https://topherchris420.github.io/33/lab/mechanism.html) | The committed linkage sweep and model-comparison views |
| [Evidence Observatory](https://topherchris420.github.io/33/lab/observatory.html) | Claims, evidence classes, discrepancies, and grounded questions |
| [Telemetry Theater](https://topherchris420.github.io/33/lab/telemetry.html) | Replay, timing gaps, duplicate samples, filtering, and spectra |
| [Instrumentation](https://topherchris420.github.io/33/lab/instruments.html) | Stale readings, alert ages, configuration identity, and local report inspection |
| [Research Archive](https://topherchris420.github.io/33/lab/archive.html) | Capabilities, provenance, source audit, and documents |

To explore locally, run `python tools/serve_lab.py`, then open **http://localhost:8000/lab/**. This serves the committed static files; no installation or site build is needed.

### V3D-TO-33-1 · Utility Bench Manual

[![Project 33 claymation Utility Bench Manual. Select the cover to play the full film with sound.](assets/marketing/bench-manual-poster.svg)](https://topherchris420.github.io/33/lab/bench-manual.html)

**[Play the complete film with sound](https://topherchris420.github.io/33/lab/bench-manual.html)** · **[Download MP4](project33-bench-manual-github-720p.mp4)** · **4:09 · 720p · 19.1 MB**

A miniature engineering workshop of annotated pages, conceptual assemblies, bench instruments, and session passports. The companion [searchable binder](https://topherchris420.github.io/33/lab/bench-manual.html#reference) has nine source-linked chapters, a glossary, printable pages, and personal reading marks. [Manual guide and source coverage](docs/UTILITY_BENCH_MANUAL.md).

The cover opens an HTML5 player on the project site; GitHub does not play repository-hosted MP4 files inline. The film is an illustrated orientation. Refer to the [claim ledger](#claim-status) for the project's evidence state.

<details>
<summary>Follow the film into the engineering record</summary>

| Sequence | Inspect the source |
|---|---|
| Description and assembly | [Architecture](docs/ARCHITECTURE.md) · [CAD assemblies](docs/CAD_ASSEMBLIES.md) |
| Offline evidence review | [Evidence Observatory](docs/EVIDENCE_OBSERVATORY.md) |
| Inert bench preflight | [Bench configuration](docs/BENCH_CONFIGURATION.md) · [Safety](docs/SAFETY.md) |
| Session passport | [Bench sessions](docs/BENCH_SESSIONS.md) · [Traceability](docs/TRACEABILITY.md) |
| Unresolved questions | [Discrepancies](docs/DISCREPANCIES.md) · [Claim passports](docs/claims/README.md) |

</details>

### Faceted 3D model

[![Faceted Project 33 model turning on its launcher and separating into parts. Open the interactive model.](assets/model/project33-faceted.gif)](https://topherchris420.github.io/33/model.html)

**[Open the interactive model](https://topherchris420.github.io/33/model.html)**: drag to turn, fold and deploy the fins, explode the assembly, toggle the launcher, and download OBJ or GLB.

*The faceted skin is a visual interpretation. Some dimensions follow the OpenRocket side view rather than the `.ork` file. [Sources and assumptions](docs/MODEL_3D.md).*

<details>
<summary>More visual studies: from frequency to form</summary>

[![Fourier epicycles trace the Project 33 blueprint, parts assemble, and the conceptual form rotates.](assets/marketing/project33-blueprint.gif)](assets/marketing/project33-blueprint.mp4)

*Concept visualization; no physical deployment is represented as measured.*

![Roll angle, roll rate, and controller output from an early telemetry dashboard export](Simulation/OpenRocket_3D_View.png)

*Not an OpenRocket view, despite the filename: a graph saved by an early version of the telemetry dashboard (`Firmware/dashboard.py`), showing roll angle, roll rate (×0.25), and the controller output shaded green and red over 1,096 samples. That version titled every saved graph "Rocket Flight Data". The session behind this one is not recorded, Project 33 is not flight-tested, and the plot is not part of the evidence record.*

[Watch the 80-second opening film](https://topherchris420.github.io/33/lab/cinematic.html) · [Open the procedural tutorial](https://topherchris420.github.io/33/tutorial.html)

</details>

## Claim status

<!-- evidence:claims-table -->
**Record state:** 8 claims · 1 contradicted · 2 unresolved · 5 supported within stated limits · 0 accepted physical measurements · 7 open discrepancies of 27 · 8 of 8 predictions not measured.

| Claim | Subject | Status | Strongest accepted evidence | Failing or disputed requirements | Open discrepancies |
|---|---|---|---|---|---|
| [C1](docs/claims/C1.md) | Folding-fin mechanism model | **SUPPORTED WITHIN STATED LIMITS** | MODEL ONLY | none failing | none |
| [C2](docs/claims/C2.md) | Deployment timing | **UNRESOLVED** | IMPLEMENTATION ONLY | none failing | D-018, D-024 |
| [C3](docs/claims/C3.md) | CAD generator software | **SUPPORTED WITHIN STATED LIMITS** | IMPLEMENTATION ONLY | none failing | none |
| [C4](docs/claims/C4.md) | Material mass accounting | **UNRESOLVED** | MODEL ONLY | none failing | D-022 |
| [C5](docs/claims/C5.md) | Static-stability model | **SUPPORTED WITHIN STATED LIMITS** | MODEL ONLY | none failing | D-023 |
| [C6](docs/claims/C6.md) | Spring margin consistency | **SUPPORTED WITHIN STATED LIMITS** | MODEL ONLY | none failing | none |
| [C7](docs/claims/C7.md) | Deployment reliability evidence | **SUPPORTED WITHIN STATED LIMITS** | MODEL ONLY | none failing | none |
| [C8](docs/claims/C8.md) | Structural claim boundaries | **CONTRADICTED** | MODEL ONLY | R-C8-MODULUS NOT SATISFIED | none |

<!-- /evidence:claims-table -->

Each passport states the claim, its assumptions, its evidence classes, and the next measurement or review it needs. The [traceability matrix](docs/TRACEABILITY.md) connects requirements to implementations, tests, and predictions.

### Read the record with its limits

- **Current and historical results are distinct.** Resolved discrepancies remain in the archive; an earlier failed result is not automatically the current claim status.
- **Claim status and evidence class answer different questions.** A supported model claim can still have no accepted physical measurement.
- **Integrity and validity are separate.** Matching file hashes establish that a packet has not changed relative to its manifest, not that its scientific interpretation is correct.
- **Unknown stays unknown.** Missing measurements, instrument provenance, and human acceptance cannot be supplied by a rendering or an automated summary.

The [Evidence Observatory guide](docs/EVIDENCE_OBSERVATORY.md) explains these distinctions. The [discrepancy register](docs/DISCREPANCIES.md) retains both open and resolved entries, while the [failure archive](evidence/archive/index.json) preserves superseded material.

## System components

| Component | Source | Evidence today |
|---|---|---|
| Mechanical and stability models | `mechanism/`, `materials/`, `structures/`, `Simulation/` | Analytical or simulated outputs, reproduced in CI |
| CAD and geometry tools | `CAD Files/` | Design implementation; NACA generator software-tested |
| Rocket and launcher firmware | `Firmware/Rocket/`, `Firmware/Launcher/` | Compiles in CI; physical behavior unmeasured |
| Dashboard and status board | `Firmware/dashboard.py`, `Firmware/ground_status.py` | Raw capture, replay, quality checks, and source-pinned fault interpretation |
| Standalone USB monitors | [USB instrumentation guide](docs/USB_BENCH_MONITOR.md) | Dedicated observer firmware, capture/replay, and identity diagnostics |
| Pressure data review | [Model-rocket review guide](docs/MODEL_ROCKET_REVIEW.md) | Relative-height and vertical-rate estimates, synthetic recovery markers; physical recovery unimplemented |
| Evidence Observatory | `evidence/` | Offline packets, integrity checks, claim assessment, and change impact |

[Architecture](docs/ARCHITECTURE.md) · [Protocol](docs/PROTOCOL.md) · [Wiring](docs/WIRING.md) · [Technology map](docs/TECHNOLOGY_INTEGRATION.md) · [Hardware integration plan](docs/HARDWARE_INTEGRATION_PLAN.md)

## Develop and verify

Use Python **3.11** to match CI. The standard-library review above also supports later Python versions; generated numeric fixtures can differ between versions. Create a virtual environment before installing the pinned model and test dependencies.

```bash
python -m venv .venv
```

Activate it with `source .venv/bin/activate` on Linux/macOS or `.venv\Scripts\Activate.ps1` in Windows PowerShell, then:

```bash
python -m pip install -r Firmware/requirements-test.txt -r requirements-evidence.txt
python tools/generate_protocol.py --check
python -m pytest tests Firmware/tests -q
python -m evidence reproduce
```

Run `make check` for all generated-view and record checks. `make review-full` attaches test and reproduction records to a new portable packet. For commands without Make, laboratory checks, and firmware setup, see [Testing](docs/TESTING.md) and [Start here](docs/START_HERE.md#work-on-the-project).

<details>
<summary>Firmware builds, dashboard, and bench workflow</summary>

Install PlatformIO separately with `python -m pip install -r Firmware/requirements-platformio.txt`. Copy `Firmware/Launcher/src/wifi_config.h.example` to `Firmware/Launcher/src/wifi_config.h` and configure it locally; the destination is git-ignored.

```bash
pio run -d Firmware/Rocket
pio run -d Firmware/Launcher
```

The dashboard runs with `python Firmware/dashboard.py` and requires Tkinter. It writes raw session folders under `Firmware/TestSessions/` (git-ignored). The [user guide](docs/USER_GUIDE.md) covers setup; [bench sessions](docs/BENCH_SESSIONS.md) explains declaration, passport creation, review, and human acceptance.

Prepare configuration-bound observation records with `python -m evidence bench init --output build/bench-plan`. See [bench configuration](docs/BENCH_CONFIGURATION.md) for templates, instrument provenance, and readiness packets.

For a review distribution containing firmware builds, run records, hashes, and a release-blocker report, see [release readiness](docs/RELEASE_READINESS.md). Fusion users can install the script with `python tools/install_fusion_script.py` and run `Project33NacaFin` from **Utilities → Scripts and Add-Ins**.

</details>

## Cost

<!-- evidence:cost -->
Estimated prototype subtotal: **$187** from 14 BOM lines (14 estimates, 0 purchased prices recorded, source dates not recorded, shipping and spares excluded). An estimate is not a purchase record; see [BOM](docs/BOM.md) and D-021.
<!-- /evidence:cost -->

## Contribute

A useful contribution closes a specific uncertainty: reproduce a discrepancy, inspect an assumption, improve a test, clarify a source, or propose an inert experiment. The [contribution guide](CONTRIBUTING.md) describes record rules and review requirements; [Start here](docs/START_HERE.md#make-a-useful-contribution) maps tasks to the relevant sources.

The project advances through **analytical model → software reproduction → synthetic test → inert bench setup → inert physical measurement → repeated measurement → independent review**. Physical evidence requires named human acceptance. Automated tools may interpret the record and propose experiments; they cannot accept sessions or invent measurements. [Safety boundary](docs/SAFETY.md).

<details>
<summary>Repository map</summary>

| Path | Purpose |
|---|---|
| `evidence/` | Claim catalog, requirements, predictions, sessions, measurements, reviews, and failure archive |
| `docs/claims/` | Generated claim passports |
| `docs/TRACEABILITY.md`, `docs/DISCREPANCIES.md` | Generated requirement, prediction, and discrepancy views |
| `docs/EVIDENCE/` | Committed model outputs and plots |
| `mechanism/`, `materials/`, `structures/`, `Simulation/` | Analytical and simulation models |
| `CAD Files/` | Fusion archives, geometry generators, and scripts |
| `Firmware/` | ESP32 firmware, dashboard, status board, and tests |
| `protocol/` | Canonical protocol and source-pinned status model |
| `tools/` | Generators, checkers, laboratory server, and packaging |
| `lab/` | Static engineering laboratory and derived data views |
| `tests/` | Regression, adversarial, mathematical, and browser checks |

</details>

Project 33 is published under the [MIT License](LICENSE).

**[Project site](https://topherchris420.github.io/33/)** · **[Project Status](docs/PROJECT_STATUS.md)** · **[Paper Alignment](docs/PAPER_ALIGNMENT.md)** · **[Roadmap](docs/ROADMAP.md)** · **[Report a security issue](SECURITY.md)**

*Build a model. Make a prediction. Measure the difference. Keep the record honest.*
