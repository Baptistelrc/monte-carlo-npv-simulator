"""Tests of the correlation matrix checks and of the Gaussian copula (phase 2)."""

import numpy as np
import pytest
from scipy import stats

from montecarlo import correlation


def test_build_matrix_from_pairs():
    names = ["price", "demand", "variable_cost"]
    matrix = correlation.build_correlation_matrix(names, {("price", "demand"): -0.5})
    expected = [[1, -0.5, 0], [-0.5, 1, 0], [0, 0, 1]]
    assert np.array_equal(matrix, expected)


def test_cholesky_matches_the_two_variable_formula():
    # X1 = Z1 and X2 = rho * Z1 + sqrt(1 - rho^2) * Z2
    rho = -0.5
    factor = correlation.cholesky_factor([[1, rho], [rho, 1]])
    assert factor == pytest.approx(np.array([[1, 0], [rho, np.sqrt(1 - rho**2)]]))


def test_identity_matrix_leaves_draws_independent():
    assert np.array_equal(correlation.cholesky_factor(np.eye(3)), np.eye(3))


def test_copula_reproduces_the_input_correlation():
    rho = -0.5
    rng = np.random.default_rng(42)
    uniforms = correlation.correlated_uniforms(rng, 100_000, [[1, rho], [rho, 1]])

    assert uniforms.min() > 0 and uniforms.max() < 1
    normals = stats.norm.ppf(uniforms)
    assert np.corrcoef(normals[:, 0], normals[:, 1])[0, 1] == pytest.approx(rho, abs=0.01)


def test_perfect_correlation_is_accepted():
    rng = np.random.default_rng(42)
    uniforms = correlation.correlated_uniforms(rng, 1_000, [[1, 1], [1, 1]])
    assert uniforms[:, 0] == pytest.approx(uniforms[:, 1])


@pytest.mark.parametrize(
    "matrix, message",
    [
        ([[1, 0.5, 0], [0.5, 1, 0]], "square"),
        ([[1, 0.5], [0.3, 1]], "symmetric"),
        ([[1, 0.5], [0.5, 2]], "diagonal"),
        ([[1, 1.2], [1.2, 1]], "between -1 and 1"),
        # A and B move together, A and C move together, but B and C opposite: impossible.
        ([[1, 0.9, 0.9], [0.9, 1, -0.9], [0.9, -0.9, 1]], "positive semi-definite"),
    ],
)
def test_invalid_matrix_raises_a_clear_error(matrix, message):
    with pytest.raises(ValueError, match=message):
        correlation.check_correlation_matrix(matrix)
