"""Tests of the statistics and standard errors (phase 2)."""

import numpy as np
import pytest

from montecarlo.stats import margin_95, summarize


def test_summary_of_a_small_known_sample():
    npvs = np.array([-30.0, -10.0, 0.0, 10.0, 80.0])
    summary = summarize(npvs)

    assert summary["n"] == 5
    assert summary["mean"] == pytest.approx(10.0)
    assert summary["sd"] == pytest.approx(41.833, abs=0.001)  # sample SD, as STDEV.S
    assert summary["p50"] == pytest.approx(0.0)
    assert summary["p5"] == pytest.approx(-26.0)  # as PERCENTILE.INC
    assert summary["p95"] == pytest.approx(66.0)
    assert summary["prob_negative"] == pytest.approx(0.4)  # zero is not negative


def test_standard_errors_follow_the_formulas():
    npvs = np.random.default_rng(42).normal(10_000, 100_000, size=5_000)
    summary = summarize(npvs)
    p = summary["prob_negative"]

    assert summary["se_mean"] == pytest.approx(summary["sd"] / np.sqrt(5_000))
    assert summary["se_prob_negative"] == pytest.approx(np.sqrt(p * (1 - p) / 5_000))


def test_margin_of_error_at_95_percent():
    assert margin_95(1_000) == pytest.approx(1_960)
