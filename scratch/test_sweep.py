import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Simulation'))
import reliability_sweep

sr, fails = reliability_sweep.run_monte_carlo(num_trials=5, seed=42)
print(f"Success Rate: {sr}")
for f in fails:
    print(f)
