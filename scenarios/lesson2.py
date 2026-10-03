"""Lesson 2: independent normal distributions, no capacity limit."""

SCENARIO = {
    "name": "Lesson 2 - independent normals",
    "inputs": {
        "price": {"dist": "normal", "mean": 50.0, "sd": 2.5},
        "demand": {"dist": "normal", "mean": 15_000, "sd": 1_500},
        "variable_cost": {"dist": "normal", "mean": 30.0, "sd": 1.5},
        "fixed_costs": {"dist": "constant", "value": 80_000},
    },
    "capacity": None,
    "correlations": {},
    "investment": 800_000,
    "discount_rate": 0.10,
    "years": 5,
}

# Results of our Excel model (5,000 iterations), rounded as in our notes.
EXCEL_NOTES = {
    "mean": 35_000,
    "sd": 201_000,
    "p5": -283_000,
    "p95": 378_000,
    "prob_negative": 0.445,  # "44-45 %"
}

# Results stored in the Excel workbook itself (its last recalculation,
# 5,000 iterations, read on 2026-10-03). Another run of the same model.
EXCEL_WORKBOOK = {
    "mean": 31_231.06,
    "sd": 201_272.43,
    "p5": -286_679.27,
    "p95": 365_905.26,
    "prob_negative": 0.4536,
}
