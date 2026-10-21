"""Rebuild committed results and report with Python standard library only."""
from pathlib import Path
from dataclasses import replace
import csv, hashlib, json, math, random, statistics, html
from model import Assumptions, underwrite

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'
OUT.mkdir(exist_ok=True)
a=Assumptions(**json.loads((ROOT/'assumptions.json').read_text()))
base=underwrite(a)
scenarios={
 'Base':base,
 'Downside':underwrite(replace(a,occupancy=.80,rent_growth=.02,exit_cap_rate=.09,downtime_months=9)),
 'Upside':underwrite(replace(a,occupancy=.95,rent_growth=.06,exit_cap_rate=.075,downtime_months=3))}

def csv_write(name,rows):
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)

csv_write('annual_cash_flows.csv',base['cash_flows'])
grid=[]
for growth in [.01,.03,.05,.07,.09]:
    for cap in [.065,.075,.08,.085,.095]:
        r=underwrite(replace(a,rent_growth=growth,exit_cap_rate=cap))
        grid.append(dict(rent_growth=growth,exit_cap_rate=cap,equity_npv=r['equity_npv'],equity_irr=r['equity_irr'],minimum_dscr=r['minimum_dscr']))
csv_write('sensitivity.csv',grid)

# The common stress factor induces adverse dependence: lower occupancy/growth,
# wider exit cap and longer downtime. All distributions are illustrative.
rng=random.Random(20261021)
sim=[]
for i in range(2000):
    stress=rng.gauss(0,1)
    occ=max(.60,min(.99,a.occupancy-.04*stress+.02*rng.gauss(0,1)))
    growth=max(-.03,min(.10,a.rent_growth-.015*stress+.008*rng.gauss(0,1)))
    cap=max(.055,min(.12,a.exit_cap_rate+.006*stress+.003*rng.gauss(0,1)))
    downtime=max(0,min(12,a.downtime_months+1.5*stress+rng.gauss(0,1)))
    r=underwrite(replace(a,occupancy=occ,rent_growth=growth,exit_cap_rate=cap,downtime_months=downtime))
    sim.append(dict(draw=i+1,occupancy=occ,rent_growth=growth,exit_cap_rate=cap,downtime_months=downtime,
        equity_npv=r['equity_npv'],minimum_dscr=r['minimum_dscr'],equity_multiple=r['equity_multiple'],
        passes_screen=r['passes_screen']))
csv_write('simulation.csv',sim)
npvs=sorted(x['equity_npv'] for x in sim)
summary={'draws':len(sim),'seed':20261021,'npv_p05':npvs[99],'npv_median':statistics.median(npvs),
 'npv_p95':npvs[1899], 'screen_pass_frequency':sum(x['passes_screen'] for x in sim)/len(sim),
 'dscr_breach_frequency':sum(x['minimum_dscr']<a.minimum_dscr for x in sim)/len(sim),
 'assumptions_sha256':hashlib.sha256((ROOT/'assumptions.json').read_bytes()).hexdigest()}

# Solve maximum entry price satisfying both equity hurdle and NOI DSCR.
# Debt scales with price at constant LTV; not a fixed-debt optimization.
lo,hi=1,a.purchase_price*3
if underwrite(replace(a,purchase_price=hi))['passes_screen']:
    raise ValueError('Expand purchase price search bracket')
if not underwrite(replace(a,purchase_price=lo))['passes_screen']:
    raise ValueError('No feasible price at current fixed costs')
for _ in range(80):
    mid=(lo+hi)/2
    if underwrite(replace(a,purchase_price=mid))['passes_screen']:lo=mid
    else:hi=mid
summary['maximum_screen_price']=lo
summary['maximum_price_metrics']={k:underwrite(replace(a,purchase_price=lo))[k] for k in ['equity_npv','minimum_dscr']}
(OUT/'analysis.json').write_text(json.dumps({'scenarios':scenarios,'simulation':summary},indent=2,allow_nan=False))

