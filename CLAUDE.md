# CLAUDE.md — Monte Carlo valuation tool

## 1. Context and your role

We are two finance students (bachelor, Finance & Management Control). We master the finance
(NPV, DCF, WACC, Monte Carlo logic) and built the whole model by hand in Excel (lessons 1 to 4).
**We do not code.** You build the entire project. We supervise, validate and must be able to
explain every result and every modelling choice in a job or master's interview.

**Your role: lead developer and explainer.**

- You write all the code, files and tests.
- Work **phase by phase** (section 5). **At the end of each phase, stop** and explain to us, in
  French, with English technical terms:
  1. what you built, in finance terms (not code terms);
  2. how it was validated (which test, which expected value, which result);
  3. what we should look at and how to read the outputs;
  4. any modelling choice you made, and why.
  Then wait for our explicit go before starting the next phase.
- Do not teach us Python syntax. Explain the **logic** of the model, not the language.
- **Never change a modelling assumption** (section 6) without asking us. If something looks wrong
  or ambiguous in the specification, ask.
- Keep the code **simple and readable**: small functions, clear names, short comments. A recruiter
  or a teacher must be able to follow it. No over-engineering, no feature we did not ask for.
- Explain any command before running it.

## 2. Language

- Talk to us in **French**, keeping finance and code terms in **English** (NPV, cash flow,
  discount rate, array, seed…). Spell out any abbreviation the first time you use it.
- Code, comments, docstrings, commit messages and `README.md`: **English** (public portfolio).
- `docs/methodology.md`: **French** (our study and interview notes).

## 3. Environment

- macOS, VS Code, zsh. Python is managed with **conda** (Anaconda); the terminal shows `(base)`.
- Create a dedicated conda environment named **`montecarlo`** (Python 3.13) with: numpy, scipy,
  pandas, plotly, streamlit, pytest. **Never install anything in `base`.** Ask before creating it.
- Provide an `environment.yml` (and a `requirements.txt` for Streamlit Cloud deployment).
- A Python 3.14 from python.org also exists on the machine: **do not use it**.
- The folder is a Git repository named "Monte Carlo", managed with GitHub Desktop, not yet
  published. Create a `.gitignore` (`.venv/`, `__pycache__/`, `.DS_Store`, `.pytest_cache/`…).
  Make small commits with clear messages at the end of each phase.
  **Never push, publish or change repository settings without asking us.**

## 4. Target architecture

```
Monte Carlo/
├── CLAUDE.md
├── README.md                # English, portfolio presentation
├── environment.yml
├── requirements.txt
├── app.py                   # Streamlit dashboard
├── montecarlo/
│   ├── __init__.py
│   ├── model.py             # deterministic NPV, vectorised
│   ├── distributions.py     # Normal, PERT, Triangular, Lognormal, Constant, estimation from data
│   ├── correlation.py       # correlation matrix checks, Cholesky, Gaussian copula
│   ├── simulation.py        # runs a simulation from a config, returns draws and NPVs
│   └── stats.py             # mean, SD, P5/P50/P95, P(NPV<0), standard errors, tornado
├── scenarios/               # one config per lesson (lesson2, lesson3, lesson4)
├── tests/                   # pytest
├── docs/
│   ├── methodology.md       # French: method, choices, limits, results
│   └── validation.md        # Python vs Excel comparison tables
└── excel/                   # our Excel reference model (we will add it)
```

## 5. Phases (stop and explain at the end of each one)

**Phase 1 — Setup and deterministic model.** Conda environment, Git hygiene, `model.py`.
NPV must be vectorised: one draw applies to all 5 years, so
NPV = −Investment + annual cash flow × annuity factor. Tests: base case = **33,973.09 €**
(to the cent); break-even price ≈ 49.40 € gives NPV ≈ 0; break-even volume ≈ 14,552 gives
NPV ≈ 0; the function accepts scalars and arrays.

**Phase 2 — Reproduce lessons 2, 3 and 4.** One scenario config per lesson (section 6).
Use `np.random.default_rng(seed)`; default seed 42. Run with 5,000 and with 100,000 iterations.
Write `docs/validation.md`: a table Python vs Excel for each lesson, with the standard error and a
verdict (within / outside the margin of error). Tests: base case mode gives 33,973.09 €;
ρ = 0 reproduces lesson 3; measured correlation ≈ the input ρ; capped volume never exceeds
capacity; PERT draws stay within [min, max] and their mean ≈ (min + 4·mode + max)/6;
statistical results within tolerance of the Excel references.

**Phase 3 — Streamlit dashboard.**
- Sidebar: base case inputs; for each uncertain input, a distribution choice (Constant, Normal,
  PERT, Triangular, Lognormal) with its parameters; capacity; price–demand correlation; number of
  iterations; seed; buttons to load the lesson 2, 3 and 4 scenarios.
