"""Statistics of the simulated NPVs, with their standard errors.

A simulated statistic is an estimate: another seed gives a slightly different
value. The standard error (SE) measures this simulation noise, and the 95 %
margin of error is 1.96 x SE.
"""

import numpy as np
import pandas as pd

from montecarlo import distributions
from montecarlo.simulation import INPUT_NAMES, npv_from_inputs

Z_95 = 1.96  # 95 % confidence level of a normal distribution


def summarize(npvs):
    """Main statistics of the simulated NPVs.

    SE of the mean = SD / sqrt(N); SE of a probability = sqrt(p (1 - p) / N).
    Percentiles use linear interpolation, like Excel's PERCENTILE.INC, and
    the standard deviation is the sample one, like Excel's STDEV.S.
    """
    npvs = np.asarray(npvs, dtype=float)
    n = npvs.size
    p5, p50, p95 = np.percentile(npvs, [5, 50, 95])
    sd = npvs.std(ddof=1)
    prob_negative = np.mean(npvs < 0)
    return {
        "n": n,
        "mean": float(npvs.mean()),
        "sd": float(sd),
        "p5": float(p5),
        "p50": float(p50),
        "p95": float(p95),
        "prob_negative": float(prob_negative),
        "se_mean": float(sd / np.sqrt(n)),
        "se_prob_negative": float(np.sqrt(prob_negative * (1 - prob_negative) / n)),
    }


def margin_95(standard_error):
    """95 % margin of error: the estimate is reported as value +/- margin."""
    return Z_95 * standard_error


def tornado(scenario, base_inputs):
    """Swing analysis: sensitivity of the NPV to each uncertain input.

    Each input moves alone from its 10th percentile (P10) to its 90th
    percentile (P90) while the others stay at their base case value.
    `base_inputs` gives the base case value of price, demand, variable_cost
    and fixed_costs. Constant inputs have no swing and are left out.
    Returns one row per input, the largest swing first.

    This measures sensitivity, not correlation: inputs move one at a time.
    """
    rows = []
    for name in INPUT_NAMES:
        distribution = distributions.from_spec(scenario["inputs"][name])
        low, high = (float(distribution.ppf(q)) for q in (0.10, 0.90))
        if low == high:
            continue
        npv_low = float(npv_from_inputs(scenario, **{**base_inputs, name: low}))
        npv_high = float(npv_from_inputs(scenario, **{**base_inputs, name: high}))
        rows.append(
            {
                "input": name,
                "p10": low,
                "p90": high,
                "npv_at_p10": npv_low,
                "npv_at_p90": npv_high,
                "swing": abs(npv_high - npv_low),
            }
        )
    columns = ["input", "p10", "p90", "npv_at_p10", "npv_at_p90", "swing"]
    table = pd.DataFrame(rows, columns=columns)
    return table.sort_values("swing", ascending=False, ignore_index=True)
