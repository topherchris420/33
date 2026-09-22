.PHONY: evidence review evidence-demo
PYTHON ?= python

# Offline review: no model execution or hardware needed. Choose a new directory
# when retaining several runs; existing bundles are deliberately not overwritten.
REVIEW_OUTPUT ?= build/review
DEMO_OUTPUT ?= build/demo
review:
	$(PYTHON) -m evidence build --output "$(REVIEW_OUTPUT)"
	$(PYTHON) -m evidence verify "$(REVIEW_OUTPUT)"

evidence-demo:
	$(PYTHON) -m evidence demo --output "$(DEMO_OUTPUT)"
	$(PYTHON) -m evidence verify "$(DEMO_OUTPUT)/review"

evidence:
	$(PYTHON) -m pytest tests Firmware/tests -q
	$(PYTHON) mechanism/four_bar.py --emit docs/EVIDENCE/C1_four_bar_sweep.json
	$(PYTHON) materials/mass_rollup.py --emit docs/EVIDENCE/C4_mass_baseline.csv docs/EVIDENCE/C4_mass_optimized.csv
	$(PYTHON) Simulation/static_margin.py --emit docs/EVIDENCE/C5_static_margin.csv docs/EVIDENCE/C5_static_margin.png --ork "Simulation/Folding Stabilized Rocket.ork"
	$(PYTHON) mechanism/spring_sizing.py --emit docs/EVIDENCE/C6_spring_sweep.json
	$(PYTHON) Simulation/reliability_sweep.py --emit docs/EVIDENCE/C7_reliability.csv
	$(PYTHON) structures/fea_lite.py --emit docs/EVIDENCE/C8_clt.csv docs/EVIDENCE/C8_hinge_fos.md
	$(PYTHON) "CAD Files/FusionScripts/Project33FourBar/Project33FourBar.py" --export "CAD Files/Four Bar Linkage.step"
