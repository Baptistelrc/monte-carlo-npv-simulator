"""Short written reading of the simulation results, in English or French.

The wording follows our finance rules: a negative NPV means the project does
not cover its cost of capital; gaps are given in euros, never in percent;
every simulated statistic comes with its margin of error; mean and dispersion
are explained separately; sensitivity is not correlation.
"""

from montecarlo import stats

# Same names as the labels of the dashboard, in both languages.
INPUT_LABELS = {
    "price": "Price",
    "demand": "Demand",
    "variable_cost": "Variable cost",
    "fixed_costs": "Fixed costs",
}


def number(value, decimals, language):
    """1,234.5 in English; 1 234,5 in French; with a true minus sign."""
    text = f"{value:,.{decimals}f}".replace("-", "−")
    if language == "fr":
        text = text.replace(",", " ").replace(".", ",")
    return "0" if text in ("−0", "-0") else text


def euros(value, language):
    return f"{number(value, 0, language)} €"


def reading(summary, base_npv, tornado_table, scenario, language="en"):
    """Bullet list (Markdown) reading the results, in "en" or "fr"."""
    write = english_lines if language == "en" else french_lines
    lines = write(summary, base_npv, tornado_table, scenario)
    return "\n".join(f"- {line}" for line in lines)


def key_figures(summary, base_npv, scenario, language):
    """The numbers used by both languages, already formatted."""
    mean_margin = stats.margin_95(summary["se_mean"])
    gap = summary["mean"] - base_npv
    return {
        "mean": euros(summary["mean"], language),
        "mean_margin": euros(mean_margin, language),
        "mean_is_uncertain": abs(summary["mean"]) <= mean_margin,
        "mean_is_negative": summary["mean"] < 0,
        "base": euros(base_npv, language),
        "gap": euros(gap, language),
        "gap_is_significant": abs(gap) > mean_margin,
        "prob": number(summary["prob_negative"] * 100, 1, language),
        "prob_margin": number(stats.margin_95(summary["se_prob_negative"]) * 100, 1, language),
        "p5": euros(summary["p5"], language),
        "p50": euros(summary["p50"], language),
        "p95": euros(summary["p95"], language),
        "sd": euros(summary["sd"], language),
        "n": number(summary["n"], 0, language),
        "rate": number(scenario["discount_rate"] * 100, 1, language),
        "rho": scenario["correlations"].get(("price", "demand"), 0.0),
        "has_capacity": scenario["capacity"] is not None,
    }


def english_lines(summary, base_npv, tornado_table, scenario):
    f = key_figures(summary, base_npv, scenario, "en")
    lines = []

    # 1. Level of the mean NPV, with its margin of error.
    if f["mean_is_uncertain"]:
        verdict = (
            "Zero lies within the margin of error: the simulation cannot tell whether "
            "the mean NPV is positive or negative."
        )
    elif f["mean_is_negative"]:
        verdict = (
            f"On average, the project does not cover its cost of capital ({f['rate']} % discount "
            "rate); this does not mean that it loses money."
        )
    else:
        verdict = (
            f"On average, the project creates value beyond its cost of capital "
            f"({f['rate']} % discount rate)."
        )
    lines.append(
        f"**Mean NPV: {f['mean']} ± {f['mean_margin']}** "
        f"(95 % margin of error, {f['n']} iterations). {verdict}"
    )

    # 2. Mean versus base case: a gap in euros, never in percent.
    if f["gap_is_significant"]:
        causes = [
            "the mean of each input, which differs from its base case value when the "
            "distribution is asymmetric or shifted"
        ]
        if f["has_capacity"]:
            causes.append("the capacity limit, which cuts sales when demand is high")
        if f["rho"] != 0:
            causes.append("the price–demand correlation")
        lines.append(
            f"**Base case: {f['base']}.** The mean NPV differs from it by {f['gap']}. The base "
            f"case uses the reference value of each input, not its mean; the gap comes from: "
            f"{'; '.join(causes)}."
        )
    else:
        lines.append(
            f"**Base case: {f['base']}.** The gap with the mean NPV ({f['gap']}) is smaller "
            "than the margin of error: it is not significant."
        )

    # 3. Probability of not covering the cost of capital.
    lines.append(
        f"**P(NPV < 0): {f['prob']} % ± {f['prob_margin']} pt.** In this share of the "
        "scenarios, the project does not cover its cost of capital."
    )

    # 4. Dispersion, kept separate from the level of the mean.
    lines.append(
        f"**Dispersion:** 90 % of the scenarios give an NPV between {f['p5']} (P5) and "
        f"{f['p95']} (P95); standard deviation of {f['sd']}. The median (P50) is {f['p50']}. "
        "Dispersion measures the risk around the mean; it does not explain the level of the mean."
    )

    # 5. Sensitivity (tornado), not to be confused with correlation.
    if len(tornado_table) > 0:
        first = tornado_table.iloc[0]
        lines.append(
            f"**Sensitivity:** the input that moves the NPV the most is "
            f"**{INPUT_LABELS[first['input']]}**: the NPV goes from "
            f"{euros(first['npv_at_p10'], 'en')} to {euros(first['npv_at_p90'], 'en')} when it "
            "moves from its P10 to its P90, the other inputs staying at their base case value. "
            "This ranking combines how strongly the NPV reacts to an input and how uncertain "
            "that input is."
        )
    if f["rho"] != 0:
        effect = (
            "Being negative, it acts as a natural hedge (a low price comes with a high demand) "
            "and tends to reduce dispersion."
            if f["rho"] < 0
            else "Being positive, it makes price and demand move in the same direction and "
            "tends to increase dispersion."
        )
        lines.append(
            f"**Price–demand correlation (ρ = {number(f['rho'], 2, 'en')}):** it describes how "
            f"the two variables move together; it is not a sensitivity. {effect}"
        )
    return lines


