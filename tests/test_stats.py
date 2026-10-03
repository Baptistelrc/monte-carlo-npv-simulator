"""Tests of the statistics and standard errors (phase 2)."""

import numpy as np
import pytest

from montecarlo.model import annuity_factor
from montecarlo.stats import margin_95, summarize, tornado
from scenarios import lesson2, lesson3


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


BASE_INPUTS = {"price": 50.0, "demand": 15_000, "variable_cost": 30.0, "fixed_costs": 80_000}


def test_tornado_of_lesson_2():
    table = tornado(lesson2.SCENARIO, BASE_INPUTS)

    # Fixed costs are constant: no swing, so only three inputs remain.
    assert list(table["input"]) == ["price", "demand", "variable_cost"]
    assert list(table["swing"]) == sorted(table["swing"], reverse=True)

    # Price: P10 and P90 of Normal(50, 2.5) are 50 -/+ 1.2816 x 2.5.
    price = table.iloc[0]
    assert price["p10"] == pytest.approx(50 - 1.2816 * 2.5, abs=0.001)
    assert price["p90"] == pytest.approx(50 + 1.2816 * 2.5, abs=0.001)
    # Other inputs at base case: NPV = -800,000 + (15,000 x (price - 30) - 80,000) x 3.7908
    annuity = annuity_factor(0.10, 5)
    for column, value in (("npv_at_p10", price["p10"]), ("npv_at_p90", price["p90"])):
        expected = -800_000 + (15_000 * (value - 30) - 80_000) * annuity
        assert price[column] == pytest.approx(expected)


def test_tornado_a_higher_cost_lowers_the_npv():
    table = tornado(lesson2.SCENARIO, BASE_INPUTS).set_index("input")
    assert table.loc["variable_cost", "npv_at_p90"] < table.loc["variable_cost", "npv_at_p10"]
    assert table.loc["price", "npv_at_p90"] > table.loc["price", "npv_at_p10"]


def test_tornado_respects_the_capacity_limit():
    # Demand P90 = 16,922 is below the 17,000 capacity; with a capacity of
    # 16,000 the upside of demand is cut.
    tight_capacity = {**lesson3.SCENARIO, "capacity": 16_000}
    normal = tornado(lesson3.SCENARIO, BASE_INPUTS).set_index("input")
    capped = tornado(tight_capacity, BASE_INPUTS).set_index("input")
    assert capped.loc["demand", "npv_at_p90"] < normal.loc["demand", "npv_at_p90"]
    assert capped.loc["demand", "npv_at_p10"] == pytest.approx(normal.loc["demand", "npv_at_p10"])
