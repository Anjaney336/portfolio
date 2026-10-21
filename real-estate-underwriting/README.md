# Bengaluru Office Acquisition Underwriting

A reproducible investment-analysis portfolio case by Anjaney Malhotra. The question is whether a hypothetical 100,000 sq ft office asset supports its purchase price after operating costs, lease rollover, capital costs and debt service.

**[Read the investment case](https://anjaney336.github.io/portfolio/real-estate-underwriting/)**

## Decision and evidence

At the illustrative INR 100 crore entry price, the base case produces approximately INR -11.00 crore equity NPV at a 15% hurdle and 1.04x minimum NOI DSCR against a 1.25x screen. The maximum price satisfying both screens is approximately INR 83.53 crore, assuming debt resizes at constant 55% LTV. Debt coverage binds at that price. This is a model threshold, not a market price opinion.

The model explicitly captures year-three lease rollover, lost rent, tenant improvements, leasing fees, annual debt amortization and year-six NOI used for a year-five disposal. A later equity contribution is included in both the cash-flow series and the equity-multiple denominator.

## Reproduce

Python 3.10+; no external packages required.

```bash
cd real-estate-underwriting
python -m unittest -v
python run_analysis.py
```

Open `index.html` after running. Results are deterministic with seed 20261021. Monetary model outputs use nominal INR; the report converts to INR crore (1 crore = 10,000,000).

## What is included

- `model.py`: validated assumptions, annual asset cash flows, amortizing debt, NPV, conventional-cash-flow IRR and equity multiple.
- `assumptions.json`: editable and explicitly illustrative input set.
- `test_model.py`: ten tests including hand calculations, debt and equity reconciliation, maturity, zero interest, missing IRR, invalid inputs and sensitivity direction.
- `run_analysis.py`: base/downside/upside scenarios, a 25-cell sensitivity grid, 2,000 correlated simulations, price screening and report generation.
- `results/annual_cash_flows.csv`: auditable operating and financing bridge.
- `results/sensitivity.csv`: rent-growth versus exit-cap sensitivity.
- `results/simulation.csv`: every stress draw, parameters and outcomes.
- `results/analysis.json`: full scenario results, simulation summary and input-file SHA-256.
- `index.html`: investment memo, scenario tables, NOI chart, diligence questions and downloads.

## Calculation conventions

1. Initial uses = price + price x acquisition cost allowance + initial capex. Initial debt = price x LTV. Equity funds the balance.
2. Occupied area = total area x baseline occupancy. Rent grows annually. Only occupied area is subject to the specified rollover fraction.
3. Rollover-year lost rent = occupied area x rollover fraction x current monthly rent x downtime months. The model assumes the space relets after that downtime without permanently changing baseline occupancy.
4. NOI = collected rent - property expenses. Expenses apply to total area and escalate independently of rent; expense recoveries are not modeled.
5. Unlevered operating cash = NOI - reserve - rollover TI / leasing costs. Reserves are treated as retained cash unavailable to equity and not recovered at exit.
6. Annual debt payment is the standard annuity payment; principal repayment is capped at the opening balance. Debt is fully repaid at maturity or from sale proceeds.
7. Net sale proceeds = year N+1 NOI / exit cap x (1 - sale cost). Levered sale proceeds also deduct year N closing debt.
8. All cash flows occur at year end except the time-zero investment. Taxes, tax shields, financing fees, deposits and mid-year timing are excluded.
9. NOI DSCR = NOI / scheduled principal plus interest. It excludes leasing costs and reserves. A separate post-capex coverage field is provided; do not mistake NOI coverage for distributable cash.
10. IRR is deliberately withheld for multiple sign changes rather than reporting an arbitrary root. NPV remains the primary decision metric. The base levered cash flows include a year-three equity call. Equity multiple includes every negative contribution.

## Simulation design

For each of 2,000 draws, let S and four independent epsilon terms be standard normal variables. Use:

- occupancy = clip(0.90 - 0.04 S + 0.02 epsilon, 0.60, 0.99)
- annual rent growth = clip(0.05 - 0.015 S + 0.008 epsilon, -0.03, 0.10)
- exit cap = clip(0.08 + 0.006 S + 0.003 epsilon, 0.055, 0.12)
- downtime months = clip(6 + 1.5 S + epsilon, 0, 12)

One sampled growth rate applies throughout the holding period; this is parameter uncertainty, not a simulated annual time path. The shared stress factor creates adverse dependence. Only 8.3% of the specified draws pass both screens; this is a conditional model frequency, **not a calibrated probability of a real investment succeeding**. Quantiles use the 100th and 1,900th order statistics for the 5th and 95th percentiles; the median is the mean of the middle observations.

## Data provenance and limitations

All property inputs are synthetic analyst assumptions. Bengaluru is a case label; no specific asset, owner, tenant, transaction or company performance is represented. The 6% acquisition allowance is not a legal or tax rate. No live market rents, comparable transactions or proprietary internship data are used. The case is not a recommendation to buy, sell or finance a property.

An actual transaction requires a lease-level rent roll, micro-market evidence, independent technical and legal diligence, taxes, lender terms, more granular capex and properly calibrated distributions. The model assumes a single rollover event and stable baseline occupancy outside that event. It is not a full tenant-level lease engine or a complete development feasibility model.

## Role relevance

This case demonstrates cash-flow forecasting, valuation sensitivity, debt analysis, risk screening, reproducibility and investment-memo writing. JLL's [India capital markets careers page](https://www.jll.com/en-in/careers/finance) describes data-driven investment decisions and risk management. Its [investment-modeling role description](https://jll.wd1.myworkdayjobs.com/en-US/jllcareers/job/SME--Investment-Modeling_REQ496429) provides useful examples of cash-flow forecasting and valuation work; it is not presented as an undergraduate opening.

## Authorship and learning

Developed for Anjaney Malhotra's portfolio with AI coding assistance. The candidate should reproduce the results, explain the formulas and challenge the assumptions before presenting the work in interviews. This project does not claim employer sponsorship, live-deal experience or independently achieved investment returns.
