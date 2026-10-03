"""Tests of the Monte Carlo simulation and of the three lessons (phase 2)."""

import numpy as np
import pytest

from montecarlo.simulation import run_simulation
from montecarlo.stats import summarize
from scenarios import lesson2, lesson3, lesson4
from validate import STATISTICS, standard_errors_by_repetition

N_LARGE = 100_000
LESSONS = {"lesson2": lesson2, "lesson3": lesson3, "lesson4": lesson4}


@pytest.fixture(scope="module")
def large_runs():
    """One simulation of 100,000 iterations per lesson, shared by the tests."""
    return {name: run_simulation(lesson.SCENARIO, N_LARGE) for name, lesson in LESSONS.items()}


def test_base_case_mode_gives_the_deterministic_npv():
    # Every input constant at its base case value: no uncertainty left.
    base_case_scenario = {
        **lesson2.SCENARIO,
        "inputs": {
            "price": {"dist": "constant", "value": 50},
            "demand": {"dist": "constant", "value": 15_000},
            "variable_cost": {"dist": "constant", "value": 30},
            "fixed_costs": {"dist": "constant", "value": 80_000},
        },
    }
    draws = run_simulation(base_case_scenario, 1_000)
    assert np.all(draws["npv"].round(2) == 33_973.09)


def test_same_seed_gives_the_same_results():
    first = run_simulation(lesson4.SCENARIO, 5_000, seed=42)
    second = run_simulation(lesson4.SCENARIO, 5_000, seed=42)
    other_seed = run_simulation(lesson4.SCENARIO, 5_000, seed=43)

    assert first.equals(second)
    assert not first.equals(other_seed)


def test_output_has_one_row_per_iteration():
    draws = run_simulation(lesson3.SCENARIO, 5_000)
    assert len(draws) == 5_000
    assert {"price", "demand", "volume", "variable_cost", "fixed_costs", "npv"} <= set(draws.columns)


def test_zero_correlation_reproduces_lesson_3():
    lesson4_without_correlation = {**lesson4.SCENARIO, "correlations": {("price", "demand"): 0.0}}
    with_zero = run_simulation(lesson4_without_correlation, 5_000)
    reference = run_simulation(lesson3.SCENARIO, 5_000)
    assert np.allclose(with_zero["npv"], reference["npv"])


def test_measured_correlation_is_close_to_the_input(large_runs):
    draws = large_runs["lesson4"]
    measured = np.corrcoef(draws["price"], draws["demand"])[0, 1]
    assert measured == pytest.approx(-0.5, abs=0.02)


def test_variable_cost_stays_independent(large_runs):
    draws = large_runs["lesson4"]
    assert abs(np.corrcoef(draws["price"], draws["variable_cost"])[0, 1]) < 0.01
    assert abs(np.corrcoef(draws["demand"], draws["variable_cost"])[0, 1]) < 0.01


def test_capped_volume_never_exceeds_capacity(large_runs):
    for name in ("lesson3", "lesson4"):
        draws = large_runs[name]
        assert draws["demand"].max() > 17_000  # demand itself can exceed capacity
        assert draws["volume"].max() <= 17_000
        assert np.all(draws["volume"] <= draws["demand"])


def test_lesson_2_has_no_capacity_limit(large_runs):
    draws = large_runs["lesson2"]
    assert np.array_equal(draws["volume"], draws["demand"])


def test_price_stays_within_pert_bounds_in_the_simulation(large_runs):
    for name in ("lesson3", "lesson4"):
        assert large_runs[name]["price"].between(44, 52).all()


def test_correlation_reduces_dispersion_but_barely_moves_the_mean(large_runs):
    # Natural hedge: when the price is low, demand tends to be high.
    lesson3_stats = summarize(large_runs["lesson3"]["npv"])
    lesson4_stats = summarize(large_runs["lesson4"]["npv"])

    assert lesson4_stats["sd"] < 0.9 * lesson3_stats["sd"]
    assert lesson4_stats["mean"] - lesson3_stats["mean"] == pytest.approx(-4_000, abs=1_500)


@pytest.mark.parametrize("name", LESSONS)
@pytest.mark.parametrize("reference_name", ["EXCEL_NOTES", "EXCEL_WORKBOOK"])
def test_results_match_the_excel_references(large_runs, name, reference_name):
    """Python (100,000 iterations) vs Excel (5,000 iterations).

    Tolerance: 3 standard errors of the difference, so that the test only
    fails on a real modelling gap and not on ordinary simulation noise.
    docs/validation.md reports the stricter 95 % verdicts.
    """
    lesson = LESSONS[name]
    reference = getattr(lesson, reference_name)
    python = summarize(large_runs[name]["npv"])
    se_excel = standard_errors_by_repetition(lesson.SCENARIO, 5_000, n_repetitions=200)

    for statistic in STATISTICS:
        se_python = se_excel[statistic] * np.sqrt(5_000 / N_LARGE)
        tolerance = 3 * np.sqrt(se_excel[statistic] ** 2 + se_python**2)
        assert python[statistic] == pytest.approx(reference[statistic], abs=tolerance), statistic
