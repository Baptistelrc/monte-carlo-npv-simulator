"""Lesson 3: justified distributions (PERT price, capacity cap, cost from data)."""

from montecarlo.distributions import estimate_mean_sd

# Historical variable cost per unit (EUR): the Normal is fitted on these data.
VARIABLE_COST_HISTORY = [28.5, 29.0, 31.2, 30.4, 29.8, 32.1, 30.6, 28.9]
cost_mean, cost_sd = estimate_mean_sd(VARIABLE_COST_HISTORY)  # 30.0625 and ~1.2443

SCENARIO = {
    "name": "Lesson 3 - justified distributions",
    "inputs": {
        "price": {"dist": "pert", "min": 44.0, "mode": 50.0, "max": 52.0},
        "demand": {"dist": "normal", "mean": 15_000, "sd": 1_500},
        "variable_cost": {"dist": "normal", "mean": cost_mean, "sd": cost_sd},
        "fixed_costs": {"dist": "constant", "value": 80_000},
    },
    "capacity": 17_000,
    "correlations": {},
    "investment": 800_000,
    "discount_rate": 0.10,
    "years": 5,
}

# Results of our Excel model (5,000 iterations), rounded as in our notes.
EXCEL_NOTES = {
    "mean": -13_000,
    "sd": 147_000,
    "p5": -253_000,
    "p95": 231_000,
    "prob_negative": 0.54,
}

# Results stored in the Excel workbook itself (its last recalculation,
# 5,000 iterations, read on 2026-10-03). Another run of the same model.
EXCEL_WORKBOOK = {
    "mean": -8_870.65,
    "sd": 149_663.02,
    "p5": -256_753.60,
    "p95": 234_140.54,
    "prob_negative": 0.5258,
}
