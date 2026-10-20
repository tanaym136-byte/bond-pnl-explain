"""Fixed-coupon bonds: coupon schedule, accrued interest, pricing and risk.

Prices are per 100 face. A bond is priced by discounting its remaining cash
flows on the Treasury zero curve plus a constant z-spread:

    dirty price = sum( CF_i * DF(t_i) * exp(-s * t_i) )

Simplifications (stated in the README): valuation is on trade date (no
settlement lag), coupon dates are not adjusted for weekends, and time for
discounting is ACT/365 from the valuation date.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from functools import cached_property

import numpy as np
from dateutil.relativedelta import relativedelta

from .curves import ZeroCurve

BP = 1e-4


def days_30_360(d1: date, d2: date) -> int:
    """US (bond basis) 30/360 day count."""
    day1 = min(d1.day, 30)
    day2 = 30 if (d2.day == 31 and day1 >= 30) else d2.day
    return (d2.year - d1.year) * 360 + (d2.month - d1.month) * 30 + (day2 - day1)


@dataclass(frozen=True)
class Bond:
    bond_id: str
    description: str
    kind: str          # "UST" or "CORP"
    rating: str        # "UST", "AA", "A", "BBB", "BB"
    coupon: float      # annual coupon in percent, paid semi-annually
    maturity: date
    day_count: str     # "ACT/ACT" or "30/360"
    start_spread_bp: float = 0.0
    _cache: dict = field(default_factory=dict, compare=False, repr=False)

    @cached_property
    def coupon_dates(self) -> list[date]:
        """Semi-annual dates counted back from maturity (no business-day roll)."""
        dates, k = [], 0
        while True:
            d = self.maturity - relativedelta(months=6 * k)
            if d.year < 2015:
                break
            dates.append(d)
            k += 1
        return sorted(dates)

    def prev_next_coupon(self, d: date) -> tuple[date, date]:
        dates = self.coupon_dates
        nxt = next(c for c in dates if c > d)
        i = dates.index(nxt)
        prev = dates[i - 1] if i > 0 else nxt - relativedelta(months=6)
        return prev, nxt

    def accrued(self, d: date) -> float:
        """Accrued interest per 100 face at date d."""
        if d >= self.maturity:
            return 0.0
        prev, nxt = self.prev_next_coupon(d)
        if self.day_count == "30/360":
            return self.coupon * days_30_360(prev, d) / 360.0
        if self.day_count == "ACT/ACT":
            return self.coupon / 2.0 * (d - prev).days / (nxt - prev).days
        raise ValueError(self.day_count)

    def coupon_paid(self, d0: date, d1: date) -> float:
        """Coupon cash per 100 face for coupon dates in (d0, d1]."""
        n = sum(1 for c in self.coupon_dates if d0 < c <= d1)
        return n * self.coupon / 2.0

    def cashflows(self, d: date) -> tuple[np.ndarray, np.ndarray]:
        """Remaining cash flows strictly after d: (times in years, amounts per 100)."""
        key = ("cf", d)
        if key not in self._cache:
            dates = [c for c in self.coupon_dates if c > d]
            t = np.array([(c - d).days / 365.0 for c in dates])
            cf = np.full(len(dates), self.coupon / 2.0)
            cf[-1] += 100.0
            self._cache[key] = (t, cf)
        return self._cache[key]

    def dirty_price(self, d: date, curve: ZeroCurve, spread_bp: float) -> float:
        t, cf = self.cashflows(d)
        return float((cf * curve.df(t) * np.exp(-spread_bp * BP * t)).sum())

    def clean_price(self, d: date, curve: ZeroCurve, spread_bp: float) -> float:
        return self.dirty_price(d, curve, spread_bp) - self.accrued(d)


def load_bonds(path) -> dict[str, Bond]:
    import pandas as pd

    df = pd.read_csv(path, parse_dates=["maturity"])
    bonds = {}
    for r in df.itertuples(index=False):
        bonds[r.bond_id] = Bond(
            bond_id=r.bond_id,
            description=r.description,
            kind=r.kind,
            rating=r.rating,
            coupon=float(r.coupon),
            maturity=r.maturity.date(),
            day_count=r.day_count,
            start_spread_bp=float(r.start_spread_bp),
        )
    return bonds
