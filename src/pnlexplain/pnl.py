"""Daily P&L production and attribution.

Two numbers are produced every day and compared:

ACTUAL P&L (what the books say), from official end-of-day marks:
    P&L = closing value - opening value + cash in the period
    value = position * (official clean price + accrued) / 100
    cash  = coupons received, trade settlements, amendment and cancel corrections

EXPLAINED P&L (what the risk says), built bottom-up:
    accrual       coupon interest earned on positions held overnight
    roll          pull-to-par and roll-down: reprice today on yesterday's curve
    rates         key-rate DV01 x change in each Treasury par yield
    convexity     0.5 x gamma x (DV01-weighted rate move)^2
    credit        CS01 x spread change + 0.5 x spread gamma x change^2
    new trades    (end-of-day mark - trade price) x notional
    amendments    cash effect of corrected trade prices
    cancellations reversal of cancelled trades

UNEXPLAINED = ACTUAL - EXPLAINED. Small on a normal day (second-order effects
and price rounding); large when something is wrong with a mark or a booking.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from .bonds import Bond
from .book import Book
from .curves import TENOR_LABELS
from .market import build_curve_set

EXPLAIN_COLS = ["accrual", "roll", "rates", "convexity", "credit",
                "new_trades", "amendments", "cancellations"]


class PnLEngine:
    def __init__(self, bonds: dict[str, Bond], par_yields: pd.DataFrame, spreads: pd.DataFrame,
                 book: Book, stale_marks: set[tuple[str, date]] = frozenset(), mark_dp: int = 3):
        self.bonds = bonds
        self.par = par_yields
        self.spreads = spreads
        self.book = book
        self.dates: list[date] = list(par_yields.index)
        self.curves = {d: build_curve_set(par_yields.loc[d].values) for d in self.dates}
        self.independent = self._model_clean_prices()
        self.official = self._official_marks(stale_marks, mark_dp)
        self._risk_cache: dict = {}

    # ---------- marks ----------
    def _model_clean_prices(self) -> pd.DataFrame:
        """Independent model price for every bond and date (the IPV benchmark)."""
        out = {}
        for b_id, b in self.bonds.items():
            out[b_id] = [b.clean_price(d, self.curves[d].base, self.spreads.loc[d, b_id]) for d in self.dates]
        return pd.DataFrame(out, index=self.dates)

    def _official_marks(self, stale: set[tuple[str, date]], dp: int) -> pd.DataFrame:
        """Front-office marks: model price rounded, except where the price feed went stale."""
        marks = self.independent.round(dp).copy()
        for i, d in enumerate(self.dates):
            for b_id in self.bonds:
                if (b_id, d) in stale and i > 0:
                    marks.loc[d, b_id] = marks.loc[self.dates[i - 1], b_id]
        return marks

    def official_dirty(self, b_id: str, d: date) -> float:
        return self.official.loc[d, b_id] + self.bonds[b_id].accrued(d)

    # ---------- risk ----------
    def risk(self, b_id: str, d: date) -> dict:
        """Sensitivities per 100 face on date d (per 1bp moves)."""
        key = (b_id, d)
        if key not in self._risk_cache:
            b, cs, s = self.bonds[b_id], self.curves[d], self.spreads.loc[d, b_id]
            pv = b.dirty_price(d, cs.base, s)
            krd = np.array([b.dirty_price(d, c, s) - pv for c in cs.key_rate_up])
            gamma = b.dirty_price(d, cs.parallel_up, s) + b.dirty_price(d, cs.parallel_down, s) - 2 * pv
            if b.kind == "UST":
                cs01 = cgamma = 0.0  # Treasuries carry rate risk only
            else:
                up, dn = b.dirty_price(d, cs.base, s + 1), b.dirty_price(d, cs.base, s - 1)
                cs01, cgamma = up - pv, up + dn - 2 * pv
            self._risk_cache[key] = dict(pv=pv, krd=krd, dv01=krd.sum(), gamma=gamma,
                                         cs01=cs01, cgamma=cgamma)
        return self._risk_cache[key]

    # ---------- the daily run ----------
    def run(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        daily, by_bond = [], []
        for prev, d in zip(self.dates[:-1], self.dates[1:]):
            dpar_bp = (self.par.loc[d].values - self.par.loc[prev].values) * 100.0
            day = dict(date=d, actual=0.0, cash=0.0, **{c: 0.0 for c in EXPLAIN_COLS})
            for b_id, b in self.bonds.items():
                row = self._bond_day(b_id, b, prev, d, dpar_bp)
                by_bond.append(row)
                for k in ["actual", "cash", *EXPLAIN_COLS]:
                    day[k] += row[k]
            day["explained"] = sum(day[c] for c in EXPLAIN_COLS)
            day["unexplained"] = day["actual"] - day["explained"]
            day["closing_value"] = self.book_value(d)
            day.update(self._market_moves(prev, d))
            daily.append(day)
        return pd.DataFrame(daily).set_index("date"), pd.DataFrame(by_bond)

    def _bond_day(self, b_id: str, b: Bond, prev: date, d: date, dpar_bp: np.ndarray) -> dict:
        book = self.book
        pos_prev, pos = book.position(b_id, prev), book.position(b_id, d)
        held = book.held_through(b_id, prev, d)
        ai_prev, ai = b.accrued(prev), b.accrued(d)
        cpn = b.coupon_paid(prev, d)

        # cash: coupons on overnight holdings, plus trade-related cash
        cash = held * cpn / 100.0
        new_pnl = amend_pnl = cancel_pnl = 0.0
        for t in book.new_trades(d):
            if t.bond_id != b_id:
                continue
            price = t.price_on(d)
            cash -= t.notional * (price + ai) / 100.0
            new_pnl += t.notional * (self.official.loc[d, b_id] - price) / 100.0
        for t, a in book.amendments(d):
            if t.bond_id != b_id or t.trade_date == d:
                continue
            adj = -t.notional * (a.new_price - a.old_price) / 100.0
            cash += adj
            amend_pnl += adj
        for t in book.cancels(d):
            if t.bond_id != b_id:
                continue
            refund = t.notional * (t.price_on(prev) + b.accrued(t.trade_date)) / 100.0
            cash += refund
            cancel_pnl += refund - t.notional * self.official_dirty(b_id, prev) / 100.0

        actual = (pos * self.official_dirty(b_id, d) - pos_prev * self.official_dirty(b_id, prev)) / 100.0 + cash

        # risk-based explain for the position held overnight, using yesterday's risk
        r = self.risk(b_id, prev)
        s_prev, s = self.spreads.loc[prev, b_id], self.spreads.loc[d, b_id]
        carry = b.dirty_price(d, self.curves[prev].base, s_prev) + cpn - r["pv"]
        accrual = ai - ai_prev + cpn
        rates = float(r["krd"] @ dpar_bp)
        eq_move = rates / r["dv01"] if abs(r["dv01"]) > 1e-12 else 0.0
        ds = s - s_prev
        f = held / 100.0
        row = dict(
            date=d, bond_id=b_id, position=pos, held_overnight=held,
            actual=actual, cash=cash,
            accrual=f * accrual,
            roll=f * (carry - accrual),
            rates=f * rates,
            convexity=f * 0.5 * r["gamma"] * eq_move ** 2,
            credit=f * (r["cs01"] * ds + 0.5 * r["cgamma"] * ds ** 2),
            new_trades=new_pnl, amendments=amend_pnl, cancellations=cancel_pnl,
            dv01=f * r["dv01"], cs01=f * r["cs01"], spread_change_bp=ds,
            official_clean=self.official.loc[d, b_id], independent_clean=self.independent.loc[d, b_id],
        )
        row["explained"] = sum(row[c] for c in EXPLAIN_COLS)
        row["unexplained"] = actual - row["explained"]
        return row

    def book_value(self, d: date) -> float:
        return sum(self.book.position(b_id, d) * self.official_dirty(b_id, d) / 100.0 for b_id in self.bonds)

    def _market_moves(self, prev: date, d: date) -> dict:
        moves = {f"{t}_chg_bp": (self.par.loc[d, t] - self.par.loc[prev, t]) * 100 for t in ["2Y", "10Y", "30Y"]}
        for bucket in ["A", "BBB", "BB"]:
            ids = [i for i, b in self.bonds.items() if b.rating == bucket]
            moves[f"{bucket}_spread_chg_bp"] = float((self.spreads.loc[d, ids] - self.spreads.loc[prev, ids]).mean())
        return moves


__all__ = ["PnLEngine", "EXPLAIN_COLS", "TENOR_LABELS"]
