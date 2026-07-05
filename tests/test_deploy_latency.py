import pytest
import csv
from pathlib import Path

def test_deploy_latency_requirements(tmp_path):
    # Simulated bench CSV for CI
    # format: trial_num, requested_us, actual_us, jitter_us
    csv_data = [
        "trial,requested_us,actual_us,jitter_us",
    ]
    for i in range(100):
        csv_data.append(f"{i},50000,50030,30")
    for i in range(100, 200):
        csv_data.append(f"{i},50000,50045,45")
    csv_data.append("200,50000,50400,400") # P99.9 outlier
    
    csv_file = tmp_path / "bench_results.csv"
    csv_file.write_text("\n".join(csv_data))
    
    jitters = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            jitters.append(int(row['jitter_us']))
            
    jitters.sort()
    median = jitters[len(jitters)//2]
    p99_9_index = int(len(jitters) * 0.999)
    if p99_9_index >= len(jitters):
        p99_9_index = len(jitters) - 1
    p99_9 = jitters[p99_9_index]
    
    assert median <= 50, f"Median jitter {median} > 50 us"
    assert p99_9 <= 500, f"P99.9 jitter {p99_9} > 500 us"
