"""Convergence test: with many iterations, the simulated mean NPV must reach
the exact analytical mean NPV, whatever the seed."""

import pytest
from scipy import stats

from montecarlo import distributions, model
from montecarlo.simulation import run_simulation
from montecarlo.stats import summarize
from scenarios import lesson2, lesson3

N_ITERATIONS = 1_000_000
SEEDS = [42, 2024, 7]


def expected_volume_sold(demand_mean, demand_sd, capacity):
    """Exact mean of min(demand, capacity) for a normal demand.

    mean - sd x [phi(z) - z x (1 - Phi(z))], with z = (capacity - mean) / sd.
    The bracket is the average demand lost because of the capacity limit.
    """
    if capacity is None:
        return demand_mean
    z = (capacity - demand_mean) / demand_sd
    lost_demand = demand_sd * (stats.norm.pdf(z) - z * (1 - stats.norm.cdf(z)))
    return demand_mean - lost_demand


def analytical_mean_npv(scenario):
    """Exact mean NPV of a scenario with independent inputs and a normal demand.

    With independent inputs, the mean of volume x margin is the product of
    the means, so the mean NPV is the NPV of the mean inputs.
    """
    inputs = scenario["inputs"]
    return model.npv(
        volume=expected_volume_sold(
            inputs["demand"]["mean"], inputs["demand"]["sd"], scenario["capacity"]
        ),
        price=distributions.from_spec(inputs["price"]).mean(),
        variable_cost=distributions.from_spec(inputs["variable_cost"]).mean(),
        fixed_costs=inputs["fixed_costs"]["value"],
        investment=scenario["investment"],
        discount_rate=scenario["discount_rate"],
        years=scenario["years"],
    )


def test_analytical_mean_of_lesson_2_is_the_base_case():
    assert round(float(analytical_mean_npv(lesson2.SCENARIO)), 2) == 33_973.09


def test_analytical_mean_of_lesson_3():
    scenario = lesson3.SCENARIO
    assert distributions.from_spec(scenario["inputs"]["price"]).mean() == pytest.approx(49.333, abs=0.001)
    assert expected_volume_sold(15_000, 1_500, 17_000) == pytest.approx(14_936.4, abs=0.1)
    assert analytical_mean_npv(scenario) == pytest.approx(-12_137, abs=5)


@pytest.mark.parametrize("lesson", [lesson2, lesson3], ids=["lesson2", "lesson3"])
@pytest.mark.parametrize("seed", SEEDS)
def test_mean_npv_converges_to_the_analytical_value(lesson, seed):
    exact = analytical_mean_npv(lesson.SCENARIO)
    summary = summarize(run_simulation(lesson.SCENARIO, N_ITERATIONS, seed=seed)["npv"])

    # 3 standard errors: about 600 EUR (lesson 2) and 440 EUR (lesson 3).
    tolerance = 3 * summary["se_mean"]
    assert summary["mean"] == pytest.approx(exact, abs=tolerance)
