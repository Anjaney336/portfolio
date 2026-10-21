"""Illustrative annual property underwriting. Cash flows in nominal INR, end-year.

No market-data feed or investment recommendation. Uses a simplified fixed-occupancy
rent model with one explicit lease-rollover event, amortizing fixed-rate debt,
and year N+1 NOI capitalized at disposal. See README for omitted costs and risks.
"""
from dataclasses import dataclass, asdict
import math

@dataclass(frozen=True)
class Assumptions:
    case: str = 'Illustrative Bengaluru office acquisition'
    currency: str = 'INR'
    area_sqft: float = 100000
    purchase_price: float = 1e9
    acquisition_cost_pct: float = .06
    initial_capex: float = 2e7
    rent_psf_month: float = 90
    occupancy: float = .90
    rent_growth: float = .05
    opex_psf_year: float = 180
    opex_growth: float = .05
    reserve_pct_revenue: float = .03
    ltv: float = .55
    interest_rate: float = .09
    amortization_years: int = 15
    hold_years: int = 5
    exit_cap_rate: float = .08
    sale_cost_pct: float = .02
    unlevered_discount_rate: float = .11
    equity_hurdle: float = .15
    minimum_dscr: float = 1.25
    rollover_year: int = 3
    rollover_share: float = .30
    downtime_months: float = 6
    tenant_improvements_psf: float = 800
    leasing_fee_months: float = 2

    def validate(self):
        for k,v in asdict(self).items():
            if isinstance(v,(int,float)) and not math.isfinite(v):
                raise ValueError(f'{k} must be finite')
        for k in ('area_sqft','purchase_price','rent_psf_month','exit_cap_rate','minimum_dscr'):
            if getattr(self,k)<=0: raise ValueError(f'{k} must be positive')
        for k in ('occupancy','rollover_share'):
            if not 0<=getattr(self,k)<=1: raise ValueError(f'{k} outside [0,1]')
        for k in ('ltv','acquisition_cost_pct','sale_cost_pct','reserve_pct_revenue','interest_rate'):
            if not 0<=getattr(self,k)<1: raise ValueError(f'{k} outside [0,1)')
        for k in ('rent_growth','opex_growth','unlevered_discount_rate','equity_hurdle'):
            if getattr(self,k)<=-1: raise ValueError(f'{k} must exceed -1')
        for k in ('initial_capex','opex_psf_year','tenant_improvements_psf','leasing_fee_months'):
            if getattr(self,k)<0: raise ValueError(f'{k} must be nonnegative')
        if not 0<=self.downtime_months<=12: raise ValueError('downtime outside [0,12]')
        for k in ('hold_years','amortization_years','rollover_year'):
            if type(getattr(self,k)) is not int or getattr(self,k)<1: raise ValueError(f'{k} must be positive integer')

def npv(rate, flows):
    if rate<=-1: raise ValueError('discount rate must exceed -1')
    return sum(cf/(1+rate)**t for t,cf in enumerate(flows))

def irr(flows):
    """Unique annual IRR for conventional cash flows; None for ambiguous patterns.

    No arbitrary root is reported when more than one sign change is present.
    NPV at a stated hurdle remains defined even when IRR is not.
    """
    signs=[1 if x>0 else -1 for x in flows if x!=0]
    if not signs or signs[0]!=-1 or signs[-1]!=1: return None
    if sum(a!=b for a,b in zip(signs,signs[1:]))!=1: return None
    lo,hi=-.9999,1.
    while npv(hi,flows)>0 and hi<1e6: hi=2*hi+1
    if npv(hi,flows)>0: return None
    for _ in range(120):
        mid=(lo+hi)/2
        if npv(mid,flows)>0: lo=mid
        else: hi=mid
    return (lo+hi)/2

def payment(principal,rate,years):
    return principal/years if rate==0 else principal*rate/(1-(1+rate)**(-years))

def underwrite(a):
    a.validate()
    cost=a.purchase_price*(1+a.acquisition_cost_pct)+a.initial_capex
    debt=a.purchase_price*a.ltv
    equity=cost-debt
    annual_payment=payment(debt,a.interest_rate,a.amortization_years)
    balance=debt
    rows=[]
    for year in range(1,a.hold_years+2):
        rent=a.rent_psf_month*(1+a.rent_growth)**(year-1)
        occupied=a.area_sqft*a.occupancy
        rollover=occupied*a.rollover_share if year==a.rollover_year else 0
        gross=occupied*rent*12
        lost=rollover*rent*a.downtime_months
        revenue=gross-lost
        opex=a.area_sqft*a.opex_psf_year*(1+a.opex_growth)**(year-1)
        noi=revenue-opex
        reserve=revenue*a.reserve_pct_revenue
        leasing_capex=rollover*(a.tenant_improvements_psf+rent*a.leasing_fee_months)
        unlevered=noi-reserve-leasing_capex
        opening=balance
        interest=opening*a.interest_rate
        principal=min(opening,max(0,annual_payment-interest))
        service=interest+principal
        balance=max(0,opening-principal)
        rows.append(dict(year=year,rent_psf_month=rent,gross_rent=gross,lost_rent=lost,
            revenue=revenue,opex=opex,noi=noi,reserve=reserve,leasing_capex=leasing_capex,
            unlevered_cf=unlevered,opening_debt=opening,interest=interest,
            principal=principal,debt_service=service,closing_debt=balance,
            dscr=noi/service if service else None,
            post_capex_coverage=unlevered/service if service else None,
            equity_operating_cf=unlevered-service))
    terminal=rows[-1]['noi']/a.exit_cap_rate
    net_sale=terminal*(1-a.sale_cost_pct)
    sale_equity=net_sale-rows[a.hold_years-1]['closing_debt']
    ucf=[-cost]+[r['unlevered_cf'] for r in rows[:-1]]
    ecf=[-equity]+[r['equity_operating_cf'] for r in rows[:-1]]
    ucf[-1]+=net_sale; ecf[-1]+=sale_equity
    debt_cov=[r['dscr'] for r in rows[:-1] if r['dscr'] is not None]
    # This includes any later equity calls, not only time-zero equity.
    multiple=sum(max(0,c) for c in ecf)/(-sum(min(0,c) for c in ecf))
    hurdle_npv=npv(a.equity_hurdle,ecf)
    min_dscr=min(debt_cov) if debt_cov else None
    passed=hurdle_npv>=0 and (min_dscr is None or min_dscr>=a.minimum_dscr)
    return dict(assumptions=asdict(a),cash_flows=rows[:-1],forward_noi=rows[-1]['noi'],
        total_cost=cost,initial_equity=equity,initial_debt=debt,terminal_value=terminal,
        net_sale=net_sale,equity_sale_proceeds=sale_equity,unlevered_flows=ucf,equity_flows=ecf,
        unlevered_irr=irr(ucf),equity_irr=irr(ecf),equity_multiple=multiple,
        equity_npv=hurdle_npv,unlevered_npv=npv(a.unlevered_discount_rate,ucf),
        dcf_asset_value=npv(a.unlevered_discount_rate,[0]+ucf[1:]),
        minimum_dscr=min_dscr,passes_screen=passed)
