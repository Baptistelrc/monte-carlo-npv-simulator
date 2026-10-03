"""Lesson 4: lesson 3 plus a negative price-demand correlation (Gaussian copula)."""

from scenarios import lesson3

SCENARIO = {
    **lesson3.SCENARIO,
    "name": "Lesson 4 - price-demand correlation",
    "correlations": {("price", "demand"): -0.5},
}

# Results of our Excel model (5,000 iterations), rounded as in our notes.
EXCEL_NOTES = {
    "mean": -16_700,
    "sd": 117_000,
    "p5": -212_000,
    "p95": 176_000,
    "prob_negative": 0.56,
}

# Results stored in the Excel workbook itself (its last recalculation,
# 5,000 iterations, read on 2026-10-03). Another run of the same model.
EXCEL_WORKBOOK = {
    "mean": -14_170.99,
    "sd": 119_830.08,
    "p5": -209_468.88,
    "p95": 185_689.31,
    "prob_negative": 0.547,
}
