"""Probability distributions of the uncertain inputs.

A distribution is described by a small dictionary (a "spec"), for example:

    {"dist": "normal", "mean": 50, "sd": 2.5}
    {"dist": "pert", "min": 44, "mode": 50, "max": 52}
    {"dist": "triangular", "min": 44, "mode": 50, "max": 52}
    {"dist": "lognormal", "mean": 30, "sd": 1.5}
    {"dist": "constant", "value": 80000}

Every distribution exposes `ppf(u)`, its inverse CDF (percent point function):
it turns a probability u between 0 and 1 into a value of the input. Drawing
u uniformly and applying the inverse CDF gives a draw from the distribution;
this is also what lets the Gaussian copula correlate the inputs.
"""

import numpy as np
from scipy import stats


class Constant:
    """An input without uncertainty: every draw returns the same value."""

    def __init__(self, value):
        self.value = float(value)

    def ppf(self, u):
        return np.full(np.shape(u), self.value)


def normal(mean, sd):
    if sd <= 0:
        raise ValueError(f"Normal: the standard deviation must be > 0 (got {sd}).")
    return stats.norm(loc=mean, scale=sd)


def check_min_mode_max(name, minimum, mode, maximum):
    if not minimum < maximum:
        raise ValueError(f"{name}: min must be < max (got min={minimum}, max={maximum}).")
    if not minimum <= mode <= maximum:
        raise ValueError(
            f"{name}: need min <= mode <= max (got min={minimum}, mode={mode}, max={maximum})."
        )


def pert_shape(minimum, mode, maximum):
    """Alpha and beta of the Beta distribution behind a PERT."""
    alpha = 1 + 4 * (mode - minimum) / (maximum - minimum)
    beta = 1 + 4 * (maximum - mode) / (maximum - minimum)
    return alpha, beta


def pert(minimum, mode, maximum):
    """PERT: a Beta(alpha, beta) stretched from [0, 1] to [min, max]."""
    check_min_mode_max("PERT", minimum, mode, maximum)
    alpha, beta = pert_shape(minimum, mode, maximum)
    return stats.beta(alpha, beta, loc=minimum, scale=maximum - minimum)


def triangular(minimum, mode, maximum):
    check_min_mode_max("Triangular", minimum, mode, maximum)
    width = maximum - minimum
    return stats.triang(c=(mode - minimum) / width, loc=minimum, scale=width)


def lognormal(mean, sd):
    """Lognormal described by the mean and SD of the input itself (not of its log)."""
    if mean <= 0:
        raise ValueError(f"Lognormal: the mean must be > 0 (got {mean}).")
    if sd <= 0:
        raise ValueError(f"Lognormal: the standard deviation must be > 0 (got {sd}).")
    log_variance = np.log(1 + (sd / mean) ** 2)
    log_mean = np.log(mean) - log_variance / 2
    return stats.lognorm(s=np.sqrt(log_variance), scale=np.exp(log_mean))


def estimate_mean_sd(data):
    """Sample mean and sample standard deviation (ddof = 1) of historical data."""
    data = np.asarray(data, dtype=float)
    if data.size < 2:
        raise ValueError("At least two observations are needed to estimate a standard deviation.")
    return float(data.mean()), float(data.std(ddof=1))


def from_spec(spec):
    """Build a distribution from its dictionary description."""
    kind = spec["dist"]
    if kind == "constant":
        return Constant(spec["value"])
    if kind == "normal":
        return normal(spec["mean"], spec["sd"])
    if kind == "pert":
        return pert(spec["min"], spec["mode"], spec["max"])
    if kind == "triangular":
        return triangular(spec["min"], spec["mode"], spec["max"])
    if kind == "lognormal":
        return lognormal(spec["mean"], spec["sd"])
    raise ValueError(f"Unknown distribution: {kind!r}.")
