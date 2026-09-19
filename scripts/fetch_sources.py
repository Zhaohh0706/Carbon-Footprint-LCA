"""Fetch and pin the two downloadable sources this analysis rests on.

* IPCC AR5 WGIII Annex III (2014), whose Table A.III.2 gives lifecycle emissions
  and Table A.III.1 plant lifetimes. The PDF is not redistributed here; its
  SHA-256 is checked so a transcription can be traced to one exact file.
* Our World in Data's energy dataset, whose Chinese generation shares come from
  Ember and the Energy Institute. Only China, 2015–2024, is kept.

The third source, the official 2023 grid emission factors, is a table of seven
numbers transcribed into ``data/mee_2023_grid_factors.csv`` with the notice's
URL and the SHA-256 of its PDF.
"""
from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data" / "sources"  # not committed

AR5_URL = "https://www.ipcc.ch/site/assets/uploads/2018/02/ipcc_wg3_ar5_annex-iii.pdf"
AR5_SHA256 = "dec39383e03caf843f833ad8f4b373f72be3b86ada6d826bd172e8955ffe24c2"

OWID_URL = "https://nyc3.digitaloceanspaces.com/owid-public/data/energy/owid-energy-data.csv"

# OWID column -> the category used here.  Every source of generation is kept, so
# the shares sum to 100% and nothing silently drops out of a weighted mean.
MIX_COLUMNS = {
    "coal_share_elec": "coal", "gas_share_elec": "gas", "oil_share_elec": "oil",
    "hydro_share_elec": "hydro", "nuclear_share_elec": "nuclear",
    "wind_share_elec": "wind", "solar_share_elec": "solar",
    "biofuel_share_elec": "bioenergy",
}


def _download(url: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "carbon-footprint-lca"})
    with urllib.request.urlopen(request, timeout=180) as response:
        target.write_bytes(response.read())
    return target


def ar5() -> Path:
    path = SOURCES / "ipcc_ar5_wg3_annex_iii.pdf"
    if not path.exists():
        _download(AR5_URL, path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != AR5_SHA256:
        raise SystemExit(f"AR5 Annex III does not match the transcribed file: {digest}")
    return path


def china_mix() -> pd.DataFrame:
    raw = _download(OWID_URL, SOURCES / "owid-energy-data.csv")
    frame = pd.read_csv(raw)
    china = frame[(frame["country"] == "China") & frame["year"].between(2015, 2024)]
    out = china[["year", "electricity_generation", *MIX_COLUMNS]].rename(
        columns={"electricity_generation": "generation_twh", **MIX_COLUMNS}
    )
    total = out[list(MIX_COLUMNS.values())].sum(axis=1)
    if not ((total - 100).abs() < 0.5).all():
        raise SystemExit(f"shares do not sum to 100%: {total.round(2).tolist()}")
    out = out.round(2)
    out.to_csv(ROOT / "data" / "china_generation_mix_2015_2024.csv", index=False)
    return out


if __name__ == "__main__":
    print("AR5 Annex III:", ar5().name, "sha256 ok")
    mix = china_mix()
    print(f"China mix: {len(mix)} years, shares sum to 100% in every year")
    sys.exit(0)
