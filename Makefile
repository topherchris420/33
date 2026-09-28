.PHONY: evidence review review-full evidence-demo check reproduce docs
PYTHON ?= python

# Offline review: standard library only; no model execution or hardware needed.
# Existing outputs are deliberately never overwritten: choose a new directory,
# e.g. make review REVIEW_OUTPUT=build/review-02.
REVIEW_OUTPUT ?= build/review
DEMO_OUTPUT ?= build/demo
FULL_OUTPUT ?= build/review-full

review:
	$(PYTHON) -m evidence build --output "$(REVIEW_OUTPUT)"
	$(PYTHON) -m evidence verify "$(REVIEW_OUTPUT)"

# Strict record check: prediction drift, stale reviews, failed consistency,
# stale generated documents, and stale review figures all fail.
check:
	$(PYTHON) -m evidence check
	$(PYTHON) tools/review_figures.py --check

evidence-demo:
	$(PYTHON) -m evidence demo --output "$(DEMO_OUTPUT)"
	$(PYTHON) -m evidence verify "$(DEMO_OUTPUT)/review"

# Regenerate every model output in a temporary directory and compare values
# with the committed artifacts (needs requirements-evidence.txt).
reproduce:
	$(PYTHON) -m evidence reproduce --record build/reproduction.json

# A review packet with the test run record and the reproduction record attached.
review-full:
	mkdir -p build
	$(PYTHON) -m pytest tests Firmware/tests -q --junitxml=build/pytest.xml
	$(PYTHON) -m evidence reproduce --record build/reproduction.json
	$(PYTHON) -m evidence build --output "$(FULL_OUTPUT)" --execution-record build/pytest.xml --reproduction-record build/reproduction.json
	$(PYTHON) -m evidence verify "$(FULL_OUTPUT)"

# Regenerate record views and review figures after editing evidence/*.json.
docs:
	$(PYTHON) -m evidence docs
	$(PYTHON) tools/review_figures.py

# Local only: regenerate committed model outputs in place. Afterwards run
# `make check`; any changed output drifts from its registered predictions and
# makes dependent reviews stale, which is the point.
evidence:
	$(PYTHON) mechanism/four_bar.py --emit docs/EVIDENCE/C1_four_bar_sweep.json
	$(PYTHON) materials/mass_rollup.py --emit docs/EVIDENCE/C4_mass_baseline.csv docs/EVIDENCE/C4_mass_optimized.csv
	$(PYTHON) Simulation/static_margin.py --emit docs/EVIDENCE/C5_static_margin.csv docs/EVIDENCE/C5_static_margin.png --ork "Simulation/Folding Stabilized Rocket.ork"
	$(PYTHON) Simulation/barrowman_crosscheck.py --ork "Simulation/Folding Stabilized Rocket.ork" --reference-csv docs/EVIDENCE/C5_static_margin.csv --emit docs/EVIDENCE/C5_barrowman_crosscheck.json
	$(PYTHON) mechanism/spring_sizing.py --emit docs/EVIDENCE/C6_spring_sweep.json
	$(PYTHON) Simulation/reliability_sweep.py --emit docs/EVIDENCE/C7_reliability.csv
	$(PYTHON) structures/fea_lite.py --emit docs/EVIDENCE/C8_clt.csv docs/EVIDENCE/C8_hinge_fos.json
	$(PYTHON) "CAD Files/FusionScripts/Project33FourBar/Project33FourBar.py" --export "CAD Files/Four Bar Linkage.step"
