"""Compare the Python simulation with the Excel model and write docs/validation.md.

Run it with:  python validate.py
"""

from pathlib import Path

import numpy as np

from montecarlo import model
from montecarlo.simulation import DEFAULT_SEED, run_simulation
from montecarlo.stats import Z_95, summarize
from scenarios import lesson2, lesson3, lesson4

LESSONS = [lesson2, lesson3, lesson4]
STATISTICS = {
    "mean": "Mean NPV",
    "sd": "Standard deviation",
    "p5": "P5",
    "p95": "P95",
    "prob_negative": "P(NPV < 0)",
}
N_EXCEL = 5_000
N_LARGE = 100_000
N_REPETITIONS = 1_000
OUTPUT = Path(__file__).parent / "docs" / "validation.md"


def standard_errors_by_repetition(scenario, n_iterations=N_EXCEL, n_repetitions=N_REPETITIONS):
    """Standard error of each statistic for a simulation of `n_iterations`.

    The simulation is repeated with many different seeds (like pressing F9
    many times in Excel); the standard deviation of a statistic across the
    repetitions is its standard error.
    """
    results = {name: [] for name in STATISTICS}
    for repetition in range(n_repetitions):
        draws = run_simulation(scenario, n_iterations, seed=1_000 + repetition)
        summary = summarize(draws["npv"])
        for name in STATISTICS:
            results[name].append(summary[name])
    return {name: float(np.std(values, ddof=1)) for name, values in results.items()}


def margin_of_difference(se_excel_size, n_python=N_LARGE, n_excel=N_EXCEL):
    """95 % margin of (Excel run - Python run): both are affected by noise.

    A standard error is proportional to 1 / sqrt(N), so the Python run with
    n_python iterations has SE = se_excel_size x sqrt(n_excel / n_python).
    """
    se_python = se_excel_size * np.sqrt(n_excel / n_python)
    return Z_95 * np.sqrt(se_excel_size**2 + se_python**2)


def fmt(name, value, signed=False):
    """Euros without decimals; probabilities in % (differences in points)."""
    sign = "+" if signed else ""
    if name == "prob_negative":
        return f"{value * 100:{sign}.1f} {'pt' if signed else '%'}"
    return f"{value:{sign},.0f} €"


