"""Lifecycle emissions of electricity technologies, applied to China's grid.

Three inputs, each read from a table that records where it came from:

* ``data/ar5_lifecycle_emissions.csv`` — IPCC AR5 WGIII Annex III (2014),
  Table A.III.2 lifecycle emissions (min / median / max, gCO2eq/kWh) and Table
  A.III.1 plant lifetimes, transcribed from the PDF whose SHA-256 is pinned in
  ``scripts/fetch_sources.py``.
* ``data/china_generation_mix_2015_2024.csv`` — China's generation shares by
  source, from Our World in Data (Ember and the Energy Institute).
* ``data/mee_2023_grid_factors.csv`` — the official 2023 national and regional
  grid emission factors (生态环境部、国家统计局, published 2025-12-31).

Nothing is hard-coded here, so a number in a figure can always be traced to a
row in one of those files.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# Which AR5 technology stands for each category of Chinese generation.
#
# * Wind is not split onshore/offshore in the mix data; onshore (11) is used for
#   all of it. Offshore is 12, so the choice moves nothing that is reported.
# * Solar is taken as utility-scale (48). A large share of Chinese PV is
#   distributed rooftop (41), so this errs slightly high.
# * Oil-fired generation (0.6–0.9% of the mix) has no row in Table A.III.2 and
#   is left out; each year's intensity is reported over the share that is
#   covered, and that coverage is reported beside it.
TECH_FOR_CATEGORY = {
    "coal": "Coal — PC",
    "gas": "Gas — Combined Cycle",
    "hydro": "Hydropower",
    "nuclear": "Nuclear",
    "wind": "Wind onshore",
    "solar": "Solar PV — utility",
    "bioenergy": "Biomass — dedicated",
}
UNCOVERED = ["oil"]


def load_ar5() -> pd.DataFrame:
    return pd.read_csv(DATA / "ar5_lifecycle_emissions.csv").set_index("technology")


def load_mix() -> pd.DataFrame:
    return pd.read_csv(DATA / "china_generation_mix_2015_2024.csv").set_index("year")


def load_grid_factors() -> pd.DataFrame:
    return pd.read_csv(DATA / "mee_2023_grid_factors.csv").set_index("region_en")


def lifecycle_intensity(shares: pd.Series, ar5: pd.DataFrame, stat: str = "median") -> tuple[float, float]:
    """Share-weighted lifecycle intensity (gCO2eq/kWh) and the share it covers (%).

    Weighted over the covered share only. Multiplying shares that do not sum to
    100% by their factors, which an earlier version of this repository did,
    silently counts the missing generation as zero-emission; here the missing
    share is named and excluded instead.
    """
    column = f"lifecycle_{stat}"
    covered = sum(shares[c] for c in TECH_FOR_CATEGORY)
    weighted = sum(shares[c] * ar5.loc[t, column] for c, t in TECH_FOR_CATEGORY.items())
    return weighted / covered, covered


def intensity_series() -> pd.DataFrame:
    """China's lifecycle-basis grid intensity, 2015–2024, with its AR5 range."""
    ar5, mix = load_ar5(), load_mix()
    rows = []
    for year, shares in mix.iterrows():
        median, covered = lifecycle_intensity(shares, ar5, "median")
        low, _ = lifecycle_intensity(shares, ar5, "min")
        high, _ = lifecycle_intensity(shares, ar5, "max")
        rows.append({
            "year": int(year),
            "coal_share_pct": shares["coal"],
            "non_fossil_share_pct": round(sum(shares[c] for c in ["hydro", "nuclear", "wind", "solar", "bioenergy"]), 2),
            "intensity_median": round(median, 1),
            "intensity_min": round(low, 1),
            "intensity_max": round(high, 1),
            "covered_share_pct": round(covered, 2),
        })
    return pd.DataFrame(rows)


def avoided_emissions(capacity_mw: float, technology: str, capacity_factor: float,
                      grid_factor_g_per_kwh: float) -> dict:
    """Annual and lifetime emissions avoided by a plant displacing grid electricity.

    Gross avoided is what the grid would have emitted for the same energy. Net
    subtracts the plant's own lifecycle emissions. Lifetime is AR5's (Table
    A.III.1), not an assumption made here.
    """
    ar5 = load_ar5()
    row = ar5.loc[technology]
    mwh = capacity_mw * capacity_factor * 8760
    # g/kWh is kg/MWh, so MWh × g/kWh is kilograms and tonnes are that over
    # 1,000.  An earlier version divided by 1,000,000 and reported every avoided
    # tonnage a thousand times too small; ratios between regions survived the
    # error, which is why nothing that quoted only ratios noticed it.
    gross = mwh * grid_factor_g_per_kwh / 1e3
    net = mwh * (grid_factor_g_per_kwh - row["lifecycle_median"]) / 1e3
    return {
        "technology": technology, "capacity_mw": capacity_mw, "capacity_factor": capacity_factor,
        "annual_generation_gwh": round(mwh / 1000, 1),
        "grid_factor_g_per_kwh": grid_factor_g_per_kwh,
        "lifecycle_g_per_kwh": row["lifecycle_median"],
        "gross_avoided_t_per_year": round(gross),
        "net_avoided_t_per_year": round(net),
        "lifetime_years": int(row["plant_lifetime_yr"]),
        "lifetime_net_avoided_t": round(net * row["plant_lifetime_yr"]),
    }


def payback_years(technology: str, grid_factor_g_per_kwh: float, stat: str = "median") -> float:
    """Years of operation to avoid as much as the plant's lifecycle emitted.

    A plant with lifecycle intensity L over a lifetime of T years emits L·E·T in
    total for annual generation E, and avoids G·E a year against a grid factor
    G. Payback is therefore L·T/G years — independent of capacity factor, which
    cancels. It treats all lifecycle emissions as incurred up front, which for
    wind and solar (no direct emissions at all in Table A.III.2) is close to
    true.
    """
    row = load_ar5().loc[technology]
    return float(row[f"lifecycle_{stat}"] * row["plant_lifetime_yr"] / grid_factor_g_per_kwh)


if __name__ == "__main__":
    series = intensity_series()
    series.to_csv(DATA / "china_grid_intensity.csv", index=False)
    print(series.to_string(index=False))
