from datetime import date

import pytest

from pnlexplain import controls
from pnlexplain.book import Book, Trade
from pnlexplain.pnl import EXPLAIN_COLS, PnLEngine

STALE_DAYS = {date(2026, 10, 5), date(2026, 10, 6), date(2026, 10, 7)}


def test_explain_components_add_up(results):
    daily, by_bond = results
    assert (daily[EXPLAIN_COLS].sum(axis=1) - daily["explained"]).abs().max() < 1e-6
    total = by_bond.groupby("date")["actual"].sum()
    assert (total - daily["actual"]).abs().max() < 1e-6


def test_book_value_rolls_forward_to_the_cent(engine, results):
    daily, _ = results
    for start, end in [(engine.dates[0], date(2026, 9, 30)), (engine.dates[0], engine.dates[-1])]:
        assert abs(controls.reconcile(engine, daily, start, end)["difference"]) < 0.01


def test_risk_explains_normal_days(results):
    daily, _ = results
    normal = daily.loc[[d for d in daily.index if d not in STALE_DAYS and d != date(2026, 10, 8)]]
    assert normal["unexplained"].abs().max() < 1_500
    assert 1 - normal["unexplained"].abs().sum() / normal["actual"].abs().sum() > 0.99


def test_only_the_stale_mark_days_break_the_unexplained_threshold(results):
    daily, _ = results
    breaks = controls.unexplained_breaks(daily)
    assert set(breaks.index[breaks["break"]]) == STALE_DAYS


def test_trade_review_catches_keying_error_and_duplicate(engine):
    nac = controls.trade_review(engine)
    flagged_new = nac[(nac.event == "NEW") & nac.flag]
    assert set(flagged_new.trade_id) == {"T1002", "T1005", "T1006"}
    assert not nac[(nac.event == "NEW") & ~nac.flag].trade_id.isin(["T1002"]).any()


def test_stale_price_and_ipv_checks(engine):
    stale = controls.stale_prices(engine)
    assert set(zip(stale.bond_id, stale.date)) == {("BBB_NRG_45", d) for d in STALE_DAYS}
    ipv = controls.ipv(engine)
    assert set(ipv[ipv.breach].bond_id) == {"BBB_NRG_45"}


def test_amendment_reverses_the_keying_error(engine, results):
    _, by_bond = results
    util = by_bond[by_bond.bond_id == "A_UTIL_33"].set_index("date")
    day_one = util.loc[date(2026, 9, 16), "new_trades"] + util.loc[date(2026, 9, 17), "amendments"]
    # after the correction, the trade's day-one P&L is the true one: bought 4m at 95.57 vs the official mark
    mark = engine.official.loc[date(2026, 9, 16), "A_UTIL_33"]
    assert day_one == pytest.approx(4_000_000 * (mark - 95.57) / 100, abs=0.01)


def test_cancelled_duplicate_leaves_no_pnl_behind(engine, results):
    """Running the book without the duplicate gives the same cumulative P&L once it is cancelled."""
    daily, _ = results
    trades = {k: v for k, v in engine.book.trades.items() if k != "T1006"}
    clean = PnLEngine(engine.bonds, engine.par, engine.spreads, Book(engine.book.opening, trades),
                      stale_marks=set())
    clean_daily, _ = clean.run()
    after = [d for d in daily.index if d >= date(2026, 10, 2) and d < date(2026, 10, 5)]
    cum_with = daily["actual"].cumsum()
    cum_without = clean_daily["actual"].cumsum()
    for d in after:
        assert cum_with[d] == pytest.approx(cum_without[d], abs=0.01)


def test_new_trade_at_the_mark_has_no_day_one_pnl(engine):
    d = date(2026, 9, 10)
    mark = engine.official.loc[d, "BBB_IND_30"]
    t = Trade("TX", "BBB_IND_30", d, 1_000_000, mark)
    e = PnLEngine(engine.bonds, engine.par, engine.spreads, Book(engine.book.opening, {"TX": t}))
    _, by_bond = e.run()
    row = by_bond[(by_bond.bond_id == "BBB_IND_30") & (by_bond.date == d)].iloc[0]
    assert row["new_trades"] == pytest.approx(0.0, abs=1e-9)
