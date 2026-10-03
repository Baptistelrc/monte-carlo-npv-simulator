"""Tests of the Streamlit dashboard (phase 3), run without a browser."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_FILE = str(Path(__file__).parent.parent / "app.py")


@pytest.fixture
def app():
    app = AppTest.from_file(APP_FILE, default_timeout=60)
    app.run()
    return app


def metrics(app):
    return {metric.label: metric.value for metric in app.metric}


def click_lesson(app, label):
    next(button for button in app.sidebar.button if button.label.startswith(label)).click()
    app.run()


def test_dashboard_opens_on_lesson_4_without_error(app):
    assert not app.exception
    assert not app.error
    assert set(metrics(app)) == {"Mean NPV", "P(NPV < 0)", "P5", "P95"}
    # Same figures as docs/validation.md (lesson 4, 100,000 iterations, seed 42).
    assert metrics(app)["Mean NPV"] == "-14,923 €"
    assert metrics(app)["P(NPV < 0)"] == "55.5%"


@pytest.mark.parametrize(
    "label, mean_npv",
    [("Lesson 2", "35,201 €"), ("Lesson 3", "-11,274 €"), ("Lesson 4", "-14,923 €")],
)
def test_lesson_buttons_load_the_scenarios(app, label, mean_npv):
    click_lesson(app, label)
    assert not app.exception
    assert metrics(app)["Mean NPV"] == mean_npv


def test_all_constant_inputs_give_the_base_case(app):
    for name in ("price", "demand", "variable_cost", "fixed_costs"):
        app.sidebar.selectbox(key=f"{name}_dist").set_value("constant")
    app.run()
    assert not app.exception
    assert metrics(app)["Mean NPV"] == "33,973 €"


def test_every_distribution_can_be_selected(app):
    for kind in ("normal", "pert", "triangular", "lognormal"):
        app.sidebar.selectbox(key="price_dist").set_value(kind)
        app.run()
        assert not app.exception
        assert not app.error


def test_lognormal_parameters_are_explained(app):
    app.sidebar.selectbox(key="variable_cost_dist").set_value("lognormal")
    app.run()
    assert any("not those of its logarithm" in caption.value for caption in app.sidebar.caption)


@pytest.mark.parametrize(
    "key, value, message",
    [
        ("demand_sd", 0.0, "standard deviation must be > 0"),
        ("price_mode", 60.0, "min <= mode <= max"),
        ("price_min", 55.0, "min must be < max"),
        ("rho", 1.0, "strictly between"),
        ("rho", -1.0, "strictly between"),
    ],
)
def test_invalid_inputs_show_a_clear_error(app, key, value, message):
    app.sidebar.number_input(key=key).set_value(value)
    app.run()
    assert not app.exception
    assert any(message in error.value for error in app.error)
    assert not app.metric  # no result is shown on invalid inputs


def test_reading_is_in_english_by_default(app):
    reading = app.markdown[-1].value
    assert "does not cover its cost of capital" in reading
    assert "it is not a sensitivity" in reading
    assert "95 % margin of error" in reading


def test_reading_can_be_switched_to_french(app):
    app.radio(key="reading_language").set_value("FR")
    app.run()
    reading = app.markdown[-1].value
    assert "ne couvre pas son cost of capital" in reading
    assert "ce n'est pas une sensibilité" in reading
    assert "margin of error à 95 %" in reading
    # Finance terms stay in English and inputs keep their dashboard labels.
    assert "**Demand**" in reading
    for french_term in ("VAN", "coût du capital", "écart-type", "la demande", "le prix"):
        assert french_term not in reading
