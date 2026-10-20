from datetime import date

import numpy as np
import pytest

from pnlexplain.bonds import Bond, days_30_360
from pnlexplain.curves import ZeroCurve, bootstrap, par_bond_price_on_grid
from pnlexplain.market import load_par_yields

from conftest import ROOT


def test_bootstrap_reprices_every_par_tenor_to_100():
    par = load_par_yields(ROOT / "data" / "treasury_par_yields.csv")
    for d in par.index[[0, 15, -1]]:
        curve = bootstrap(par.loc[d].values)
        for label, years in [("1Y", 1), ("2Y", 2), ("5Y", 5), ("10Y", 10), ("30Y", 30)]:
            assert par_bond_price_on_grid(curve, par.loc[d, label], years) == pytest.approx(100.0, abs=1e-9)


def test_discount_factors_fall_with_maturity():
    par = load_par_yields(ROOT / "data" / "treasury_par_yields.csv")
    curve = bootstrap(par.iloc[0].values)
    dfs = curve.df(np.linspace(0.1, 30, 300))
    assert np.all(np.diff(dfs) < 0)


def test_30_360_day_count():
    assert days_30_360(date(2026, 3, 15), date(2026, 9, 15)) == 180
    assert days_30_360(date(2026, 1, 31), date(2026, 3, 1)) == 31
    assert days_30_360(date(2026, 3, 31), date(2026, 4, 30)) == 30


def corp():
    return Bond("X", "test", "CORP", "BBB", 6.0, date(2030, 3, 15), "30/360")


def test_accrued_interest_and_coupon_dates():
    b = corp()
    assert b.accrued(date(2026, 3, 15)) == 0.0
    assert b.accrued(date(2026, 6, 15)) == pytest.approx(1.5)        # 90/360 * 6
    assert b.coupon_paid(date(2026, 9, 14), date(2026, 9, 15)) == 3.0
    assert b.coupon_paid(date(2026, 9, 15), date(2026, 9, 16)) == 0.0


def test_price_matches_hand_calculation_on_flat_curve():
    b, d = corp(), date(2026, 9, 15)
    curve = ZeroCurve(np.array([0.1, 40.0]), np.array([0.05, 0.05]))
    t, cf = b.cashflows(d)
    expected = float((cf * np.exp(-(0.05 + 0.01) * t)).sum())
    assert b.dirty_price(d, curve, 100.0) == pytest.approx(expected, rel=1e-12)


def test_risk_signs_and_key_rates_add_up(engine):
    d = engine.dates[0]
    for b_id, b in engine.bonds.items():
        r = engine.risk(b_id, d)
        assert r["dv01"] < 0                       # price falls when yields rise
        assert r["gamma"] > 0                      # positive convexity
        if b.kind == "CORP":
            assert r["cs01"] < 0
        parallel = (b.dirty_price(d, engine.curves[d].parallel_up, engine.spreads.loc[d, b_id]) - r["pv"])
        assert r["dv01"] == pytest.approx(parallel, rel=0.01)   # key rates sum to the parallel DV01
