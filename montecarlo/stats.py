"""Statistics of the simulated NPVs, with their standard errors.

A simulated statistic is an estimate: another seed gives a slightly different
value. The standard error (SE) measures this simulation noise, and the 95 %
margin of error is 1.96 x SE.
"""

import numpy as np

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