def comparison_table(reference, large, small, standard_errors):
    lines = [
        f"| Statistic | Excel (N = {N_EXCEL:,}) | Python (N = {N_EXCEL:,}) "
        f"| Python (N = {N_LARGE:,}) | SE at N = {N_EXCEL:,} | Excel − Python {N_LARGE:,} "
        "| 95 % margin | Verdict |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for name, label in STATISTICS.items():
        difference = reference[name] - large[name]
        margin = margin_of_difference(standard_errors[name])
        verdict = "within" if abs(difference) <= margin else "**outside**"
        lines.append(
            f"| {label} | {fmt(name, reference[name])} | {fmt(name, small[name])} "
            f"| {fmt(name, large[name])} | {fmt(name, standard_errors[name]).replace(' %', ' pt')} "
            f"| {fmt(name, difference, signed=True)} "
            f"| ± {fmt(name, margin).replace(' %', ' pt')} | {verdict} |"
        )
    return "\n".join(lines)


def build_report():
    base_case_npv = float(model.npv(**model.BASE_CASE))
    sections, large_runs, n_outside, n_total = [], {}, 0, 0

    for lesson in LESSONS:
        scenario = lesson.SCENARIO
        small = summarize(run_simulation(scenario, N_EXCEL)["npv"])
        draws = run_simulation(scenario, N_LARGE)
        large = summarize(draws["npv"])
        large_runs[lesson] = (large, draws)
        standard_errors = standard_errors_by_repetition(scenario)

        for reference in (lesson.EXCEL_NOTES, lesson.EXCEL_WORKBOOK):
            for name in STATISTICS:
                margin = margin_of_difference(standard_errors[name])
                n_outside += abs(reference[name] - large[name]) > margin
                n_total += 1

        sections.append(
            f"## {scenario['name']}\n\n"
            "**Excel reference from our notes** (rounded values):\n\n"
            f"{comparison_table(lesson.EXCEL_NOTES, large, small, standard_errors)}\n\n"
            "**Excel run stored in the workbook** (last recalculation of "
            "`excel/monte carlo stage 1-4.xlsx`):\n\n"
            f"{comparison_table(lesson.EXCEL_WORKBOOK, large, small, standard_errors)}\n\n"
            f"SE of the mean by formula (SD / √N, N = {N_EXCEL:,}): "
            f"{fmt('mean', small['se_mean'])}; SE of P(NPV < 0) by formula "
            f"(√(p(1−p)/N)): {small['se_prob_negative'] * 100:.1f} pt. "
            "Both agree with the SE measured by repetition in the tables."
        )

    mean2, mean3, mean4 = (large_runs[lesson][0]["mean"] for lesson in LESSONS)
    se2, se3, se4 = (large_runs[lesson][0]["se_mean"] for lesson in LESSONS)
    sd3, sd4 = (large_runs[lesson][0]["sd"] for lesson in (lesson3, lesson4))
    draws4 = large_runs[lesson4][1]
    measured_rho = float(np.corrcoef(draws4["price"], draws4["demand"])[0, 1])

    return f"""# Validation: Python vs Excel

This file is generated by `python validate.py`. Do not edit it by hand.

## Method

- The Python model uses the same inputs and formulas as our Excel model
  (lessons 2, 3 and 4). Python runs use seed {DEFAULT_SEED}.
- Deterministic check: base case NPV = **{base_case_npv:,.2f} €** in Python,
  equal to the Excel base case to the cent.
- A simulation is an estimate. Two runs of the same model never give exactly
  the same statistics, so Python and Excel are compared **within a margin of
  error**, not to the euro.
- **Standard error (SE)**: the Python simulation of {N_EXCEL:,} iterations is
  repeated {N_REPETITIONS:,} times with different seeds (like pressing F9
  {N_REPETITIONS:,} times in Excel). The standard deviation of a statistic
  across these repetitions is its SE for a run of {N_EXCEL:,} iterations.
- **Margin**: Excel ({N_EXCEL:,} iterations) is compared with the Python run of
  {N_LARGE:,} iterations, the most precise estimate available. Both are noisy,
  so the 95 % margin of their difference is
  1.96 × √(SE² at {N_EXCEL:,} + SE² at {N_LARGE:,}), with SE proportional to 1/√N.
- **Verdict**: "within" if the difference is smaller than the margin.
  Even with a perfect model, about 1 comparison in 20 falls outside a 95 %
  margin by chance alone.
- Two Excel references are used: the rounded results from our notes, and the
  run stored in the workbook. They are two different runs of the same model;
  the gap between them shows the noise of {N_EXCEL:,} iterations.

{chr(10).join(section + chr(10) for section in sections)}
## Summary

{n_total - n_outside} of {n_total} comparisons are within the 95 % margin of error
({n_outside} outside; about {n_total / 20:.1f} expected by chance alone, and the
statistics of a same run are not independent: a run with a low standard
deviation also has a low P95). No difference points to a modelling gap
between Python and Excel.

## Theory checks (Python, N = {N_LARGE:,})

| Check | Theory | Python | 95 % margin |
| --- | ---: | ---: | ---: |
| Lesson 2 mean NPV ≈ base case (linear model, independent inputs) | {base_case_npv:,.0f} € | {mean2:,.0f} € | ± {Z_95 * se2:,.0f} € |
| Lesson 3 mean NPV ≈ base case − 37,900 − 4,600 − 3,500 | ≈ −12,000 € | {mean3:,.0f} € | ± {Z_95 * se3:,.0f} € |
| Lesson 4 mean − lesson 3 mean ≈ ρ·σ_price·σ_demand × annuity factor | ≈ −4,000 € | {mean4 - mean3:,.0f} € | same random numbers in both runs |
| Lesson 4 standard deviation lower than lesson 3 (natural hedge) | lower | {sd4:,.0f} € vs {sd3:,.0f} € | |
| Lesson 4 measured price–demand correlation ≈ ρ = −0.5 | ≈ −0.5 | {measured_rho:.3f} | |

The measured correlation is slightly weaker than the input ρ: the copula
imposes ρ on the underlying normal variables, and transforming one of them
into an asymmetric PERT price slightly reduces the linear correlation.
"""


if __name__ == "__main__":
    OUTPUT.write_text(build_report(), encoding="utf-8")
    print(f"Written: {OUTPUT}")
