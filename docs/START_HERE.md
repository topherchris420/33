# Start here

Project 33 is an open laboratory for a folding-fin rocket concept and its engineering evidence. Choose an entry point that fits the question you brought.

## Explore in a browser

No account, hardware, or software installation is needed for the published laboratory.

| Route | A useful first action | Follow the source |
|---|---|---|
| [Guided laboratory](https://topherchris420.github.io/33/lab/guided.html) | Try a lesson and inspect the explanation behind its answer. | [Laboratory guide](LIVING_LAB.md) |
| [3D workbench](https://topherchris420.github.io/33/lab/workbench.html) | Select a part, inspect its source category, then compare solid and section views. | [CAD assembly notes](CAD_ASSEMBLIES.md) |
| [Mechanism Lab](https://topherchris420.github.io/33/lab/mechanism.html) | Inspect the closure gap in the committed linkage sweep. | [C1 passport](claims/C1.md) |
| [Evidence Observatory](https://topherchris420.github.io/33/lab/observatory.html) | Choose a contradicted claim and follow its requirement and discrepancy links. | [Traceability](TRACEABILITY.md) |
| [Utility Bench Manual](https://topherchris420.github.io/33/lab/bench-manual.html) | Watch the film, then search the companion binder for an unfamiliar term. | [Manual guide](UTILITY_BENCH_MANUAL.md) |

The laboratory distinguishes source geometry, conceptual illustrations, and synthetic data. Its animations do not establish physical performance. Current evidence status is in the [claim passports](claims/README.md).

## Review without hardware

With Git and Python 3.11+ installed:

```bash
git clone https://github.com/topherchris420/33.git
cd 33
python -m evidence status
python -m evidence check
python -m evidence build --output build/review
python -m evidence verify build/review
```

After cloning, these commands use the standard library and run offline. Open `build/review/index.html`. A successful first review has three observable results:

- `check` exits 0 and reports no record-consistency findings or stale generated documents.
- The packet contains copied artifacts, record files, a manifest, and verification instructions.
- `verify` reports `bundle_integrity: verified`.

Contradicted claims and unmeasured quantities remain in that report. A consistent record can describe a failed requirement.

To check a packet on another machine, copy the entire packet directory, enter its `reviewer` subdirectory, and run `python -m evidence verify ..`. For independent verification, use reviewer code from a trusted checkout and a manifest digest received through a trusted channel. [Integrity and review scope](EVIDENCE_OBSERVATORY.md#what-a-packet-establishes).

## Work on the project

Use Python **3.11** and the pinned dependencies to match CI. Full tests include models and CAD, so install both requirement files in a virtual environment:

```bash
python -m venv .venv
```

Activate the environment with the command for your shell:

| Shell | Command |
|---|---|
| Linux/macOS Bash or Zsh | `source .venv/bin/activate` |
| Windows PowerShell | `.venv\Scripts\Activate.ps1` |
| Windows Command Prompt | `.venv\Scripts\activate.bat` |

Then run:

```bash
python -m pip install -r Firmware/requirements-test.txt -r requirements-evidence.txt
python tools/generate_protocol.py --check
python -m pytest tests Firmware/tests -q
python -m evidence reproduce
```

To check the complete generated record without Make:

```bash
python tools/build_bench_manual.py --check
python -m evidence check
python tools/review_figures.py --check
python tools/export_lab_data.py --check
python tools/build_altimeter_example.py --check
python tools/check_markdown_links.py
```

For a local laboratory preview, run `python tools/serve_lab.py`, open http://localhost:8000/lab/, and stop the server with Ctrl+C. The committed static assets are ready to serve; these pages do not require Jekyll. The repository's main `index.md` uses Jekyll and is built separately by GitHub Pages CI.

For a packet with attached test and reproduction records, use `make review-full`. For JavaScript and firmware checks, see [Testing](TESTING.md) and [Contributing](../CONTRIBUTING.md). The dashboard additionally needs Tkinter, supplied separately by some operating systems.

## Make a useful contribution

Choose one question and keep its evidence scope visible.

| Contribution | Start with | Reviewable outcome |
|---|---|---|
| Clarify a source or explanation | [Manual guide](UTILITY_BENCH_MANUAL.md), [architecture](ARCHITECTURE.md) | A precise correction linked to its source; regenerate any affected views |
| Investigate linkage assumptions | [C1](claims/C1.md), [D-002](DISCREPANCIES.md#d-002) | A reproducible model critique or a documented design question |
| Review stability formulations | [C5](claims/C5.md), [discrepancy register](DISCREPANCIES.md) | Explicit assumptions and a reproducible comparison |
| Improve software reliability | [Testing](TESTING.md), `tests/`, `Firmware/tests/` | A failing example and a bounded fix with regression coverage |
| Propose an inert experiment | [Pre-registrations](EVIDENCE_OBSERVATORY.md#predictions-measurements-and-pre-registration), [bench configuration](BENCH_CONFIGURATION.md) | A proposed method, interpretation rule, and required instrument provenance |

Before editing an evidence input, run `python -m evidence impact PATH`. Afterward, inspect changed artifacts and record freshness; [Contributing](../CONTRIBUTING.md#evidence-record-rules) describes the update process. Generated documents and derived laboratory data must be regenerated by their owning tools.

Automated contributors can propose experiments and record tooling snapshots. Registration of experiments, acceptance of sessions, and human review belong to named people. Physical quantities stay unmeasured until their records have been accepted through that process.

[README](../README.md) · [Roadmap](ROADMAP.md) · [Safety](SAFETY.md) · [Evidence Observatory](EVIDENCE_OBSERVATORY.md)
