"""Report-calculation checks for the C2 timing fixture.

The fixture is synthetic. These tests exercise the statistics used to summarize
a timing capture; they are not a timing benchmark and cannot satisfy the
hardware jitter requirement R-C2-JITTER, which requires a physical measurement.
"""

import csv
import math
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / "docs" / "EVIDENCE" / "C2_latency.csv"


def nearest_rank(values, fraction):
    ordered = sorted(values)
    return ordered[max(math.ceil(fraction * len(ordered)) - 1, 0)]


def load():
    with FIXTURE.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_fixture_identifies_itself_as_synthetic_in_every_row():
    # The columns match Firmware/Rocket/tests/bench_deploy_isr.ino output, so the
    # label must travel with the data, not only in the evidence catalog.
    rows = load()
    assert rows
    assert {row["origin"] for row in rows} == {"synthetic-fixture"}


def test_jitter_column_is_consistent_with_requested_and_actual():
    for row in load():
        assert int(row["jitter_us"]) == abs(int(row["actual_us"]) - int(row["requested_us"]))


def test_nearest_rank_percentile_on_small_samples():
    values = list(range(1, 22))
    assert nearest_rank(values, 0.5) == 11
    # With 21 samples the 99.9th percentile is simply the maximum: a tail
    # bound cannot be estimated from this few samples.
    assert nearest_rank(values, 0.999) == 21
