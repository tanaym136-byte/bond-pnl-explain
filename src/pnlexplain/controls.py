"""Daily product control checks.

1. Unexplained P&L    |actual - explained| above max(USD 10k, 5% of |actual|)
2. Trade review (NAC) every New, Amend and Cancel is listed with its P&L effect;
                      new trades priced away from the independent mark, and
                      possible duplicates, are flagged
3. Stale prices       official mark unchanged while the independent price moved
4. IPV                official mark vs independent price, in USD on the position
5. Reconciliation     closing value = opening value + P&L - net cash, by period
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from .pnl import PnLEngine

UNEXPLAINED_ABS_USD = 10_000
UNEXPLAINED_REL = 0.05
PRICE_TOLERANCE_PTS = {"UST": 0.25, "AA": 0.75, "A": 0.75, "BBB": 0.75, "BB": 1.50}
STALE_MOVE_PTS = 0.02
IPV_TOLERANCE_USD = 10_000


def unexplained_breaks(daily: pd.DataFrame) -> pd.DataFrame:
    d = daily.copy()
    d["threshold"] = (d["actual"].abs() * UNEXPLAINED_REL).clip(lower=UNEXPLAINED_ABS_USD)
    d["break"] = d["unexplained"].abs() > d["threshold"]
    return d[["actual", "explained", "unexplained", "threshold", "break"]]


def trade_review(engine: PnLEngine) -> pd.DataFrame:
    """New, Amends and Cancels report for the period."""
    rows = []
    trades = engine.book.trades
    for t in trades.values():
        b = engine.bonds[t.bond_id]
        mark = engine.independent.loc[t.trade_date, t.bond_id]
        diff = t.booked_price - mark
        dupes = [o.trade_id for o in trades.values()
                 if o.trade_id != t.trade_id and o.trade_date == t.trade_date and o.bond_id == t.bond_id
                 and o.notional == t.notional and o.booked_price == t.booked_price]
        issues = []
        if abs(diff) > PRICE_TOLERANCE_PTS[b.rating]:
            issues.append(f"price {diff:+.2f} pts from independent mark (tolerance {PRICE_TOLERANCE_PTS[b.rating]:.2f})")
        if dupes:
            issues.append(f"possible duplicate of {', '.join(dupes)}")
        rows.append(dict(date=t.trade_date, event="NEW", trade_id=t.trade_id, bond_id=t.bond_id,
                         notional=t.notional, price=t.booked_price, independent_mark=round(mark, 3),
                         pnl_impact=t.notional * (engine.official.loc[t.trade_date, t.bond_id] - t.booked_price) / 100,
                         flag=bool(issues), note="; ".join(issues) or t.comment))
        for a in t.amendments:
            rows.append(dict(date=a.event_date, event="AMEND", trade_id=t.trade_id, bond_id=t.bond_id,
                             notional=t.notional, price=a.new_price, independent_mark=None,
                             pnl_impact=-t.notional * (a.new_price - a.old_price) / 100,
                             flag=True, note=a.comment))
        if t.cancel_date is not None:
            prev = engine.dates[engine.dates.index(t.cancel_date) - 1]
            refund = t.notional * (t.price_on(prev) + b.accrued(t.trade_date)) / 100
            impact = refund - t.notional * engine.official_dirty(t.bond_id, prev) / 100
            rows.append(dict(date=t.cancel_date, event="CANCEL", trade_id=t.trade_id, bond_id=t.bond_id,
                             notional=t.notional, price=None, independent_mark=None, pnl_impact=impact,
                             flag=True, note=t.cancel_comment))
    return pd.DataFrame(rows).sort_values(["date", "trade_id", "event"]).reset_index(drop=True)


def stale_prices(engine: PnLEngine) -> pd.DataFrame:
    rows = []
    off, ind = engine.official, engine.independent
    for prev, d in zip(engine.dates[:-1], engine.dates[1:]):
        for b_id in engine.bonds:
            moved = ind.loc[d, b_id] - ind.loc[prev, b_id]
            if off.loc[d, b_id] == off.loc[prev, b_id] and abs(moved) > STALE_MOVE_PTS:
                rows.append(dict(date=d, bond_id=b_id, official=off.loc[d, b_id],
                                 independent=round(ind.loc[d, b_id], 3), independent_move=round(moved, 3)))
    return pd.DataFrame(rows, columns=["date", "bond_id", "official", "independent", "independent_move"])


def ipv(engine: PnLEngine) -> pd.DataFrame:
    rows = []
    for d in engine.dates:
        for b_id in engine.bonds:
            pos = engine.book.position(b_id, d)
            var = (engine.official.loc[d, b_id] - engine.independent.loc[d, b_id]) * pos / 100
            rows.append(dict(date=d, bond_id=b_id, position=pos, official=engine.official.loc[d, b_id],
                             independent=engine.independent.loc[d, b_id], variance_usd=var,
                             breach=abs(var) > IPV_TOLERANCE_USD))
    return pd.DataFrame(rows)


def reconcile(engine: PnLEngine, daily: pd.DataFrame, start: date, end: date) -> dict:
    """Roll the book value forward from start to end and check it ties to P&L."""
    period = daily.loc[(daily.index > start) & (daily.index <= end)]
    opening, closing = engine.book_value(start), engine.book_value(end)
    pnl, cash = period["actual"].sum(), period["cash"].sum()
    return dict(start=start, end=end, opening_value=opening, pnl=pnl, net_cash_received=cash,
                closing_value=closing, difference=closing - (opening + pnl - cash))
