"""Outputs: daily P&L report with commentary, exceptions, charts and a summary."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from . import controls
from .pnl import EXPLAIN_COLS, PnLEngine


def usd(x: float) -> str:
    sign = "-" if x < 0 else "+"
    x = abs(x)
    if x >= 1e6:
        return f"{sign}${x / 1e6:.2f}m"
    if x >= 1e3:
        return f"{sign}${x / 1e3:.1f}k"
    return f"{sign}${x:.0f}"


def usd_abs(x: float) -> str:
    return usd(abs(x))[1:]


def commentary(row: pd.Series, is_break: bool) -> str:
    drivers = {
        "rates": (row["rates"] + row["convexity"], f"10y {row['10Y_chg_bp']:+.0f}bp"),
        "credit": (row["credit"], f"BBB {row['BBB_spread_chg_bp']:+.1f}bp, BB {row['BB_spread_chg_bp']:+.1f}bp"),
        "carry": (row["accrual"] + row["roll"], "accrual and roll-down"),
        "new trades": (row["new_trades"], "day-one P&L"),
        "amendments": (row["amendments"], "price corrections"),
        "cancellations": (row["cancellations"], "reversals"),
    }
    top = sorted(drivers.items(), key=lambda kv: -abs(kv[1][0]))[:2]
    text = f"{usd(row['actual'])}: " + "; ".join(f"{k} {usd(v)} ({why})" for k, (v, why) in top if abs(v) >= 500)
    if is_break:
        text += f". UNEXPLAINED {usd(row['unexplained'])} above threshold, investigate"
    return text


def build_outputs(engine: PnLEngine, daily: pd.DataFrame, by_bond: pd.DataFrame, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)

    breaks = controls.unexplained_breaks(daily)
    report = daily.copy()
    report["threshold"] = breaks["threshold"]
    report["unexplained_break"] = breaks["break"]
    report["commentary"] = [commentary(r, b) for (_, r), b in zip(report.iterrows(), breaks["break"])]
    cols = ["actual", *EXPLAIN_COLS, "explained", "unexplained", "threshold", "unexplained_break",
            "2Y_chg_bp", "10Y_chg_bp", "30Y_chg_bp", "A_spread_chg_bp", "BBB_spread_chg_bp", "BB_spread_chg_bp",
            "commentary"]
    report[cols].round(2).to_csv(out / "daily_pnl_explain.csv")
    by_bond.round(4).to_csv(out / "position_pnl_explain.csv", index=False)

    nac = controls.trade_review(engine)
    nac.round(3).to_csv(out / "trade_review_nac.csv", index=False)
    stale = controls.stale_prices(engine)
    ipv = controls.ipv(engine)
    ipv_breaches = ipv[ipv["breach"]]

    exceptions = []
    for d, r in breaks[breaks["break"]].iterrows():
        exceptions.append(dict(date=d, control="Unexplained P&L", item="book",
                               detail=f"unexplained {usd(r['unexplained'])} vs threshold {usd(r['threshold'])}"))
    for r in nac[nac["flag"]].itertuples():
        exceptions.append(dict(date=r.date, control=f"Trade review ({r.event})", item=f"{r.trade_id} {r.bond_id}",
                               detail=f"{r.note} | P&L effect {usd(r.pnl_impact)}"))
    for r in stale.itertuples():
        exceptions.append(dict(date=r.date, control="Stale price", item=r.bond_id,
                               detail=f"official {r.official:.3f} unchanged; independent moved {r.independent_move:+.3f}"))
    for r in ipv_breaches.itertuples():
        exceptions.append(dict(date=r.date, control="IPV", item=r.bond_id,
                               detail=f"official {r.official:.3f} vs independent {r.independent:.3f}: {usd(r.variance_usd)}"))
    exc = pd.DataFrame(exceptions).sort_values(["date", "control"]).reset_index(drop=True)
    exc.to_csv(out / "control_exceptions.csv", index=False)

    start = engine.dates[0]
    month_end = max(d for d in engine.dates if d.month == start.month)
    recs = pd.DataFrame([controls.reconcile(engine, daily, start, month_end),
                         controls.reconcile(engine, daily, month_end, engine.dates[-1]),
                         controls.reconcile(engine, daily, start, engine.dates[-1])])
    recs.round(2).to_csv(out / "reconciliation.csv", index=False)

    _charts(report, breaks, out)
    stats = _summary_stats(engine, report, breaks, recs)
    (out / "summary.md").write_text(_summary_markdown(engine, report, stats, exc, recs, month_end))
    return stats


def _charts(report: pd.DataFrame, breaks: pd.DataFrame, out: Path) -> None:
    groups = {
        "Carry (accrual + roll)": report["accrual"] + report["roll"],
        "Rates (incl. convexity)": report["rates"] + report["convexity"],
        "Credit spreads": report["credit"],
        "Trade activity": report["new_trades"] + report["amendments"] + report["cancellations"],
        "Unexplained": report["unexplained"],
    }
    x = pd.to_datetime(report.index)
    fig, ax = plt.subplots(figsize=(10, 5))
    for name, s in groups.items():
        ax.plot(x, s.cumsum() / 1e3, label=name, lw=1.6)
    ax.plot(x, report["actual"].cumsum() / 1e3, label="Actual P&L", color="black", lw=2.4)
    ax.axhline(0, color="grey", lw=0.6)
    ax.set_ylabel("Cumulative P&L (USD thousands)")
    ax.set_title("Where the P&L came from, 2 Sep to 19 Oct 2026")
    ax.legend(frameon=False, fontsize=9)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out / "cumulative_pnl_by_driver.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4))
    colors = ["#c0392b" if b else "#7f8c8d" for b in breaks["break"]]
    ax.bar(x, report["unexplained"] / 1e3, color=colors, width=0.8)
    ax.plot(x, breaks["threshold"] / 1e3, color="black", lw=1, ls="--", label="threshold", drawstyle="steps-mid")
    ax.plot(x, -breaks["threshold"] / 1e3, color="black", lw=1, ls="--", drawstyle="steps-mid")
    ax.set_ylabel("Unexplained P&L (USD thousands)")
    ax.set_title("Daily unexplained P&L against threshold (red = break)")
    ax.legend(frameon=False, fontsize=9)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out / "daily_unexplained.png", dpi=150)
    plt.close(fig)


def _summary_stats(engine: PnLEngine, report: pd.DataFrame, breaks: pd.DataFrame, recs: pd.DataFrame) -> dict:
    clean = report[~breaks["break"]]
    d0 = engine.dates[0]
    dv01 = sum(engine.book.position(b, d0) * engine.risk(b, d0)["dv01"] / 100 for b in engine.bonds)
    cs01 = sum(engine.book.position(b, d0) * engine.risk(b, d0)["cs01"] / 100 for b in engine.bonds)
    return dict(
        days=len(report), bonds=len(engine.bonds), trades=len(engine.book.trades),
        dv01=dv01, cs01=cs01, total_actual=report["actual"].sum(),
        by_driver={c: report[c].sum() for c in EXPLAIN_COLS}, total_unexplained=report["unexplained"].sum(),
        clean_days=len(clean), break_days=int(breaks["break"].sum()),
        clean_max_abs_unexplained=clean["unexplained"].abs().max(),
        clean_top_unexplained=clean["unexplained"].abs().sort_values(ascending=False).head(3),
        clean_mean_abs_unexplained=clean["unexplained"].abs().mean(),
        clean_gross_explained=1 - clean["unexplained"].abs().sum() / clean["actual"].abs().sum(),
        max_recon_difference=recs["difference"].abs().max(),
    )


def _summary_markdown(engine, report, s, exc, recs, month_end: date) -> str:
    sep = report.loc[report.index <= month_end]
    lines = [
        "# Daily P&L attribution: results",
        "",
        f"Period: {engine.dates[1]:%d %b %Y} to {engine.dates[-1]:%d %b %Y} ({s['days']} P&L days). "
        f"Book: {s['bonds']} bonds, {s['trades']} trades in the blotter. "
        f"Opening risk: a 1bp rise in Treasury yields changes the book's value by {usd(s['dv01'])}, "
        f"and a 1bp widening in credit spreads by {usd(s['cs01'])}.",
        "",
        "## P&L by driver",
        "",
        "| Driver | September | Period to date |",
        "| --- | ---: | ---: |",
    ]
    for c in [*EXPLAIN_COLS, "unexplained", "actual"]:
        lines.append(f"| {c.replace('_', ' ').capitalize()} | {usd(sep[c].sum())} | {usd(report[c].sum())} |")
    lines += [
        "",
        "## How well the risk explains the P&L",
        "",
        f"* Days without an unexplained break: {s['clean_days']} of {s['days']}. On those days the average "
        f"unexplained amount was {usd_abs(s['clean_mean_abs_unexplained'])}; the three largest were "
        + ", ".join(f"{usd_abs(v)} on {d:%d %b}" for d, v in s['clean_top_unexplained'].items()) + ".",
        f"* Share of gross daily P&L explained on those days: {s['clean_gross_explained']:.1%}.",
        f"* Days with an unexplained break: {s['break_days']}.",
        f"* Book value roll-forward: largest difference {usd_abs(s['max_recon_difference'])} across the three periods tested.",
        "",
        "## Control exceptions",
        "",
        "| Date | Control | Item | Detail |",
        "| --- | --- | --- | --- |",
    ]
    for r in exc.itertuples():
        lines.append(f"| {r.date} | {r.control} | {r.item} | {r.detail} |")
    lines += ["", "## Book value roll-forward", "",
              "| From | To | Opening value | P&L | Net cash received | Closing value | Difference |",
              "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for r in recs.itertuples():
        lines.append(f"| {r.start} | {r.end} | {r.opening_value:,.2f} | {r.pnl:,.2f} | {r.net_cash_received:,.2f} | "
                     f"{r.closing_value:,.2f} | {r.difference:,.2f} |")
    lines += ["", "## Daily commentary", ""]
    lines += [f"* {d:%d %b}: {c}" for d, c in report["commentary"].items()]
    return "\n".join(lines) + "\n"
