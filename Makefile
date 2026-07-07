.PHONY: evidence
evidence:
	python -m pytest tests Firmware/tests -q
	python mechanism/four_bar.py --emit docs/EVIDENCE/C1_four_bar_sweep.json
	python materials/mass_rollup.py --emit docs/EVIDENCE/C4_mass_baseline.csv docs/EVIDENCE/C4_mass_optimized.csv
	python Simulation/static_margin.py --emit docs/EVIDENCE/C5_static_margin.csv docs/EVIDENCE/C5_static_margin.png --ork "Simulation/Folding Stabilized Rocket.ork"
	python mechanism/spring_sizing.py --emit docs/EVIDENCE/C6_spring_sweep.json
	python Simulation/reliability_sweep.py --emit docs/EVIDENCE/C7_reliability.csv
	python structures/fea_lite.py --emit docs/EVIDENCE/C8_clt.csv docs/EVIDENCE/C8_hinge_fos.md
	python "CAD Files/FusionScripts/Project33FourBar/Project33FourBar.py" --export "CAD Files/Four Bar Linkage.step"
