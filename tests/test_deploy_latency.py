import pytest
import csv
from pathlib import Path

def test_deploy_latency_requirements():
    csv_file = Path(__file__).resolve().parents[1] / "docs" / "EVIDENCE" / "C2_latency.csv"
    assert csv_file.exists(), "C2_latency.csv missing"
    
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
