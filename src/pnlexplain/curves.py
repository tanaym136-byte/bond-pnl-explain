"""Treasury curve building.

The US Treasury publishes par yields at fixed tenors (the CMT curve). To price
bonds we need discount factors, so we bootstrap the par yields into a zero
curve:

* tenors under 6 months are treated as bill yields: DF = 1 / (1 + y * t)
* from 6 months to 30 years, par yields are interpolated linearly onto a
  semi-annual grid and bootstrapped one point at a time, using the fact that a
  par bond is priced at 100:  1 = c/2 * sum(DF_1..DF_n) + DF_n

Zero rates are continuously compounded and interpolated linearly in time.
"""
from __future__ import annotations

import numpy as np

# CMT tenors in years, in the same order as the columns of the data file
TENOR_LABELS = ["1M", "1.5M", "2M", "3M", "4M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"]
TENORS = np.array([1 / 12, 1.5 / 12, 2 / 12, 3 / 12, 4 / 12, 0.5, 1, 2, 3, 5, 7, 10, 20, 30])

_GRID = np.arange(1, 61) * 0.5  # 0.5y to 30y, semi-annual


class ZeroCurve:
    """Continuously compounded zero curve, linear in time between nodes."""

    def __init__(self, times: np.ndarray, zero_rates: np.ndarray):
        self.times = np.asarray(times, dtype=float)
        self.zero_rates = np.asarray(zero_rates, dtype=float)

    def zero(self, t):
        return np.interp(t, self.times, self.zero_rates)  # flat beyond the ends

    def df(self, t):
        t = np.asarray(t, dtype=float)
        return np.exp(-self.zero(t) * t)


def bootstrap(par_yields_pct) -> ZeroCurve:
    """Build a zero curve from the 14 CMT par yields (in percent)."""
    par = np.asarray(par_yields_pct, dtype=float) / 100.0
    if par.shape != TENORS.shape:
        raise ValueError(f"expected {len(TENORS)} par yields, got {par.shape}")

    short = TENORS < 0.5
    short_t = TENORS[short]
    short_df = 1.0 / (1.0 + par[short] * short_t)

    grid_par = np.interp(_GRID, TENORS, par)
    grid_df = np.empty_like(_GRID)
    for n, c in enumerate(grid_par):
        grid_df[n] = (1.0 - c / 2.0 * grid_df[:n].sum()) / (1.0 + c / 2.0)

    times = np.concatenate([short_t, _GRID])
    dfs = np.concatenate([short_df, grid_df])
    return ZeroCurve(times, -np.log(dfs) / times)


def par_bond_price_on_grid(curve: ZeroCurve, coupon: float, maturity_years: float) -> float:
    """Price of a semi-annual bond whose cash flows sit exactly on the grid.

    Used in tests: a bond paying the par yield as coupon must price at 100.
    """
    n = int(round(maturity_years * 2))
    times = np.arange(1, n + 1) * 0.5
    cfs = np.full(n, coupon / 2.0)
    cfs[-1] += 100.0
    return float((cfs * curve.df(times)).sum())