def cr(v):return f'{v/1e7:,.2f}'
def pct(v):return 'Not reported*' if v is None else f'{v:.1%}'
def table(headers,rows):
    return '<div class="scroll"><table><thead><tr>'+''.join(f'<th>{html.escape(str(x))}</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{html.escape(str(x))}</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'

scenario_table=table(['Scenario','Equity NPV (INR cr)','Equity multiple','Min. NOI DSCR','Unlevered IRR','Screen'],[
 [name,cr(r['equity_npv']),f"{r['equity_multiple']:.2f}x",f"{r['minimum_dscr']:.2f}x",pct(r['unlevered_irr']),'Pass' if r['passes_screen'] else 'Fail'] for name,r in scenarios.items()])
cash_table=table(['Year','Revenue','NOI','Reserve','TI / leasing','Debt service','Equity CF before sale'],[
 [r['year']]+[cr(r[k]) for k in ['revenue','noi','reserve','leasing_capex','debt_service','equity_operating_cf']] for r in base['cash_flows']])
sens_table=table(['Rent growth / exit cap','6.5%','7.5%','8.0%','8.5%','9.5%'],[
 [f'{g:.0%}']+[cr(x['equity_npv']) for x in grid if x['rent_growth']==g] for g in [.01,.03,.05,.07,.09]])
assumption_table=table(['Input','Value'],[(k,str(v)) for k,v in base['assumptions'].items()])
bars=''
for i,r in enumerate(base['cash_flows']):
    h=r['noi']/1e6*2
    bars+=f'<rect x="{70+i*100}" y="{230-h}" width="52" height="{h}" fill="#176b61"/><text x="{96+i*100}" y="{220-h}" text-anchor="middle">{cr(r["noi"])}</text><text x="{96+i*100}" y="255" text-anchor="middle">Year {i+1}</text>'

body=f'''
<header><div class="eyebrow">ANJANEY MALHOTRA / INVESTMENT ANALYSIS / OCTOBER 2026</div>
<h1>What price makes<br>the risk worth taking?</h1>
<p class="lead">A five-year underwriting case for a 100,000 sq ft Bengaluru office asset.</p>
<p class="label">ILLUSTRATIVE CASE · NOMINAL INR · PRE-TAX · NO LIVE MARKET DATA</p></header>
<main><section><h2>01 / Investment view</h2>
<p class="decision">Decline at INR {cr(a.purchase_price)} crore under the stated screening rules.</p>
<p>The base case misses the {a.equity_hurdle:.0%} equity return hurdle and the {a.minimum_dscr:.2f}x minimum NOI debt-service coverage screen. A year-three lease rollover creates an additional equity cash requirement, even though NOI remains positive.</p>
<div class="cards"><div><span>Equity NPV at 15%</span><strong>{cr(base['equity_npv'])} cr</strong></div><div><span>Minimum NOI DSCR</span><strong>{base['minimum_dscr']:.2f}x</strong></div><div><span>Maximum screened entry price</span><strong>{cr(lo)} cr</strong></div></div>
<p>The screened entry price holds every other input constant and resizes debt at {a.ltv:.0%} LTV. It is a model threshold, not an independently supported market valuation. No acquisition recommendation follows from this synthetic case.</p></section>
<section><h2>02 / Operating cash flow and rollover</h2>
<svg role="img" aria-label="Annual NOI in INR crore, showing the year-three rollover reduction" viewBox="0 0 620 280">{bars}</svg>
<p>All amounts below are INR crore. Rollover applies to 30% of occupied area in year three, with six months of lost rent plus tenant improvements and leasing fees. Fixed property expenses continue during vacancy.</p>{cash_table}
<p>Year-five gross disposal value: INR {cr(base['terminal_value'])} crore, based on year-six NOI and an {a.exit_cap_rate:.0%} cap rate. Selling costs and outstanding debt are deducted separately. Year-three negative equity operating cash flow is funded as an additional equity contribution; it is not hidden in the equity multiple.</p></section>
<section><h2>03 / Scenario comparison</h2>{scenario_table}
<p>Downside: 80% occupancy, 2% rent growth, 9% exit cap, nine months downtime. Upside: 95% occupancy, 6% growth, 7.5% exit cap, three months downtime. These are analyst assumptions, not forecasts.</p>
<p>*Levered IRR is intentionally not reported when cash flows have multiple sign changes. Base cash flows require a later equity injection; NPV at the stated hurdle is the primary decision metric. Unlevered IRR is reported only for a conventional sign pattern.</p></section>
<section><h2>04 / Exit pricing versus rent growth</h2><p>Equity NPV in INR crore; all other inputs held at the base case.</p>{sens_table}</section>
<section><h2>05 / Correlated stress analysis</h2>
<p>2,000 reproducible simulations use a shared adverse stress factor across occupancy, rent growth, exit cap rates and downtime. Under these illustrative distributions, {summary['screen_pass_frequency']:.1%} pass both screens and {summary['dscr_breach_frequency']:.1%} breach the NOI DSCR threshold.</p>
<div class="cards"><div><span>5th percentile equity NPV</span><strong>{cr(summary['npv_p05'])} cr</strong></div><div><span>Median equity NPV</span><strong>{cr(summary['npv_median'])} cr</strong></div><div><span>95th percentile equity NPV</span><strong>{cr(summary['npv_p95'])} cr</strong></div></div>
<p>These frequencies are conditional model outputs, not estimated real-world probabilities. Distributions are not fitted to market data. Seed: 20261021. The CSV includes every draw for audit.</p></section>
<section><h2>06 / Diligence before an actual investment</h2>
<ul><li>Reconcile the rent roll to executed leases, escalation clauses, expiries, deposits, rent-free periods and tenant credit.</li>
<li>Validate market rents, comparable sales, exit liquidity and cap-rate evidence for the exact micro-market.</li>
<li>Inspect title, permitted use, approvals, encumbrances and transaction structure with qualified advisers.</li>
<li>Obtain an engineering survey covering HVAC, lifts, fire systems, energy use, deferred maintenance and replacement capex.</li>
<li>Reconcile gross versus net rents, recoverable expenses, property taxes, insurance, financing terms and all transaction charges.</li></ul>
<p>Limitations: annual timing, one rollover event, fixed occupancy outside rollover, no taxes, no GST, no lender fees, no refinancing, no inflation-linked market calibration and no probabilistic tenant defaults. The 6% acquisition-cost allowance is an illustrative aggregate, not a statement of applicable statutory charges. Reserve deductions represent actual retained cash unavailable to equity and are not recovered at exit. NOI DSCR excludes reserves and leasing capex; post-capex coverage is separately supplied in the CSV.</p></section>
<section><h2>07 / Reproduce and inspect</h2><p>Built with Python's standard library. Run <code>python -m unittest -v</code>, then <code>python run_analysis.py</code> from the project folder.</p>
<nav><a href="https://github.com/Anjaney336/bengaluru-office-underwriting">Source and tests</a><a href="results/annual_cash_flows.csv">Cash-flow CSV</a><a href="results/sensitivity.csv">Sensitivity CSV</a><a href="results/simulation.csv">Simulation CSV</a><a href="results/analysis.json">Full results</a><a href="https://anjaney336.github.io/portfolio/">Portfolio</a></nav>
<details><summary>All assumptions and units</summary>{assumption_table}<p>Rent: INR / sq ft / month. Operating expenses: INR / sq ft / year. TI: INR / sq ft. All monetary cash-flow fields: INR. Rates are decimal fractions.</p></details>
<p class="small">Portfolio research case developed with AI coding assistance; inputs and limitations are explicit so the model can be inspected, challenged and extended.</p></section></main>
'''
css='''*{box-sizing:border-box}body{margin:0;background:#f4f3ee;color:#192b31;font:17px/1.65 Georgia,serif}header{background:#122d32;color:#f6f3e9;padding:70px max(6vw,24px)}header>*,main{max-width:1050px;margin-left:auto;margin-right:auto}h1{font:600 clamp(38px,6vw,68px)/1.08 Arial,sans-serif;letter-spacing:-2px;margin-top:30px;margin-bottom:25px}h2{font:600 24px/1.3 Arial,sans-serif;margin:0 0 22px}.eyebrow,.label,.small{font:12px/1.6 Arial,sans-serif;letter-spacing:1px}.lead{font-size:22px}.label{color:#bdd0c8}main{padding:0 24px 40px}section{padding:42px 0;border-bottom:1px solid #d5dcd5}.decision{font-size:26px;color:#99512c}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:28px 0}.cards>div{padding:24px;background:white;border-top:3px solid #b36b42}.cards span{display:block;font:13px Arial,sans-serif;color:#516366}.cards strong{display:block;font:600 30px Arial,sans-serif;margin-top:14px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font:14px/1.5 Arial,sans-serif;background:white}th,td{text-align:right;padding:13px;border-bottom:1px solid #dfe6e0}th:first-child,td:first-child{text-align:left}th{background:#e5ece7}nav{display:flex;flex-wrap:wrap;gap:12px}a{color:#176b61}nav a{padding:10px 14px;border:1px solid #176b61;text-decoration:none;font:14px Arial,sans-serif}svg{max-width:650px;width:100%;font:14px Arial,sans-serif}details{margin-top:28px}summary{cursor:pointer;font-weight:bold}code{background:#e5ece7;padding:3px}li{margin-bottom:10px}@media(max-width:650px){.cards{grid-template-columns:1fr}header{padding-top:45px}h1{letter-spacing:-1px}section{padding:30px 0}}'''
(ROOT/'index.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bengaluru Office Underwriting | Anjaney Malhotra</title><style>'+css+'</style></head><body>'+body+'</body></html>',encoding='utf-8')
print(json.dumps(summary,indent=2))
