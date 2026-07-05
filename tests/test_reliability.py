import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Simulation'))
import reliability_sweep
import pytest

def test_reliability_exceeds_threshold():
    # Use fewer trials for test speed, or 10,000 if fast enough.
    # 10,000 might take 10 seconds. Let's test with 500 for the test suite, 
    # and the full 10k is run by the Makefile.
    sr, fails = reliability_sweep.run_monte_carlo(num_trials=500, seed=42)
    assert sr >= 0.999, f"Success rate {sr} < 0.999"
