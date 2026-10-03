"""Tests of the deterministic NPV model (phase 1)."""

import numpy as np
import pytest

from montecarlo.model import (
    BASE_CASE,
    annual_cash_flow,
    annuity_factor,
    break_even_price,
    break_even_volume,
    npv,
)


def base_case_with(**changes):
    """Base case inputs, with some of them replaced."""
    return {**BASE_CASE, **changes}


def without(inputs, name):
    """Inputs without the one we are solving for."""
    return {key: value for key, value in inputs.items() if key != name}


def test_base_case_annual_cash_flow():
    cash_flow = annual_cash_flow(15_000, 50.0, 30.0, 80_000.0)
    assert cash_flow == pytest.approx(220_000.0)


def test_base_case_npv_to_the_cent():
    assert round(float(npv(**BASE_CASE)), 2) == 33_973.09


def test_annuity_factor_matches_year_by_year_discounting():
    # Independent check: discount 1 EUR year by year, as in the Excel model.
    year_by_year = sum(1 / 1.10**year for year in range(1, 6))
    assert annuity_factor(0.10, 5) == pytest.approx(year_by_year)


def test_annuity_factor_with_zero_discount_rate():
    assert annuity_factor(0.0, 5) == 5.0


def test_break_even_price():
    price = break_even_price(**without(BASE_CASE, "price"))
    assert price == pytest.approx(49.40, abs=0.01)
    assert npv(**base_case_with(price=price)) == pytest.approx(0.0, abs=1e-6)


def test_break_even_volume():
    volume = break_even_volume(**without(BASE_CASE, "volume"))
    assert volume == pytest.approx(14_552, abs=1)
    assert npv(**base_case_with(volume=volume)) == pytest.approx(0.0, abs=1e-6)


def test_npv_accepts_scalars():
    result = npv(**BASE_CASE)
    assert np.ndim(result) == 0


def test_npv_accepts_arrays():
    prices = np.array([45.0, 50.0, 55.0])
    volumes = np.array([14_000, 15_000, 16_000])
    result = npv(**base_case_with(price=prices, volume=volumes))

    assert result.shape == (3,)
    # Each element must equal the NPV computed one scenario at a time.
    for i in range(3):
        one_by_one = npv(**base_case_with(price=prices[i], volume=volumes[i]))
        assert result[i] == pytest.approx(one_by_one)
    assert round(float(result[1]), 2) == 33_973.09


def test_npv_mixes_arrays_and_scalars():
    prices = np.array([49.0, 50.0, 51.0])
    result = npv(**base_case_with(price=prices))
    assert result.shape == (3,)
    assert result[0] < result[1] < result[2]