- Main page: KPI cards (Mean NPV with its ±95 % margin, P(NPV<0) with its margin, P5, P95);
  NPV histogram with vertical lines at 0, base case and mean; cumulative distribution (CDF);
  statistics table; **tornado chart** (swing analysis: NPV when each input moves from its P10 to
  its P90, the others at base case); a short auto-generated reading in French of the results;
  CSV export of the simulated draws.
- Validate inputs (min ≤ mode ≤ max, SD > 0, |ρ| < 1) with clear error messages.

**Phase 4 — Documentation.** `README.md` in English: what the tool does, the method, a
screenshot, how to run it, results of the case study, limitations, and an honest note that the
code was written with Claude Code under our specification and validation.
`docs/methodology.md` in French. Prepare (do not perform) deployment on Streamlit Community Cloud.

**Phase 5 — Fastned case study.** Later, with a separate specification. **Never invent Fastned
data**: we will provide every figure and its source.

## 6. Model specification (do not change without asking)

### Base case

| Input | Value |
| --- | --- |
| Initial investment | 800,000 € (Year 0) |
| Project life | 5 years, salvage value = 0 |
| Volume | 15,000 units / year |
| Price | 50 € / unit |
| Variable cost | 30 € / unit |
| Fixed costs | 80,000 € / year |
| Discount rate | 10 % |

No tax, no NWC. Annual cash flow (Years 1–5) = Volume × (Price − Variable cost) − Fixed costs
= 220,000 €. Year 0 contains only the investment.

### Lesson 2 — independent normals

Price ~ Normal(50, 2.5); Volume ~ Normal(15,000, 1,500); Variable cost ~ Normal(30, 1.5).
Fixed costs constant.

### Lesson 3 — justified distributions

| Input | Distribution | Parameters |
| --- | --- | --- |
| Price | PERT | min 44, mode 50, max 52 → α = 4, β = 2 |
| Demand | Normal | mean 15,000, SD 1,500 |
| Volume sold | Cap | min(demand, capacity), capacity = 17,000 |
| Variable cost | Normal | sample mean and sample SD (ddof = 1) of the historical data |
| Fixed costs | Constant | 80,000 € |

Historical variable cost: 28.5, 29.0, 31.2, 30.4, 29.8, 32.1, 30.6, 28.9
(mean 30.0625, sample SD ≈ 1.2443).
PERT: α = 1 + 4(mode − min)/(max − min); β = 1 + 4(max − mode)/(max − min);
draw = min + (max − min) × Beta(α, β).

### Lesson 4 — price–demand correlation

ρ = −0.5 between price and demand through a **Gaussian copula**: Z1, Z2 independent standard
normals; X1 = Z1; X2 = ρ·Z1 + √(1 − ρ²)·Z2; U = Φ(X); price = PERT inverse CDF of U1;
demand = Normal inverse CDF of U2. Variable cost stays independent. Generalise with a correlation
matrix and its Cholesky decomposition; check the matrix is symmetric, has a unit diagonal and is
positive semi-definite, and raise a clear error otherwise.

### Excel reference results (5,000 iterations — compare within the margin of error)

| Statistic | Lesson 2 | Lesson 3 | Lesson 4 (ρ = −0.5) |
| --- | --- | --- | --- |
| Mean NPV | ≈ 35,000 € | ≈ −13,000 € | ≈ −16,700 € |
| Standard deviation | ≈ 201,000 € | ≈ 147,000 € | ≈ 117,000 € |
| P5 | ≈ −283,000 € | ≈ −253,000 € | ≈ −212,000 € |
| P95 | ≈ 378,000 € | ≈ 231,000 € | ≈ 176,000 € |
| P(NPV < 0) | ≈ 44–45 % | ≈ 54 % | ≈ 56 % |

Theory checks: lesson 2 mean NPV ≈ base case (linear model, independent inputs). Lesson 3 mean
≈ base case − 37,900 € (price asymmetry: PERT mean 49.33 €) − 4,600 € (capacity cap)
− 3,500 € (variable cost mean 30.06 €) ≈ −12,000 €. Lesson 4: covariance effect on the mean
≈ ρ·σ_price·σ_demand × annuity factor ≈ −4,000 €; standard deviation strongly lower than
lesson 3 (natural hedge).

## 7. Finance rules to respect in code, outputs and explanations

- A negative NPV means the project **does not cover its cost of capital**, not that it loses money.
- Mean and dispersion of the result have different causes: never explain one by the other.
- Always report a simulated statistic with its standard error (SE of mean = SD/√N;
  SE of a probability = √(p(1−p)/N)).
- Never express as a percentage the change of a number close to zero.
- The most likely value is not the mean when the distribution is asymmetric.
- Correlation is not sensitivity: the tornado chart measures sensitivity; the correlation input
  describes how variables move together.
