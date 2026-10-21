import unittest
from dataclasses import replace
from model import Assumptions,underwrite,irr,npv,payment

class ModelTests(unittest.TestCase):
    def test_known_irr(self):
        self.assertAlmostEqual(irr([-100,110]),.1,places=10)
        self.assertAlmostEqual(irr([-100,0,121]),.1,places=10)
        self.assertAlmostEqual(irr([-100,90]),-.1,places=10)
    def test_ambiguous_irr(self):
        self.assertIsNone(irr([-100,230,-132]))
        self.assertIsNone(irr([-100,-10]))
    def test_debt_free_reconciles(self):
        r=underwrite(replace(Assumptions(),ltv=0))
        self.assertEqual(r['equity_flows'],r['unlevered_flows'])
        self.assertIsNone(r['minimum_dscr'])
    def test_debt_identity(self):
        r=underwrite(Assumptions())
        for row in r['cash_flows']:
            self.assertAlmostEqual(row['opening_debt']-row['principal'],row['closing_debt'])
            self.assertAlmostEqual(row['debt_service'],row['interest']+row['principal'])
        self.assertAlmostEqual(sum(r['equity_flows'])-sum(r['unlevered_flows']),
                              -sum(x['interest'] for x in r['cash_flows']),places=5)
    def test_zero_interest_and_maturity(self):
        self.assertEqual(payment(100,0,5),20)
        r=underwrite(replace(Assumptions(),interest_rate=0,amortization_years=2))
        self.assertEqual(r['cash_flows'][1]['closing_debt'],0)
        self.assertEqual(r['cash_flows'][2]['debt_service'],0)
    def test_hand_calculation(self):
        a=replace(Assumptions(),area_sqft=100,rent_psf_month=10,occupancy=.8,
            opex_psf_year=12,rollover_share=0,reserve_pct_revenue=0,
            rent_growth=0,opex_growth=0)
        r=underwrite(a)
        self.assertEqual(r['cash_flows'][0]['noi'],8400)
        self.assertEqual(r['terminal_value'],105000)
    def test_rollover(self):
        a=Assumptions(); r=underwrite(a); y=r['cash_flows'][2]
        self.assertAlmostEqual(y['lost_rent'],a.area_sqft*a.occupancy*.3*90*1.05**2*6)
        self.assertGreater(y['leasing_capex'],0)
        self.assertEqual(r['cash_flows'][1]['leasing_capex'],0)
    def test_irr_npv_reconciliation(self):
        r=underwrite(replace(Assumptions(),rollover_share=0))
        self.assertAlmostEqual(npv(r['equity_irr'],r['equity_flows']),0,places=4)
    def test_sensitivity_direction(self):
        a=Assumptions(); r=underwrite(a)
        self.assertLess(underwrite(replace(a,exit_cap_rate=.10))['equity_npv'],r['equity_npv'])
        self.assertLess(underwrite(replace(a,occupancy=.7))['equity_npv'],r['equity_npv'])
    def test_validation(self):
        for change in ({'occupancy':1.1},{'exit_cap_rate':0},{'ltv':1},
                       {'rent_psf_month':float('nan')},{'downtime_months':13},
                       {'hold_years':2.5},{'interest_rate':-.1}):
            with self.assertRaises(ValueError): underwrite(replace(Assumptions(),**change))

if __name__=='__main__': unittest.main()
