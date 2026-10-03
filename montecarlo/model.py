"""Deterministic NPV model of the investment project.

The project pays the investment in Year 0 and then earns the same cash flow
every year (no tax, no working capital, no salvage value). Because the cash
flow is constant over the project life, the NPV is:

    NPV = -Investment + annual cash flow x annuity factor

Every function accepts single numbers or NumPy arrays. With arrays, one
element is one simulated scenario, so 100,000 NPVs are computed in one call.
"""

import numpy as np

# Base case of the case study (CLAUDE.md, section 6).
BASE_CASE = {
    "volume": 15_000,         # units per year
    "price": 50.0,            # EUR per unit
    "variable_cost": 30.0,    # EUR per unit
    "fixed_costs": 80_000.0,  # EUR per year
    "investment": 800_000.0,  # EUR, paid in Year 0
    "discount_rate": 0.10,
    "years": 5,
}


def annuity_factor(discount_rate, years):
    """Present value of 1 EUR received at the end of each year for `years` years."""
    if discount_rate == 0:
        return float(years)
    return (1 - (1 + discount_rate) ** -years) / discount_rate


def annual_cash_flow(volume, price, variable_cost, fixed_costs):
    """Cash flow of one operating year: contribution margin minus fixed costs."""
    volume = np.asarray(volume, dtype=float)
    return volume * (price - variable_cost) - fixed_costs


def npv(volume, price, variable_cost, fixed_costs, investment, discount_rate, years):
    """Net present value of the project.

    A negative NPV means the project does not cover its cost of capital;
    it does not necessarily mean the project loses money.
    """
    cash_flow = annual_cash_flow(volume, price, variable_cost, fixed_costs)
    return -investment + cash_flow * annuity_factor(discount_rate, years)


def break_even_price(volume, variable_cost, fixed_costs, investment, discount_rate, years):
    """Price at which NPV = 0, all other inputs unchanged."""
    required_cash_flow = investment / annuity_factor(discount_rate, years)
    return variable_cost + (required_cash_flow + fixed_costs) / volume


def break_even_volume(price, variable_cost, fixed_costs, investment, discount_rate, years):
    """Volume at which NPV = 0, all other inputs unchanged."""
    required_cash_flow = investment / annuity_factor(discount_rate, years)
    return (required_cash_flow + fixed_costs) / (price - variable_cost)
