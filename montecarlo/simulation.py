"""Monte Carlo simulation of the project NPV from a scenario.

A scenario is a dictionary:

    {
        "name": "...",
        "inputs": {            # one distribution spec per uncertain input
            "price": {...}, "demand": {...},
            "variable_cost": {...}, "fixed_costs": {...},
        },
        "capacity": 17000,     # or None: no capacity limit
        "correlations": {("price", "demand"): -0.5},   # may be empty
        "investment": 800000, "discount_rate": 0.10, "years": 5,
    }
"""

import numpy as np
import pandas as pd

from montecarlo import correlation, distributions, model

# Order of the inputs in the correlation matrix.
INPUT_NAMES = ["price", "demand", "variable_cost", "fixed_costs"]

DEFAULT_SEED = 42


def run_simulation(scenario, n_iterations=5_000, seed=DEFAULT_SEED):
    """Simulate the scenario; return one row per iteration (inputs and NPV)."""
    rng = np.random.default_rng(seed)

    matrix = correlation.build_correlation_matrix(
        INPUT_NAMES, scenario.get("correlations", {})
    )
    uniforms = correlation.correlated_uniforms(rng, n_iterations, matrix)

    # Each input: its own inverse CDF applied to its column of uniforms.
    draws = {}
    for column, name in enumerate(INPUT_NAMES):
        distribution = distributions.from_spec(scenario["inputs"][name])
        draws[name] = distribution.ppf(uniforms[:, column])

    draws["volume"] = volume_sold(draws["demand"], scenario.get("capacity"))
    draws["npv"] = npv_from_inputs(scenario, **{name: draws[name] for name in INPUT_NAMES})
    return pd.DataFrame(draws)


def volume_sold(demand, capacity):
    """Volume sold cannot exceed capacity (None = no capacity limit)."""
    if capacity is None:
        return demand
    return np.minimum(demand, capacity)


def npv_from_inputs(scenario, price, demand, variable_cost, fixed_costs):
    """NPV of the scenario's project for given values of the four inputs."""
    return model.npv(
        volume=volume_sold(demand, scenario.get("capacity")),
        price=price,
        variable_cost=variable_cost,
        fixed_costs=fixed_costs,
        investment=scenario["investment"],
        discount_rate=scenario["discount_rate"],
        years=scenario["years"],
    )
