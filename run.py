"""Run the full daily P&L process for the period and write the outputs.

    python run.py            # writes everything to ./output
"""
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "src"))

from pnlexplain.book import Book, load_opening, load_trades  # noqa: E402
from pnlexplain.bonds import load_bonds  # noqa: E402
from pnlexplain.market import load_par_yields, simulate_spreads  # noqa: E402
from pnlexplain.pnl import PnLEngine  # noqa: E402
from pnlexplain.report import build_outputs, usd  # noqa: E402

DATA = Path(__file__).parent / "data"
OUT = Path(__file__).parent / "output"


def build_engine(seed: int = 3) -> PnLEngine:
    par = load_par_yields(DATA / "treasury_par_yields.csv")
    bonds = load_bonds(DATA / "bonds.csv")
    spreads = simulate_spreads(bonds, list(par.index), seed=seed)
    book = Book(load_opening(DATA / "opening_positions.csv"), load_trades(DATA / "trades.csv"))
    issues = pd.read_csv(DATA / "mark_issues.csv", parse_dates=["date"])
    stale = {(r.bond_id, r.date.date()) for r in issues.itertuples() if r.issue == "stale price feed"}
    return PnLEngine(bonds, par, spreads, book, stale)


def main() -> None:
    engine = build_engine()
    daily, by_bond = engine.run()
    s = build_outputs(engine, daily, by_bond, OUT)
    print(f"P&L days: {s['days']}  |  total P&L {usd(s['total_actual'])}")
    for k, v in s["by_driver"].items():
        print(f"  {k:<14}{usd(v):>12}")
    print(f"  {'unexplained':<14}{usd(s['total_unexplained']):>12}")
    print(f"Clean days {s['clean_days']}: max |unexplained| {usd(s['clean_max_abs_unexplained'])}, "
          f"gross P&L explained {s['clean_gross_explained']:.1%}; break days {s['break_days']}")
    print(f"Outputs written to {OUT}")


if __name__ == "__main__":
    main()
