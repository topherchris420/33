"""C7 simulation structure checks.

These document what the simulation does. Whether its output supports a
reliability requirement is evaluated in the evidence record (R-C7-RELIABILITY,
discrepancy D-013), not asserted by CI.
"""

import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Simulation'))
import reliability_sweep


def test_run_record_states_its_denominator(tmp_path):
    rate, failures = reliability_sweep.run_monte_carlo(num_trials=200, seed=42, output_dir=tmp_path)
    record = json.loads((tmp_path / "C7_run_record.json").read_text())
    with (tmp_path / "C7_reliability.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert record["trials"] == 200
    assert record["successes"] + record["failures"] == record["trials"]
    assert len(rows) == record["failures"] == len(failures)
    assert record["seed"] == 42
    assert record["success_fraction"] == rate


def test_locked_trials_report_zero_final_rate_by_construction():
    # When the toggle event fires, omega_final is forced to 0, so the
    # |omega| <= 50 deg/s success test cannot fail for a locked trial.
    theta, omega = reliability_sweep.simulate_deployment(
        220.0, np.radians(90.0), 70.0, (1 / 3) * 0.015 * 0.060 ** 2, 0.8, 50.0)
    assert omega == 0.0
    assert abs(theta - 90.0) < 0.1
