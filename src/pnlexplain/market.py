"""Market data: Treasury curves (real) and issuer credit spreads (simulated).

Treasury par yields come from the US Treasury's Daily Par Yield Curve Rates
(public domain). Credit spreads are simulated, because index spread data from
commercial providers cannot be republished. The simulation is seeded, so every
run gives the same numbers:

    daily spread change = beta(rating) * common credit factor + issuer noise
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .bonds import Bond
from .curves import TENOR_LABELS, TENORS, ZeroCurve, bootstrap

# how strongly each rating bucket moves with the common credit factor
RATING_BETA = {"UST": 0.0, "AA": 0.6, "A": 0.8, "BBB": 1.0, "BB": 2.2}
COMMON_VOL_BP = 1.8      # daily vol of the common credit factor
IDIO_VOL_BP = 0.6        # daily issuer-specific vol, scaled by (0.5 + beta)


def load_par_yields(path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"]).set_index("date").sort_index()
    df.index = df.index.date
    missing = [c for c in TENOR_LABELS if c not in df.columns]
    if missing:
        raise ValueError(f"missing tenors {missing}")
    if df[TENOR_LABELS].isna().any().any():
        raise ValueError("gaps in par yield data")
    return df[TENOR_LABELS]


@dataclass
class CurveSet:
    """Base curve plus the bumped curves needed for risk on one date."""
    par: np.ndarray
    base: ZeroCurve
    key_rate_up: list[ZeroCurve]   # +1bp on each CMT tenor, one at a time
    parallel_up: ZeroCurve         # +1bp on every tenor
    parallel_down: ZeroCurve       # -1bp on every tenor


def build_curve_set(par_pct: np.ndarray) -> CurveSet:
    par_pct = np.asarray(par_pct, dtype=float)
    one_bp = 0.01  # in percent
    krs = []
    for k in range(len(TENORS)):
        bumped = par_pct.copy()
        bumped[k] += one_bp
        krs.append(bootstrap(bumped))
    return CurveSet(
        par=par_pct,
        base=bootstrap(par_pct),
        key_rate_up=krs,
        parallel_up=bootstrap(par_pct + one_bp),
        parallel_down=bootstrap(par_pct - one_bp),
    )


def simulate_spreads(bonds: dict[str, Bond], dates: list, seed: int = 3) -> pd.DataFrame:
    """Daily z-spreads in bp for every bond (Treasuries stay at zero)."""
    rng = np.random.default_rng(seed)
    n = len(dates)
    common = rng.normal(0.0, COMMON_VOL_BP, n)
    common[0] = 0.0
    out = {}
    for bond_id, b in bonds.items():
        beta = RATING_BETA[b.rating]
        idio = rng.normal(0.0, IDIO_VOL_BP * (0.5 + beta), n)
        idio[0] = 0.0
        moves = beta * common + (idio if beta > 0 else 0.0)
        out[bond_id] = b.start_spread_bp + np.cumsum(moves)
    return pd.DataFrame(out, index=dates)
