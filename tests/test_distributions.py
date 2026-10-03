"""Tests of the input distributions (phase 2)."""

import numpy as np
import pytest

from montecarlo import distributions
from scenarios.lesson3 import VARIABLE_COST_HISTORY

N = 100_000


def draw(spec, seed=42):
    """Draws from a distribution: uniform numbers through the inverse CDF."""
    uniforms = np.random.default_rng(seed).random(N)
    return distributions.from_spec(spec).ppf(uniforms)


def test_pert_shape_of_lesson_3():
    assert distributions.pert_shape(44, 50, 52) == pytest.approx((4.0, 2.0))


def test_pert_draws_stay_within_min_and_max():
    draws = draw({"dist": "pert", "min": 44, "mode": 50, "max": 52})
    assert draws.min() >= 44
    assert draws.max() <= 52


def test_pert_mean():
    draws = draw({"dist": "pert", "min": 44, "mode": 50, "max": 52})
    expected = (44 + 4 * 50 + 52) / 6  # 49.33: below the mode, the PERT is asymmetric
    assert draws.mean() == pytest.approx(expected, abs=0.02)


def test_triangular_bounds_and_mean():
    draws = draw({"dist": "triangular", "min": 44, "mode": 50, "max": 52})
    assert draws.min() >= 44
    assert draws.max() <= 52
    assert draws.mean() == pytest.approx((44 + 50 + 52) / 3, abs=0.02)


def test_normal_mean_and_sd():
    draws = draw({"dist": "normal", "mean": 15_000, "sd": 1_500})
    assert draws.mean() == pytest.approx(15_000, abs=20)
    assert draws.std(ddof=1) == pytest.approx(1_500, abs=20)


def test_lognormal_is_described_by_its_own_mean_and_sd():
    draws = draw({"dist": "lognormal", "mean": 30, "sd": 1.5})
    assert draws.min() > 0
    assert draws.mean() == pytest.approx(30, abs=0.02)
    assert draws.std(ddof=1) == pytest.approx(1.5, abs=0.02)


def test_constant_always_returns_its_value():
    draws = draw({"dist": "constant", "value": 80_000})
    assert np.all(draws == 80_000)


def test_estimation_from_historical_variable_cost():
    mean, sd = distributions.estimate_mean_sd(VARIABLE_COST_HISTORY)
    assert mean == pytest.approx(30.0625)
    assert sd == pytest.approx(1.2443, abs=0.0001)  # sample SD (ddof = 1)


@pytest.mark.parametrize(
    "spec",
    [
        {"dist": "normal", "mean": 50, "sd": 0},
        {"dist": "normal", "mean": 50, "sd": -1},
        {"dist": "pert", "min": 44, "mode": 53, "max": 52},
        {"dist": "pert", "min": 52, "mode": 50, "max": 44},
        {"dist": "triangular", "min": 44, "mode": 43, "max": 52},
        {"dist": "lognormal", "mean": -30, "sd": 1.5},
        {"dist": "lognormal", "mean": 30, "sd": 0},
        {"dist": "uniform", "min": 0, "max": 1},
    ],
)
def test_invalid_parameters_raise_a_clear_error(spec):
    with pytest.raises(ValueError):
        distributions.from_spec(spec)
