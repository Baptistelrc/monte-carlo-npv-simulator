"""Correlation between inputs through a Gaussian copula.

Steps:
1. draw independent standard normals Z;
2. mix them with the Cholesky factor L of the correlation matrix (X = Z L'),
   so that the X are standard normals with the requested correlations;
3. turn each X into a probability U = Phi(X), uniform between 0 and 1.

Each input is then obtained with its own inverse CDF applied to its U.
With two inputs and a correlation rho, step 2 is exactly:
X1 = Z1 and X2 = rho * Z1 + sqrt(1 - rho^2) * Z2.
"""

import numpy as np
from scipy import stats

TOLERANCE = 1e-8


def build_correlation_matrix(names, correlations):
    """Correlation matrix from pairs, e.g. {("price", "demand"): -0.5}.

    Pairs that are not listed are uncorrelated.
    """
    matrix = np.eye(len(names))
    for (first, second), rho in correlations.items():
        i, j = names.index(first), names.index(second)
        matrix[i, j] = matrix[j, i] = rho
    return matrix


def check_correlation_matrix(matrix):
    """Raise a clear error if the matrix is not a valid correlation matrix."""
    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("The correlation matrix must be square.")
    if not np.allclose(matrix, matrix.T, atol=TOLERANCE):
        raise ValueError("The correlation matrix must be symmetric.")
    if not np.allclose(np.diag(matrix), 1.0, atol=TOLERANCE):
        raise ValueError("The correlation matrix must have 1 on its diagonal.")
    if np.any(np.abs(matrix) > 1 + TOLERANCE):
        raise ValueError("Every correlation must be between -1 and 1.")
    if np.linalg.eigvalsh(matrix).min() < -TOLERANCE:
        raise ValueError(
            "The correlation matrix is not positive semi-definite: "
            "these correlations cannot all hold at the same time."
        )


def cholesky_factor(matrix):
    """Lower factor L such that L L' = matrix."""
    check_correlation_matrix(matrix)
    matrix = np.asarray(matrix, dtype=float)
    try:
        return np.linalg.cholesky(matrix)
    except np.linalg.LinAlgError:
        # Limit case (e.g. a correlation of exactly 1 or -1): Cholesky fails,
        # an equivalent factor is built from the eigenvalues.
        eigenvalues, eigenvectors = np.linalg.eigh(matrix)
        return eigenvectors * np.sqrt(np.clip(eigenvalues, 0, None))


def correlated_uniforms(rng, n_iterations, matrix):
    """Uniform draws (one column per input) linked by a Gaussian copula."""
    factor = cholesky_factor(matrix)
    independent_normals = rng.standard_normal((n_iterations, factor.shape[0]))
    correlated_normals = independent_normals @ factor.T
    return stats.norm.cdf(correlated_normals)
