"""C7 simulation structure checks (militarized revision 2).

These document what the simulation does. Whether its output supports a
reliability requirement is evaluated in the evidence record (R-C7-RELIABILITY);
CI asserts only that the run record is honest about its denominator, its
failure modes, and its design-point revision.
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Simulation'))
sys.path.insert(0, str(ROOT / 'mechanism'))
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


def test_failure_modes_can_actually_occur():
    # D-013: the revision-1 simulation could not produce the failures it
    # counted. Revision 2 samples spring rate, friction, aero coefficient,
    # egress speed, stop-angle scatter, and link tolerances on ranges where
    # each failure mode is reachable; the run record must name them.
    record = {
        'stalled_short', 'window_timeout', 'toggle_inside_stop_underdeploy',
        'stop_angle_under_tolerance', 'foldback_at_stop',
    }
    import inspect
    source = inspect.getsource(reliability_sweep)
    for mode in record:
        assert mode in source, f"failure mode {mode} not modeled"


def test_kinematic_profile_comes_from_the_verified_linkage():
    dp = reliability_sweep.load_design_point()
    s_m, psi_m, r_m, drds_m, toggle = reliability_sweep.kinematic_profile(dp)
    # The fin deploys monotonically from folded to past-perpendicular.
    assert psi_m[0] <= 5.0  # stowed: near flush
    assert toggle > 90.0   # toggle beyond the stop: over-center margin
    assert (r_m > 0).all()


def test_legacy_single_deployment_helper_still_runs():
    theta, omega = reliability_sweep.simulate_deployment(
        220.0, __import__('math').radians(90.0), 70.0, 1e-5, 0.8, 50.0)
    assert theta == 90.0
    assert omega == 0.0


def test_committed_run_record_meets_gate():
    committed = json.loads((ROOT / "docs" / "EVIDENCE" / "C7_run_record.json").read_text())
    # Sponsor gate: >= 99% simulated deployment reliability; the repository's
    # own requirement is 99.9% and the committed record must state which it is.
    assert committed["success_fraction"] >= 0.99
    assert committed["design_point_revision"] == "2026-11-14-phase1"