def french_lines(summary, base_npv, tornado_table, scenario):
    """French sentences; finance and statistics terms stay in English."""
    f = key_figures(summary, base_npv, scenario, "fr")
    lines = []

    # 1. Level of the mean NPV, with its margin of error.
    if f["mean_is_uncertain"]:
        verdict = (
            "Zéro est dans la margin of error : la simulation ne permet pas de dire si la "
            "mean NPV est positive ou négative."
        )
    elif f["mean_is_negative"]:
        verdict = (
            f"En moyenne, le projet ne couvre pas son cost of capital (discount rate de "
            f"{f['rate']} %) ; cela ne veut pas dire qu'il perd de l'argent."
        )
    else:
        verdict = (
            f"En moyenne, le projet crée de la valeur au-delà de son cost of capital "
            f"(discount rate de {f['rate']} %)."
        )
    lines.append(
        f"**Mean NPV : {f['mean']} ± {f['mean_margin']}** "
        f"(margin of error à 95 %, {f['n']} itérations). {verdict}"
    )

    # 2. Mean versus base case: a gap in euros, never in percent.
    if f["gap_is_significant"]:
        causes = [
            "la mean de chaque input, qui diffère de sa valeur base case quand la "
            "distribution est asymétrique ou décalée"
        ]
        if f["has_capacity"]:
            causes.append("la capacity, qui plafonne le volume vendu quand la Demand est forte")
        if f["rho"] != 0:
            causes.append("la corrélation Price–Demand")
        lines.append(
            f"**Base case : {f['base']}.** La mean NPV s'en écarte de {f['gap']}. Le base "
            f"case utilise la valeur de référence de chaque input, pas sa mean ; l'écart "
            f"vient de : {' ; '.join(causes)}."
        )
    else:
        lines.append(
            f"**Base case : {f['base']}.** L'écart avec la mean NPV ({f['gap']}) est "
            "inférieur à la margin of error : il n'est pas significatif."
        )

    # 3. Probability of not covering the cost of capital.
    lines.append(
        f"**P(NPV < 0) : {f['prob']} % ± {f['prob_margin']} pt.** Dans cette part des "
        "scénarios, le projet ne couvre pas son cost of capital."
    )

    # 4. Dispersion, kept separate from the level of the mean.
    lines.append(
        f"**Dispersion :** 90 % des scénarios donnent une NPV entre {f['p5']} (P5) et "
        f"{f['p95']} (P95) ; standard deviation de {f['sd']}. La median (P50) est de {f['p50']}. "
        "La dispersion mesure le risque autour de la mean ; elle n'explique pas le niveau "
        "de la mean."
    )

    # 5. Sensitivity (tornado), not to be confused with correlation.
    if len(tornado_table) > 0:
        first = tornado_table.iloc[0]
        lines.append(
            f"**Sensibilité (tornado) :** l'input qui fait le plus bouger la NPV est "
            f"**{INPUT_LABELS[first['input']]}** : la NPV passe de "
            f"{euros(first['npv_at_p10'], 'fr')} à {euros(first['npv_at_p90'], 'fr')} quand cet "
            "input va de son P10 à son P90, les autres restant au base case. Ce classement "
            "combine la force de réaction de la NPV à un input et l'incertitude sur cet input."
        )
    if f["rho"] != 0:
        effect = (
            "Négative, elle joue comme un natural hedge (un Price bas va avec une Demand "
            "élevée) et tend à réduire la dispersion."
            if f["rho"] < 0
            else "Positive, elle fait varier Price et Demand dans le même sens et tend à "
            "augmenter la dispersion."
        )
        lines.append(
            f"**Corrélation Price–Demand (ρ = {number(f['rho'], 2, 'fr')}) :** elle décrit "
            f"comment les deux variables bougent ensemble ; ce n'est pas une sensibilité. {effect}"
        )
    return lines
