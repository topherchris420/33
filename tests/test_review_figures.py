"""Committed review figures must match what the tested geometry code renders."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import review_figures


def test_review_figures_are_current():
    assert review_figures.main(["--check"]) == 0


def test_loop_closure_figure_reports_the_model_result():
    svg = review_figures.loop_closure()
    assert "cannot close at any drive angle" in svg
    assert "29.6 mm" in svg
