"""Trade blotter and positions.

The blotter is a list of events, as a booking system would hold them:

* NEW     a trade is booked (bond, side, notional, clean price)
* AMEND   the price of an existing trade is corrected
* CANCEL  an existing trade is cancelled, as if it never happened

Positions on any date are the opening position plus every trade that is live
on that date. Trades settle on trade date in this model (stated in README).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd


@dataclass
class Amendment:
    event_date: date
    old_price: float
    new_price: float
    comment: str


@dataclass
class Trade:
    trade_id: str
    bond_id: str
    trade_date: date
    notional: float          # signed face amount: + bought, - sold
    booked_price: float      # clean price as first booked
    comment: str = ""
    cancel_date: date | None = None
    cancel_comment: str = ""
    amendments: list[Amendment] = field(default_factory=list)

    def price_on(self, d: date) -> float:
        """Clean price as it stood in the system at the end of date d."""
        price = self.booked_price
        for a in self.amendments:
            if a.event_date <= d:
                price = a.new_price
        return price

    def live_on(self, d: date) -> bool:
        return self.trade_date <= d and (self.cancel_date is None or self.cancel_date > d)


def load_trades(path) -> dict[str, Trade]:
    df = pd.read_csv(path, parse_dates=["event_date"], dtype={"trade_id": str})
    df = df.sort_values(["event_date", "event_id"])
    trades: dict[str, Trade] = {}
    for r in df.itertuples(index=False):
        d = r.event_date.date()
        comment = "" if pd.isna(r.comment) else str(r.comment)
        if r.action == "NEW":
            if r.trade_id in trades:
                raise ValueError(f"duplicate trade id {r.trade_id}")
            sign = 1.0 if r.side == "BUY" else -1.0
            trades[r.trade_id] = Trade(r.trade_id, r.bond_id, d, sign * float(r.notional),
                                       float(r.price), comment)
        elif r.action == "AMEND":
            t = trades[r.trade_id]
            if t.cancel_date is not None:
                raise ValueError(f"amend on cancelled trade {r.trade_id}")
            t.amendments.append(Amendment(d, t.price_on(d), float(r.price), comment))
        elif r.action == "CANCEL":
            t = trades[r.trade_id]
            if d <= t.trade_date:
                raise ValueError("same-day cancels are not modelled")
            t.cancel_date, t.cancel_comment = d, comment
        else:
            raise ValueError(f"unknown action {r.action}")
    return trades


class Book:
    def __init__(self, opening: dict[str, float], trades: dict[str, Trade]):
        self.opening = opening
        self.trades = trades

    def position(self, bond_id: str, d: date) -> float:
        live = sum(t.notional for t in self.trades.values() if t.bond_id == bond_id and t.live_on(d))
        return self.opening.get(bond_id, 0.0) + live

    def held_through(self, bond_id: str, prev: date, d: date) -> float:
        """Position held overnight from prev to d (excludes today's new and cancelled trades)."""
        live = sum(t.notional for t in self.trades.values()
                   if t.bond_id == bond_id and t.live_on(prev) and t.live_on(d))
        return self.opening.get(bond_id, 0.0) + live

    def new_trades(self, d: date) -> list[Trade]:
        return [t for t in self.trades.values() if t.trade_date == d]

    def amendments(self, d: date) -> list[tuple[Trade, Amendment]]:
        return [(t, a) for t in self.trades.values() for a in t.amendments if a.event_date == d]

    def cancels(self, d: date) -> list[Trade]:
        return [t for t in self.trades.values() if t.cancel_date == d]


def load_opening(path) -> dict[str, float]:
    df = pd.read_csv(path)
    return dict(zip(df.bond_id, df.notional.astype(float)))
