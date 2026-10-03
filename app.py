"""Streamlit dashboard: Monte Carlo valuation of an investment project.

Run it with:  streamlit run app.py
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from montecarlo import distributions, model, stats
from montecarlo.reading import reading
from montecarlo.simulation import DEFAULT_SEED, INPUT_NAMES, npv_from_inputs, run_simulation
from scenarios import lesson2, lesson3, lesson4

LESSONS = {
    "Lesson 2 — independent normals": lesson2,
    "Lesson 3 — justified distributions": lesson3,
    "Lesson 4 — price–demand correlation": lesson4,
}
DISTRIBUTIONS = {
    "constant": "Constant",
    "normal": "Normal",
    "pert": "PERT",
    "triangular": "Triangular",
    "lognormal": "Lognormal",
}
# For each uncertain input: label, unit, base case key and number format.
INPUTS = {
    "price": ("Price", "€ / unit", "base_price", "%.2f"),
    "demand": ("Demand", "units / year", "base_volume", "%.0f"),
    "variable_cost": ("Variable cost", "€ / unit", "base_variable_cost", "%.4f"),
    "fixed_costs": ("Fixed costs", "€ / year", "base_fixed_costs", "%.0f"),
}


# ---------------------------------------------------------------- sidebar


def load_scenario(scenario):
    """Fill the sidebar with the base case and the assumptions of a lesson."""
    state = st.session_state
    base = model.BASE_CASE
    state["investment"] = float(base["investment"])
    state["years"] = int(base["years"])
    state["discount_rate_pct"] = base["discount_rate"] * 100
    state["base_volume"] = float(base["volume"])
    state["base_price"] = float(base["price"])
    state["base_variable_cost"] = float(base["variable_cost"])
    state["base_fixed_costs"] = float(base["fixed_costs"])

    for name in INPUT_NAMES:
        for parameter, value in scenario["inputs"][name].items():
            if parameter != "value":  # a Constant uses the base case value
                state[f"{name}_{parameter}"] = value if parameter == "dist" else float(value)

    capacity = scenario.get("capacity")
    state["use_capacity"] = capacity is not None
    if capacity is not None:
        state["capacity"] = float(capacity)
    state["rho"] = float(scenario.get("correlations", {}).get(("price", "demand"), 0.0))


def number(container, label, key, default, **options):
    """Number field that remembers its value under `key`."""
    st.session_state.setdefault(key, default)
    return container.number_input(label, key=key, **options)


def distribution_inputs(name, base_value):
    """Widgets of one uncertain input; returns its distribution spec."""
    label, unit, _, number_format = INPUTS[name]
    st.session_state.setdefault(f"{name}_dist", "constant")
    kind = st.selectbox(
        f"{label} ({unit})",
        list(DISTRIBUTIONS),
        format_func=DISTRIBUTIONS.get,
        key=f"{name}_dist",
    )

    if kind == "constant":
        st.caption(f"Stays at its base case value ({base_value:,.2f}).")
        return {"dist": "constant", "value": base_value}

    if kind in ("normal", "lognormal"):
        left, right = st.columns(2)
        spec = {
            "dist": kind,
            "mean": number(left, "Mean", f"{name}_mean", base_value, format=number_format),
            "sd": number(right, "SD", f"{name}_sd", 0.05 * base_value, format=number_format),
        }
        if kind == "lognormal":
            st.caption(
                "Lognormal: Mean and SD are those of the input itself, in its own "
                "unit, not those of its logarithm."
            )
        return spec

    left, middle, right = st.columns(3)
    return {
        "dist": kind,
        "min": number(left, "Min", f"{name}_min", 0.9 * base_value, format=number_format),
        "mode": number(middle, "Mode", f"{name}_mode", base_value, format=number_format),
        "max": number(right, "Max", f"{name}_max", 1.1 * base_value, format=number_format),
    }


def sidebar():
    """Draw the sidebar; return the scenario, the base case inputs and the run settings."""
    with st.sidebar:
        st.header("Scenarios")
        for label, lesson in LESSONS.items():
            st.button(label, on_click=load_scenario, args=(lesson.SCENARIO,), width="stretch")

        st.header("Base case")
        investment = number(st, "Initial investment (€)", "investment", 0.0, format="%.0f")
        years = number(st, "Project life (years)", "years", 5, min_value=1, max_value=50)
        discount_rate = number(st, "Discount rate (%)", "discount_rate_pct", 10.0, min_value=0.0) / 100
        base_inputs = {
            "demand": number(st, "Volume (units / year)", "base_volume", 0.0, format="%.0f"),
            "price": number(st, "Price (€ / unit)", "base_price", 0.0),
            "variable_cost": number(st, "Variable cost (€ / unit)", "base_variable_cost", 0.0),
            "fixed_costs": number(st, "Fixed costs (€ / year)", "base_fixed_costs", 0.0, format="%.0f"),
        }

        st.header("Uncertain inputs")
        specs = {name: distribution_inputs(name, base_inputs[name]) for name in INPUT_NAMES}

        st.header("Capacity")
        st.session_state.setdefault("use_capacity", False)
        capacity = None
        if st.checkbox("Volume sold = min(demand, capacity)", key="use_capacity"):
            capacity = number(st, "Capacity (units / year)", "capacity", 17_000.0, format="%.0f")

        st.header("Price–demand correlation")
        rho = number(st, "Correlation ρ", "rho", 0.0, step=0.05, format="%.2f")
        st.caption(
            "Describes how price and demand move together (Gaussian copula). "
            "It is not a sensitivity: see the tornado chart for that."
        )

        st.header("Simulation")
        n_iterations = number(
            st, "Iterations", "n_iterations", 100_000, min_value=1_000, max_value=1_000_000, step=5_000
        )
        seed = number(st, "Seed", "seed", DEFAULT_SEED, min_value=0)

    scenario = {
        "name": "Dashboard scenario",
        "inputs": specs,
        "capacity": capacity,
        "correlations": {("price", "demand"): rho},
        "investment": investment,
        "discount_rate": discount_rate,
        "years": years,
    }
    return scenario, base_inputs, n_iterations, seed


def input_errors(scenario):
    """Clear messages for every invalid input (empty list if all is valid)."""
    errors = []
    for name in INPUT_NAMES:
        try:
            distributions.from_spec(scenario["inputs"][name])
        except ValueError as error:
            errors.append(f"{INPUTS[name][0]} — {error}")
    rho = scenario["correlations"][("price", "demand")]
    if abs(rho) >= 1:
        errors.append(f"Correlation — ρ must be strictly between −1 and 1 (got {rho:g}).")
    if scenario["capacity"] is not None and scenario["capacity"] <= 0:
        errors.append("Capacity — it must be > 0.")
    return errors


# ----------------------------------------------------------------- charts


def chart_colors():
    """Chart colours for the light or dark theme (colour-blind safe palette)."""
    if getattr(st.context.theme, "type", "light") == "dark":
        return {"blue": "#3987e5", "orange": "#d95926", "aqua": "#199e70", "ink": "#c3c2b7"}
    return {"blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a", "ink": "#52514e"}


def histogram_figure(npvs, base_npv, mean_npv, colors):
    counts, edges = np.histogram(npvs, bins=60)
    shares = counts / len(npvs)
    figure = go.Figure(
        go.Bar(
            x=(edges[:-1] + edges[1:]) / 2,
            y=shares,
            width=np.diff(edges) * 0.9,
            marker_color=colors["blue"],
            customdata=np.column_stack([edges[:-1], edges[1:]]),
            hovertemplate="NPV from %{customdata[0]:,.0f} € to %{customdata[1]:,.0f} €"
            "<br>%{y:.1%} of scenarios<extra></extra>",
            showlegend=False,
        )
    )
    top = shares.max() * 1.05
    reference_lines = [
        ("NPV = 0", 0.0, colors["ink"], "solid"),
        (f"Base case: {base_npv:,.0f} €", base_npv, colors["orange"], "dash"),
        (f"Mean: {mean_npv:,.0f} €", mean_npv, colors["aqua"], "dot"),
    ]
    for label, x, color, dash in reference_lines:
        figure.add_trace(
            go.Scatter(
                x=[x, x], y=[0, top], mode="lines", name=label,
                line=dict(color=color, width=2, dash=dash), hoverinfo="name",
            )
        )
    figure.update_layout(
        xaxis=dict(title="NPV (€)", tickformat=",.0f"),
        yaxis=dict(title="Share of scenarios", tickformat=".0%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=10, r=10, t=40, b=10),
        height=380,
    )
    return figure


def cdf_figure(npvs, prob_negative, colors):
    probabilities = np.linspace(0, 1, 501)
    figure = go.Figure(
        go.Scatter(
            x=np.quantile(npvs, probabilities),
            y=probabilities,
            mode="lines",
            line=dict(color=colors["blue"], width=2),
            hovertemplate="%{y:.1%} of scenarios have an NPV below %{x:,.0f} €<extra></extra>",
            showlegend=False,
        )
    )
    figure.add_vline(x=0, line=dict(color=colors["ink"], width=1))
    figure.add_trace(
        go.Scatter(
            x=[0], y=[prob_negative], mode="markers+text",
            marker=dict(color=colors["blue"], size=10),
            text=[f"P(NPV < 0) = {prob_negative:.1%}  "], textposition="top left",
            hoverinfo="skip", showlegend=False,
        )
    )
    figure.update_layout(
        xaxis=dict(title="NPV (€)", tickformat=",.0f"),
        yaxis=dict(title="Cumulative probability", tickformat=".0%", range=[0, 1.02]),
        margin=dict(l=10, r=10, t=40, b=10),
        height=380,
    )
    return figure


def tornado_figure(table, base_npv, colors):
    table = table.iloc[::-1]  # Plotly draws the first row at the bottom
    labels = [INPUTS[name][0] for name in table["input"]]
    figure = go.Figure()
    for column, percentile, color in (
        ("npv_at_p10", "p10", colors["blue"]),
        ("npv_at_p90", "p90", colors["orange"]),
    ):
        figure.add_trace(
            go.Bar(
                y=labels,
                x=table[column] - base_npv,
                base=base_npv,
                orientation="h",
                width=0.4,
                name=f"Input at its {percentile.upper()}",
                marker_color=color,
                text=[f"{value:,.0f} €" for value in table[column]],
                textposition="outside",
                cliponaxis=False,
                customdata=table[percentile],
                hovertemplate="%{y} = %{customdata:,.2f}<br>NPV = %{text}<extra></extra>",
            )
        )
    figure.add_vline(
        x=base_npv,
        line=dict(color=colors["ink"], width=1),
        annotation_text=f"Base case: {base_npv:,.0f} €",
        annotation_position="top",
    )
    lowest = min(table["npv_at_p10"].min(), table["npv_at_p90"].min())
    highest = max(table["npv_at_p10"].max(), table["npv_at_p90"].max())
    padding = 0.2 * (highest - lowest)  # room for the value labels
    figure.update_layout(
        barmode="overlay",
        xaxis=dict(title="NPV (€)", tickformat=",.0f", range=[lowest - padding, highest + padding]),
        legend=dict(orientation="h", yanchor="bottom", y=1.1, x=0),
        margin=dict(l=10, r=10, t=60, b=10),
        height=140 + 60 * len(table),
    )
    return figure


# ------------------------------------------------------- tables and text


def statistics_table(summary, npvs, base_npv):
    def euros(value):
        return f"{value:,.0f} €"

    mean_margin = stats.margin_95(summary["se_mean"])
    prob_margin = stats.margin_95(summary["se_prob_negative"])
    rows = [
        ("Base case NPV (deterministic)", euros(base_npv), ""),
        ("Mean NPV", euros(summary["mean"]), f"± {euros(mean_margin)}"),
        ("Standard deviation", euros(summary["sd"]), ""),
        ("P5", euros(summary["p5"]), ""),
        ("P50 (median)", euros(summary["p50"]), ""),
        ("P95", euros(summary["p95"]), ""),
        ("Minimum", euros(npvs.min()), ""),
        ("Maximum", euros(npvs.max()), ""),
        ("P(NPV < 0)", f"{summary['prob_negative']:.1%}", f"± {prob_margin * 100:.1f} pt"),
        ("Iterations", f"{summary['n']:,}", ""),
    ]
    return pd.DataFrame(rows, columns=["Statistic", "Value", "95 % margin of error"])


# ------------------------------------------------------------------- page


def main():
    st.set_page_config(page_title="Monte Carlo valuation", page_icon="🎲", layout="wide")
    if "investment" not in st.session_state:
        load_scenario(lesson4.SCENARIO)  # first opening: start from lesson 4

    scenario, base_inputs, n_iterations, seed = sidebar()

    st.title("Monte Carlo valuation of an investment project")
    st.caption(
        "NPV = −Investment + annual cash flow × annuity factor, simulated under uncertainty "
        "on price, demand and costs."
    )

    errors = input_errors(scenario)
    if errors:
        for error in errors:
            st.error(error)
        st.stop()

    draws = run_simulation(scenario, n_iterations, seed)
    npvs = draws["npv"].to_numpy()
    summary = stats.summarize(npvs)
    base_npv = float(npv_from_inputs(scenario, **base_inputs))
    tornado_table = stats.tornado(scenario, base_inputs)
    colors = chart_colors()

    # KPI cards
    mean_margin = stats.margin_95(summary["se_mean"])
    prob_margin = stats.margin_95(summary["se_prob_negative"])
    cards = st.columns(4)
    cards[0].metric("Mean NPV", f"{summary['mean']:,.0f} €", border=True)
    cards[0].caption(f"± {mean_margin:,.0f} € (95 % margin of error)")
    cards[1].metric("P(NPV < 0)", f"{summary['prob_negative']:.1%}", border=True)
    cards[1].caption(f"± {prob_margin * 100:.1f} pt (95 % margin of error)")
    cards[2].metric("P5", f"{summary['p5']:,.0f} €", border=True)
    cards[2].caption("5 % of scenarios are below")
    cards[3].metric("P95", f"{summary['p95']:,.0f} €", border=True)
    cards[3].caption("5 % of scenarios are above")

    left, right = st.columns(2)
    with left:
        st.subheader("NPV distribution")
        st.plotly_chart(histogram_figure(npvs, base_npv, summary["mean"], colors), width="stretch")
    with right:
        st.subheader("Cumulative distribution (CDF)")
        st.plotly_chart(cdf_figure(npvs, summary["prob_negative"], colors), width="stretch")

    left, right = st.columns(2)
    with left:
        st.subheader("Statistics")
        st.dataframe(statistics_table(summary, npvs, base_npv), hide_index=True, width="stretch")
    with right:
        st.subheader("Tornado chart (sensitivity)")
        if len(tornado_table) == 0:
            st.info("Every input is constant: there is no sensitivity to show.")
        else:
            st.plotly_chart(tornado_figure(tornado_table, base_npv, colors), width="stretch")
            st.caption(
                "NPV when one input moves from its P10 to its P90, the others staying at "
                "their base case value. This is a sensitivity, not a correlation."
            )

    st.session_state.setdefault("reading_language", "EN")
    language = st.radio("Language of the reading", ["EN", "FR"], key="reading_language", horizontal=True)
    st.subheader("Reading of the results" if language == "EN" else "Lecture des résultats")
    st.markdown(reading(summary, base_npv, tornado_table, scenario, language.lower()))

    st.download_button(
        "Download the simulated draws (CSV)",
        data=lambda: draws.to_csv(index=False).encode("utf-8"),
        file_name="monte_carlo_draws.csv",
        mime="text/csv",
    )


main()
